# -*- coding: utf-8 -*-
"""Core service logic for the GitHub Repository microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector
from .retry import RetryEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "optimize_readme",
    "write_contributing_guide",
    "write_code_of_conduct",
    "configure_issue_templates",
    "configure_pr_templates",
    "configure_github_actions",
    "configure_github_pages",
    "configure_github_discussions",
    "configure_github_releases",
    "test_and_optimize_github_repo",
]


class GitHubRepositoryService:
    """Domain service for GitHub Repository."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._feature_count = len(OPERATIONS)

    @staticmethod
    def _get_config(request: Any) -> Dict[str, Any]:
        if request is None:
            return {}
        if hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            return {}
        if not isinstance(data, dict):
            return {}
        return data.get("config", data) if "config" in data else data

    async def get_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_state")
        config = self._get_config(request)
        feature = config.get("feature") if isinstance(config, dict) else None
        if feature and feature in self._state:
            return {
                "feature": "get_state",
                "success": True,
                "status": "found",
                "config": {"feature": feature},
                "result": {"state": self._state[feature]},
                "message": f"State for {feature}",
            }
        return {
            "feature": "get_state",
            "success": False,
            "status": "not_found",
            "config": config,
            "result": {},
            "message": "State not found",
        }

    async def backup_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("backup_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        self._backups[name] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._state.copy(),
        }
        self.metrics.inc_operation("backup_state")
        return {
            "feature": "backup_state",
            "success": True,
            "status": "backed_up",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} created",
        }

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        data = self._backups.get(name)
        if not data:
            return {
                "feature": "restore_state",
                "success": False,
                "status": "not_found",
                "config": {"name": name},
                "result": {},
                "message": f"Backup {name} not found",
            }
        self._state = data["state"].copy()
        self.metrics.inc_operation("restore_state")
        return {
            "feature": "restore_state",
            "success": True,
            "status": "restored",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} restored",
        }

    async def get_stats(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_stats")
        return {
            "feature": "get_stats",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {
                "total_requests": self.metrics.request_count,
                "cache_hits": self.metrics.cache_hits_count,
                "cache_misses": self.metrics.cache_misses_count,
                "operations": self._operations.copy(),
                "index_size": len(self._state),
                "feature_count": self._feature_count,
            },
            "message": "Statistics",
        }

    async def list_methods(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("list_methods")
        return {
            "feature": "list_methods",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {"methods": OPERATIONS + BASE_METHODS},
            "message": "Methods listed",
        }

    async def optimize_readme(self, request: Any = None) -> Dict[str, Any]:
        """Optimize Readme."""
        self.metrics.inc_request("optimize_readme")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:optimize_readme", config)
        self._state["optimize_readme"] = config
        self._operations["optimize_readme"] = self._operations.get("optimize_readme", 0) + 1
        self.metrics.inc_operation("optimize_readme")
        return {
            "feature": "optimize_readme",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "optimize_readme completed",
        }

    async def write_contributing_guide(self, request: Any = None) -> Dict[str, Any]:
        """Write Contributing Guide."""
        self.metrics.inc_request("write_contributing_guide")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_contributing_guide", config)
        self._state["write_contributing_guide"] = config
        self._operations["write_contributing_guide"] = (
            self._operations.get("write_contributing_guide", 0) + 1
        )
        self.metrics.inc_operation("write_contributing_guide")
        return {
            "feature": "write_contributing_guide",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "write_contributing_guide completed",
        }

    async def write_code_of_conduct(self, request: Any = None) -> Dict[str, Any]:
        """Write Code Of Conduct."""
        self.metrics.inc_request("write_code_of_conduct")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_code_of_conduct", config)
        self._state["write_code_of_conduct"] = config
        self._operations["write_code_of_conduct"] = (
            self._operations.get("write_code_of_conduct", 0) + 1
        )
        self.metrics.inc_operation("write_code_of_conduct")
        return {
            "feature": "write_code_of_conduct",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "write_code_of_conduct completed",
        }

    async def configure_issue_templates(self, request: Any = None) -> Dict[str, Any]:
        """Configure Issue Templates."""
        self.metrics.inc_request("configure_issue_templates")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_issue_templates", config)
        self._state["configure_issue_templates"] = config
        self._operations["configure_issue_templates"] = (
            self._operations.get("configure_issue_templates", 0) + 1
        )
        self.metrics.inc_operation("configure_issue_templates")
        return {
            "feature": "configure_issue_templates",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_issue_templates completed",
        }

    async def configure_pr_templates(self, request: Any = None) -> Dict[str, Any]:
        """Configure Pr Templates."""
        self.metrics.inc_request("configure_pr_templates")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_pr_templates", config)
        self._state["configure_pr_templates"] = config
        self._operations["configure_pr_templates"] = (
            self._operations.get("configure_pr_templates", 0) + 1
        )
        self.metrics.inc_operation("configure_pr_templates")
        return {
            "feature": "configure_pr_templates",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_pr_templates completed",
        }

    async def configure_github_actions(self, request: Any = None) -> Dict[str, Any]:
        """Configure Github Actions."""
        self.metrics.inc_request("configure_github_actions")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_github_actions", config)
        self._state["configure_github_actions"] = config
        self._operations["configure_github_actions"] = (
            self._operations.get("configure_github_actions", 0) + 1
        )
        self.metrics.inc_operation("configure_github_actions")
        return {
            "feature": "configure_github_actions",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_github_actions completed",
        }

    async def configure_github_pages(self, request: Any = None) -> Dict[str, Any]:
        """Configure Github Pages."""
        self.metrics.inc_request("configure_github_pages")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_github_pages", config)
        self._state["configure_github_pages"] = config
        self._operations["configure_github_pages"] = (
            self._operations.get("configure_github_pages", 0) + 1
        )
        self.metrics.inc_operation("configure_github_pages")
        return {
            "feature": "configure_github_pages",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_github_pages completed",
        }

    async def configure_github_discussions(self, request: Any = None) -> Dict[str, Any]:
        """Configure Github Discussions."""
        self.metrics.inc_request("configure_github_discussions")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_github_discussions", config)
        self._state["configure_github_discussions"] = config
        self._operations["configure_github_discussions"] = (
            self._operations.get("configure_github_discussions", 0) + 1
        )
        self.metrics.inc_operation("configure_github_discussions")
        return {
            "feature": "configure_github_discussions",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_github_discussions completed",
        }

    async def configure_github_releases(self, request: Any = None) -> Dict[str, Any]:
        """Configure Github Releases."""
        self.metrics.inc_request("configure_github_releases")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_github_releases", config)
        self._state["configure_github_releases"] = config
        self._operations["configure_github_releases"] = (
            self._operations.get("configure_github_releases", 0) + 1
        )
        self.metrics.inc_operation("configure_github_releases")
        return {
            "feature": "configure_github_releases",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "configure_github_releases completed",
        }

    async def test_and_optimize_github_repo(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Github Repo."""
        self.metrics.inc_request("test_and_optimize_github_repo")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_github_repo", config)
        self._state["test_and_optimize_github_repo"] = config
        self._operations["test_and_optimize_github_repo"] = (
            self._operations.get("test_and_optimize_github_repo", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_github_repo")
        return {
            "feature": "test_and_optimize_github_repo",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "GitHub Repository"},
            "message": "test_and_optimize_github_repo completed",
        }

    async def call(self, method: str, **kwargs: Any) -> Any:
        self.metrics.inc_request("call")
        if method == "list_methods":
            return await self.list_methods(**kwargs)
        if method == "get_stats":
            return await self.get_stats(**kwargs)
        if method == "get_state":
            return await self.get_state(**kwargs)
        if method == "backup_state":
            return await self.backup_state(**kwargs)
        if method == "restore_state":
            return await self.restore_state(**kwargs)
        if method in OPERATIONS:
            fn = getattr(self, method, None)
            if fn is None:
                raise ValueError(f"Unknown method: {method}")
            return await fn(**kwargs)
        raise ValueError(f"Unknown method: {method}")


Service = GitHubRepositoryService
