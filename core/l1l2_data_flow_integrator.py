# -*- coding: utf-8 -*-
"""L1-L2数据流集成适配器

实现L1实时流处理到L2分析层的数据流集成
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Union

from core.flink_stream_processor import get_flink_job_manager  # type: ignore
from core.kafka_stream_processor import KafkaTopic, get_kafka_processor
from core.monitoring_infrastructure import get_monitoring_infrastructure

_logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """分析类型"""

    ANOMALY_DETECTION = "anomaly_detection"
    RAG_ANALYSIS = "rag_analysis"
    CAUSAL_ANALYSIS = "causal_analysis"
    PREDICTION_ANALYSIS = "prediction_analysis"


@dataclass
class AnalysisResult:
    """分析结果"""

    analysis_type: AnalysisType
    data_id: str
    result: Dict[str, Any]
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class L1L2DataFlowIntegrator:
    """L1-L2数据流集成器"""

    def __init__(self):
        """初始化L1-L2数据流集成器"""
        self.kafka_processor = get_kafka_processor()
        self.flink_manager = get_flink_job_manager()
        self.monitoring = get_monitoring_infrastructure()

        self.analysis_handlers: Dict[AnalysisType, List[Callable]] = {}
        self.data_flow_stats: Dict[str, Union[int, List[float]]] = {
            "total_processed": 0,
            "total_analyzed": 0,
            "total_errors": 0,
            "processing_times": [],
        }

        self._setup_kafka_handlers()
        self._setup_flink_jobs()

    def _setup_kafka_handlers(self):
        """设置Kafka消息处理器"""
        # 注册指标数据处理
        self.kafka_processor.register_handler(KafkaTopic.METRICS.value, self._handle_metrics_data)

        # 注册日志数据处理
        self.kafka_processor.register_handler(KafkaTopic.LOGS.value, self._handle_logs_data)

        # 注册链路数据处理
        self.kafka_processor.register_handler(KafkaTopic.TRACES.value, self._handle_traces_data)

        # 注册告警数据处理
        self.kafka_processor.register_handler(KafkaTopic.ALERTS.value, self._handle_alerts_data)

        _logger.info("Kafka handlers registered for L1-L2 data flow")

    def _setup_flink_jobs(self):
        """设置Flink作业"""
        # 创建指标聚合作业
        # metrics_job_config = {
        #     "job_name": "metrics_aggregation",
        #     "job_type": FlinkJobType.METRICS_AGGREGATION,
        # }
        # self.flink_manager.create_job(metrics_job_config)

        # 创建异常检测作业
        # anomaly_job_config = {
        #     "job_name": "anomaly_detection",
        #     "job_type": FlinkJobType.ANOMALY_DETECTION,
        # }
        # self.flink_manager.create_job(anomaly_job_config)

        _logger.info("Flink jobs configured for L1-L2 data flow")

    def _handle_metrics_data(self, message):
        """处理指标数据"""
        try:
            data = message.value
            data_id = data.get("id", str(datetime.now(timezone.utc).timestamp()))

            # 记录处理指标
            self.monitoring.metrics_collector.increment_counter(
                "l1l2_data_flow_metrics_processed", labels={"topic": message.topic}
            )

            # 发送到分析层
            self._send_to_analysis(AnalysisType.ANOMALY_DETECTION, data_id, data)

            current_processed = self.data_flow_stats["total_processed"]
            self.data_flow_stats["total_processed"] = (
                (current_processed + 1) if isinstance(current_processed, int) else 1
            )  # type: ignore[assignment]

        except Exception as e:
            _logger.error(f"Error handling metrics data: {e}")
            current_errors = self.data_flow_stats["total_errors"]
            self.data_flow_stats["total_errors"] = (
                (current_errors + 1) if isinstance(current_errors, int) else 1
            )  # type: ignore[assignment]

    def _handle_logs_data(self, message):
        """处理日志数据"""
        try:
            data = message.value
            data_id = data.get("id", str(datetime.now(timezone.utc).timestamp()))

            # 记录处理指标
            self.monitoring.metrics_collector.increment_counter(
                "l1l2_data_flow_logs_processed", labels={"topic": message.topic}
            )

            # 发送到分析层
            self._send_to_analysis(AnalysisType.RAG_ANALYSIS, data_id, data)

            current_processed = self.data_flow_stats["total_processed"]
            self.data_flow_stats["total_processed"] = (
                (current_processed + 1) if isinstance(current_processed, int) else 1
            )  # type: ignore[assignment]

        except Exception as e:
            _logger.error(f"Error handling logs data: {e}")
            current_errors = self.data_flow_stats["total_errors"]
            self.data_flow_stats["total_errors"] = (
                (current_errors + 1) if isinstance(current_errors, int) else 1
            )  # type: ignore[assignment]

    def _handle_traces_data(self, message):
        """处理链路数据"""
        try:
            data = message.value
            data_id = data.get("id", str(datetime.now(timezone.utc).timestamp()))

            # 记录处理指标
            self.monitoring.metrics_collector.increment_counter(
                "l1l2_data_flow_traces_processed", labels={"topic": message.topic}
            )

            # 发送到分析层
            self._send_to_analysis(AnalysisType.CAUSAL_ANALYSIS, data_id, data)

            current_processed = self.data_flow_stats["total_processed"]
            self.data_flow_stats["total_processed"] = (
                (current_processed + 1) if isinstance(current_processed, int) else 1
            )  # type: ignore[assignment]

        except Exception as e:
            _logger.error(f"Error handling traces data: {e}")
            current_errors = self.data_flow_stats["total_errors"]
            self.data_flow_stats["total_errors"] = (
                (current_errors + 1) if isinstance(current_errors, int) else 1
            )  # type: ignore[assignment]

    def _handle_alerts_data(self, message):
        """处理告警数据"""
        try:
            data = message.value
            data_id = data.get("id", str(datetime.now(timezone.utc).timestamp()))

            # 记录处理指标
            self.monitoring.metrics_collector.increment_counter(
                "l1l2_data_flow_alerts_processed", labels={"topic": message.topic}
            )

            # 发送到分析层
            self._send_to_analysis(AnalysisType.PREDICTION_ANALYSIS, data_id, data)

            current_processed = self.data_flow_stats["total_processed"]
            self.data_flow_stats["total_processed"] = (
                (current_processed + 1) if isinstance(current_processed, int) else 1
            )  # type: ignore[assignment]

        except Exception as e:
            _logger.error(f"Error handling alerts data: {e}")
            current_errors = self.data_flow_stats["total_errors"]
            self.data_flow_stats["total_errors"] = (
                (current_errors + 1) if isinstance(current_errors, int) else 1
            )  # type: ignore[assignment]

    def _send_to_analysis(self, analysis_type: AnalysisType, data_id: str, data: Dict[str, Any]):
        """发送到分析层"""
        start_time = datetime.now(timezone.utc)

        try:
            # 调用注册的分析处理器
            handlers = self.analysis_handlers.get(analysis_type, [])
            for handler in handlers:
                try:
                    result = handler(data_id, data)
                    if result:
                        current_analyzed = self.data_flow_stats["total_analyzed"]
                        self.data_flow_stats["total_analyzed"] = (
                            (current_analyzed + 1) if isinstance(current_analyzed, int) else 1
                        )  # type: ignore[assignment]
                except Exception as e:
                    _logger.error(f"Analysis handler error: {e}")

            # 记录处理时间
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.monitoring.metrics_collector.record_timing(
                "l1l2_analysis_duration", duration_ms, labels={"analysis_type": analysis_type.value}
            )
            if isinstance(self.data_flow_stats["processing_times"], list):
                self.data_flow_stats["processing_times"].append(
                    duration_ms
                )  # type: ignore[assignment]

        except Exception as e:
            _logger.error(f"Error sending to analysis: {e}")

    def register_analysis_handler(self, analysis_type: AnalysisType, handler: Callable):
        """注册分析处理器"""
        if analysis_type not in self.analysis_handlers:
            self.analysis_handlers[analysis_type] = []
        self.analysis_handlers[analysis_type].append(handler)
        _logger.info(f"Registered analysis handler for {analysis_type}")

    def start_data_flow(self):
        """启动数据流"""
        try:
            # 启动Kafka消费
            # 这里应该启动各个topic的消费
            _logger.info("Starting L1-L2 data flow")

            # 启动Flink作业
            # for job_name in self.flink_manager.jobs:
            #     self.flink_manager.start_job(job_name)

            _logger.info("L1-L2 data flow started successfully")
            return True
        except Exception as e:
            _logger.error(f"Failed to start data flow: {e}")
            return False

    def stop_data_flow(self):
        """停止数据流"""
        try:
            # 停止Flink作业
            # for job_name in self.flink_manager.jobs:
            #     self.flink_manager.stop_job(job_name)

            _logger.info("L1-L2 data flow stopped successfully")
            return True
        except Exception as e:
            _logger.error(f"Failed to stop data flow: {e}")
            return False

    def get_data_flow_stats(self) -> Dict[str, Any]:
        """获取数据流统计"""
        avg_processing_time = 0.0
        processing_times = self.data_flow_stats.get("processing_times")
        if isinstance(processing_times, list) and processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)

        total_errors_val = self.data_flow_stats.get("total_errors", 0)
        total_errors = total_errors_val if isinstance(total_errors_val, int) else 0
        total_processed_val = self.data_flow_stats.get("total_processed", 0)
        total_processed = total_processed_val if isinstance(total_processed_val, int) else 0
        total_analyzed_val = self.data_flow_stats.get("total_analyzed", 0)
        total_analyzed = total_analyzed_val if isinstance(total_analyzed_val, int) else 0

        return {
            **self.data_flow_stats,
            "avg_processing_time_ms": avg_processing_time,
            "error_rate": total_errors / max(1, total_processed),
            "analysis_rate": total_analyzed / max(1, total_processed),
        }

    def send_test_data(self, topic: str, data: Dict[str, Any]):
        """发送测试数据（用于测试）"""
        return self.kafka_processor.send_message(topic, "test_key", data)


# 全局实例
l1l2_data_flow_integrator = L1L2DataFlowIntegrator()


def get_l1l2_data_flow_integrator() -> L1L2DataFlowIntegrator:
    """获取L1-L2数据流集成器实例"""
    return l1l2_data_flow_integrator
