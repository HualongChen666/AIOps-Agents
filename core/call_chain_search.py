# -*- coding: utf-8 -*-
"""
Call Chain Search and Filter
Enterprise-grade call chain search and filtering capabilities
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, cast

try:
    from loguru import logger
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


class SearchOperator(Enum):
    """Search operator"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"


class SortOrder(Enum):
    """Sort order"""

    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchFilter:
    """Search filter"""

    field: str
    operator: SearchOperator
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)  # type: ignore


@dataclass
class SearchCriteria:
    """Search criteria"""

    trace_id: Optional[str] = None
    service_name: Optional[str] = None
    operation_name: Optional[str] = None
    status: Optional[str] = None
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None
    custom_filters: List[SearchFilter] = field(default_factory=list)
    limit: int = 100
    offset: int = 0
    sort_by: str = "start_time"
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class SearchResult:
    """Search result"""

    trace_id: str
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str
    match_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)  # type: ignore


class CallChainSearchManager:
    """Enterprise-grade call chain search and filter manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize call chain search manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Call chain data storage
        self.call_chains: Dict[str, Dict[str, Any]] = {}

        # Index for fast search
        self.trace_index: Dict[str, List[str]] = {}  # field -> trace_ids
        self.service_index: Dict[str, List[str]] = {}  # service_name -> trace_ids
        self.operation_index: Dict[str, List[str]] = {}  # operation_name -> trace_ids
        self.status_index: Dict[str, List[str]] = {}  # status -> trace_ids
        self.time_index: List[Tuple[datetime, str]] = []  # (start_time, trace_id)

        # Statistics
        self.total_searches = 0
        self.total_results = 0
        self.avg_search_time_ms = 0.0

        logger.info("Call chain search manager initialized")

    def add_call_chain(self, trace_data: Dict[str, Any]) -> None:
        """
        Add call chain data for search

        Args:
            trace_data: Trace data dictionary
        """
        trace_id = trace_data.get("trace_id")
        if not trace_id:
            return

        self.call_chains[trace_id] = trace_data

        # Update indexes
        self._update_indexes(trace_id, trace_data)

        logger.debug(f"Added call chain to search index: {trace_id}")

    def _update_indexes(self, trace_id: str, trace_data: Dict[str, Any]) -> None:
        """
        Update search indexes

        Args:
            trace_id: Trace ID
            trace_data: Trace data
        """
        service_name = trace_data.get("service_name", "")
        operation_name = trace_data.get("operation_name", "")
        status = trace_data.get("status", "")
        start_time = trace_data.get("start_time")

        # Service index
        if service_name:
            if service_name not in self.service_index:
                self.service_index[service_name] = []
            self.service_index[service_name].append(trace_id)

        # Operation index
        if operation_name:
            if operation_name not in self.operation_index:
                self.operation_index[operation_name] = []
            self.operation_index[operation_name].append(trace_id)

        # Status index
        if status:
            if status not in self.status_index:
                self.status_index[status] = []
            self.status_index[status].append(trace_id)

        # Time index
        if start_time:
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time)
                except ValueError:
                    return
            self.time_index.append((start_time, trace_id))
            # Keep time index sorted
            self.time_index.sort(key=lambda x: x[0])

    def search_by_trace_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Search by trace ID

        Args:
            trace_id: Trace ID

        Returns:
            Trace data or None
        """
        self.total_searches += 1

        if trace_id in self.call_chains:
            self.total_results += 1
            return self.call_chains[trace_id]

        return None

    def search_by_service_name(self, service_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search by service name

        Args:
            service_name: Service name
            limit: Result limit

        Returns:
            List of trace data
        """
        self.total_searches += 1

        trace_ids = self.service_index.get(service_name, [])
        results = []

        for trace_id in trace_ids[:limit]:
            if trace_id in self.call_chains:
                results.append(self.call_chains[trace_id])
                self.total_results += 1

        return results

    def search_by_criteria(self, criteria: SearchCriteria) -> List[SearchResult]:
        """
        Search by multiple criteria

        Args:
            criteria: Search criteria

        Returns:
            List of search results
        """
        self.total_searches += 1
        start_time = datetime.now(timezone.utc)

        # Start with all trace IDs
        candidate_ids = set(self.call_chains.keys())

        # Apply filters
        if criteria.trace_id:
            candidate_ids = candidate_ids.intersection({criteria.trace_id})

        if criteria.service_name:
            service_ids = set(self.service_index.get(criteria.service_name, []))
            candidate_ids = candidate_ids.intersection(service_ids)

        if criteria.operation_name:
            operation_ids = set(self.operation_index.get(criteria.operation_name, []))
            candidate_ids = candidate_ids.intersection(operation_ids)

        if criteria.status:
            status_ids = set(self.status_index.get(criteria.status, []))
            candidate_ids = candidate_ids.intersection(status_ids)

        if criteria.start_time or criteria.end_time:
            candidate_ids = self._filter_by_time_range(
                candidate_ids, criteria.start_time, criteria.end_time
            )

        if criteria.min_duration_ms or criteria.max_duration_ms:
            candidate_ids = self._filter_by_duration_range(
                candidate_ids, criteria.min_duration_ms, criteria.max_duration_ms
            )

        if criteria.tags:
            candidate_ids = self._filter_by_tags(candidate_ids, criteria.tags)

        # Apply custom filters
        for custom_filter in criteria.custom_filters:
            candidate_ids = self._apply_custom_filter(candidate_ids, custom_filter)

        # Sort results
        results = []
        for trace_id in candidate_ids:
            if trace_id in self.call_chains:
                trace_data = self.call_chains[trace_id]
                result = SearchResult(
                    trace_id=trace_id,
                    service_name=trace_data.get("service_name", ""),
                    operation_name=trace_data.get("operation_name", ""),
                    start_time=self._parse_datetime(trace_data.get("start_time"))
                    or datetime.now(timezone.utc),
                    end_time=self._parse_datetime(trace_data.get("end_time"))
                    or datetime.now(timezone.utc),
                    duration_ms=trace_data.get("duration_ms", 0),
                    status=trace_data.get("status", ""),
                    match_score=self._calculate_match_score(trace_data, criteria),
                    metadata=trace_data.get("metadata", {}),
                )
                results.append(result)
                self.total_results += 1

        # Sort
        reverse = criteria.sort_order == SortOrder.DESC
        results.sort(key=lambda x: getattr(x, criteria.sort_by, x.start_time), reverse=reverse)

        # Apply pagination
        results = results[criteria.offset : criteria.offset + criteria.limit]

        # Calculate search time
        search_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        self.avg_search_time_ms = (
            self.avg_search_time_ms * (self.total_searches - 1) + search_time
        ) / self.total_searches

        logger.info(f"Search completed: {len(results)} results in {search_time:.2f}ms")

        return results

    def _filter_by_time_range(
        self, candidate_ids: set, start_time: Optional[datetime], end_time: Optional[datetime]
    ) -> set:
        """
        Filter by time range

        Args:
            candidate_ids: Candidate trace IDs
            start_time: Start time
            end_time: End time

        Returns:
            Filtered trace IDs
        """
        filtered_ids = set()

        for trace_id in candidate_ids:
            if trace_id not in self.call_chains:
                continue

            trace_data = self.call_chains[trace_id]
            trace_start = self._parse_datetime(trace_data.get("start_time"))

            if not trace_start:
                continue

            if start_time and trace_start < start_time:
                continue

            if end_time and trace_start > end_time:
                continue

            filtered_ids.add(trace_id)

        return filtered_ids

    def _filter_by_duration_range(
        self, candidate_ids: set, min_duration_ms: Optional[float], max_duration_ms: Optional[float]
    ) -> set:
        """
        Filter by duration range

        Args:
            candidate_ids: Candidate trace IDs
            min_duration_ms: Minimum duration
            max_duration_ms: Maximum duration

        Returns:
            Filtered trace IDs
        """
        filtered_ids = set()

        for trace_id in candidate_ids:
            if trace_id not in self.call_chains:
                continue

            trace_data = self.call_chains[trace_id]
            duration_ms = trace_data.get("duration_ms", 0)

            if min_duration_ms is not None and duration_ms < min_duration_ms:
                continue

            if max_duration_ms is not None and duration_ms > max_duration_ms:
                continue

            filtered_ids.add(trace_id)

        return filtered_ids

    def _filter_by_tags(self, candidate_ids: set, tags: Dict[str, str]) -> set:
        """
        Filter by tags

        Args:
            candidate_ids: Candidate trace IDs
            tags: Tags to match

        Returns:
            Filtered trace IDs
        """
        filtered_ids = set()

        for trace_id in candidate_ids:
            if trace_id not in self.call_chains:
                continue

            trace_data = self.call_chains[trace_id]
            trace_tags = trace_data.get("tags", {})

            # Check if all tags match
            if all(trace_tags.get(key) == value for key, value in tags.items()):
                filtered_ids.add(trace_id)

        return filtered_ids

    def _apply_custom_filter(self, candidate_ids: set, custom_filter: SearchFilter) -> set:
        """
        Apply custom filter

        Args:
            candidate_ids: Candidate trace IDs
            custom_filter: Custom filter

        Returns:
            Filtered trace IDs
        """
        filtered_ids = set()

        for trace_id in candidate_ids:
            if trace_id not in self.call_chains:
                continue

            trace_data = self.call_chains[trace_id]
            field_value = trace_data.get(custom_filter.field)

            if self._matches_filter(field_value, custom_filter):
                filtered_ids.add(trace_id)

        return filtered_ids

    def _matches_filter(self, field_value: Any, filter: SearchFilter) -> bool:
        """
        Check if field value matches filter

        Args:
            field_value: Field value
            filter: Search filter

        Returns:
            Match result
        """
        try:
            if filter.operator == SearchOperator.EQUALS:
                return cast(bool, field_value == filter.value)
            elif filter.operator == SearchOperator.NOT_EQUALS:
                return cast(bool, field_value != filter.value)
            elif filter.operator == SearchOperator.CONTAINS:
                return filter.value in str(field_value)
            elif filter.operator == SearchOperator.NOT_CONTAINS:
                return filter.value not in str(field_value)
            elif filter.operator == SearchOperator.GREATER_THAN:
                return float(field_value) > float(filter.value)
            elif filter.operator == SearchOperator.LESS_THAN:
                return float(field_value) < float(filter.value)
            elif filter.operator == SearchOperator.GREATER_THAN_OR_EQUAL:
                return float(field_value) >= float(filter.value)
            elif filter.operator == SearchOperator.LESS_THAN_OR_EQUAL:
                return float(field_value) <= float(filter.value)
            elif filter.operator == SearchOperator.IN:
                return field_value in filter.value
            elif filter.operator == SearchOperator.NOT_IN:
                return field_value not in filter.value
            elif filter.operator == SearchOperator.REGEX:
                return bool(re.search(filter.value, str(field_value)))
            else:
                return True
        except (ValueError, TypeError):
            return False

    def _calculate_match_score(self, trace_data: Dict[str, Any], criteria: SearchCriteria) -> float:
        """
        Calculate match score for result

        Args:
            trace_data: Trace data
            criteria: Search criteria

        Returns:
            Match score (0-1)
        """
        score = 0.0
        total_criteria = 0

        if criteria.trace_id and trace_data.get("trace_id") == criteria.trace_id:
            score += 1.0
        total_criteria += 1

        if criteria.service_name and trace_data.get("service_name") == criteria.service_name:
            score += 1.0
        total_criteria += 1

        if criteria.operation_name and trace_data.get("operation_name") == criteria.operation_name:
            score += 1.0
        total_criteria += 1

        if criteria.status and trace_data.get("status") == criteria.status:
            score += 1.0
        total_criteria += 1

        return score / total_criteria if total_criteria > 0 else 0.0

    def _parse_datetime(self, datetime_str: Any) -> Optional[datetime]:
        """
        Parse datetime string

        Args:
            datetime_str: Datetime string or object

        Returns:
            Datetime object or None
        """
        if isinstance(datetime_str, datetime):
            return datetime_str
        elif isinstance(datetime_str, str):
            try:
                return datetime.fromisoformat(datetime_str)
            except ValueError:
                return None
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get search statistics"""
        return {
            "total_searches": self.total_searches,
            "total_results": self.total_results,
            "avg_search_time_ms": self.avg_search_time_ms,
            "indexed_traces": len(self.call_chains),
            "indexed_services": len(self.service_index),
            "indexed_operations": len(self.operation_index),
            "time_index_size": len(self.time_index),
        }


def get_call_chain_search_manager(
    config: Optional[Dict[str, Any]] = None,
) -> CallChainSearchManager:
    """
    Factory function to get call chain search manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        CallChainSearchManager: Search manager instance
    """
    return CallChainSearchManager(config)
