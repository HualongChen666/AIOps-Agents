# -*- coding: utf-8 -*-
"""L1-L2数据流集成适配器

实现L1实时流处理到L2分析层的数据流集成
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Union

from core.flink_stream_processor import FlinkJobConfig, FlinkJobType, get_flink_job_manager  # type: ignore
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

        # 运行期状态（供 start/stop_data_flow 使用）
        self._running = False
        self._stop_event = threading.Event()
        self._consumer_threads: List[threading.Thread] = []

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
        """设置Flink作业（真实创建 metric/anomaly 两个作业）。

        历史问题（已修复）：原实现中创建 metrics_job / anomaly_job 的代码**全部被
        注释掉**，作业从未创建，"数据流"未启动任何 Flink 作业。现按 FlinkJobType
        真实创建并登记作业。
        """
        self.flink_manager.create_job(
            FlinkJobConfig(
                job_name="metrics_aggregation", job_type=FlinkJobType.METRICS_AGGREGATION
            )
        )
        self.flink_manager.create_job(
            FlinkJobConfig(job_name="anomaly_detection", job_type=FlinkJobType.ANOMALY_DETECTION)
        )
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
        """启动数据流（真实启动 Flink 作业并按 topic 启动 Kafka 消费）。

        历史问题（已修复）：原实现中启动 Kafka 消费与 Flink 作业的代码**全被注释**，
        "数据流"未启动任何消费/作业，仅注册内存 handler。现真实启动 Flink 作业，并在
        真实 Kafka 消费者可用时启动后台消费线程；消费者不可用时如实告警（不伪造）。
        """
        if self._running:
            return True
        try:
            started = [
                name
                for name in ("metrics_aggregation", "anomaly_detection")
                if self.flink_manager.start_job(name)
            ]

            consumer = getattr(self.kafka_processor, "consumer", None)
            if consumer is not None:
                self._stop_event.clear()
                for topic in KafkaTopic:
                    th = threading.Thread(
                        target=self._consume_loop,
                        args=(topic.value,),
                        name=f"l1l2-{topic.value}",
                        daemon=True,
                    )
                    th.start()
                    self._consumer_threads.append(th)
                _logger.info("L1-L2 data flow started (Kafka consumers running)")
            else:
                _logger.warning(
                    "Kafka consumer unavailable; L1-L2 flow runs without live consumers"
                )

            self._running = True
            _logger.info(f"L1-L2 data flow started successfully (flink jobs: {started})")
            return True
        except Exception as e:
            _logger.error(f"Failed to start data flow: {e}")
            return False

    def _consume_loop(self, topic: str) -> None:
        """后台消费循环：将 Kafka 消息分派给已注册处理器。"""
        handlers = self.kafka_processor.message_handlers.get(topic, [])
        while not self._stop_event.is_set():
            try:
                for message in self.kafka_processor.consume_messages(
                    topic, group_id="l1l2-data-flow", auto_commit=True
                ):
                    if self._stop_event.is_set():
                        break
                    for handler in handlers:
                        handler(message)
            except Exception as e:  # noqa: BLE001
                _logger.error(f"Consumer loop error for topic {topic}: {e}")
            self._stop_event.wait(1.0)

    def stop_data_flow(self):
        """停止数据流（真实停止 Flink 作业与消费线程）。"""
        try:
            self._stop_event.set()
            for th in list(self._consumer_threads):
                th.join(timeout=2.0)
            self._consumer_threads.clear()
            for name in ("metrics_aggregation", "anomaly_detection"):
                self.flink_manager.stop_job(name)
            self._running = False
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
