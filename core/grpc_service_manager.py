# -*- coding: utf-8 -*-
"""
gRPC Service Manager
Enterprise-grade gRPC service definition and management
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ServiceStatus(Enum):
    """Service status"""

    DEFINED = "defined"
    IMPLEMENTED = "implemented"
    DEPLOYED = "deployed"
    ERROR = "error"


@dataclass
class GRPCService:
    """gRPC service definition"""

    service_name: str
    package_name: str
    proto_content: str
    python_content: str
    status: ServiceStatus = ServiceStatus.DEFINED
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GRPCMethod:
    """gRPC method definition"""

    method_name: str
    request_type: str
    response_type: str
    streaming_type: str  # "unary", "server_streaming", "client_streaming", "bidi_streaming"
    description: str = ""


class GRPCServiceManager:
    """
    Enterprise-grade gRPC service manager
    Provides gRPC service definition and generation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize gRPC service manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Service definitions
        self.services: Dict[str, GRPCService] = {}
        self.methods: Dict[str, List[GRPCMethod]] = {}

        # Proto templates
        self.proto_templates = self._load_proto_templates()

        # Statistics
        self.total_services_defined = 0
        self.total_methods_defined = 0

        logger.info("gRPC service manager initialized")

    def _load_proto_templates(self) -> Dict[str, str]:
        """
        Load proto file templates

        Returns:
            Proto templates
        """
        return {
            "service_header": (
                """syntax = "proto3";
package {package_name};

option go_package = "./{package_name}";
"""
            ),
            "service_definition": (
                """
service {service_name} {{
{methods}
}}
"""
            ),
            "method_unary": "  rpc {method_name}({request_type}) returns ({response_type});",
            "method_server_streaming": (
                "  rpc {method_name}({request_type}) returns (stream {response_type});"
            ),
            "method_client_streaming": (
                "  rpc {method_name}(stream {request_type}) returns ({response_type});"
            ),
            "method_bidi_streaming": (
                "  rpc {method_name}(stream {request_type}) returns (stream {response_type});"
            ),
            "message": (
                """
message {message_name} {{
{fields}
}}
"""
            ),
            "field": "  {field_type} {field_name} = {field_number};",
        }

    def create_service(
        self,
        service_name: str,
        package_name: str,
        methods: List[GRPCMethod],
        messages: Optional[Dict[str, Any]] = None,
    ) -> GRPCService:
        """
        Create gRPC service definition

        Args:
            service_name: Service name
            package_name: Package name
            methods: Service methods
            messages: Message definitions

        Returns:
            gRPC service
        """
        # Generate proto content
        proto_content = self._generate_proto_content(service_name, package_name, methods, messages)

        # Generate Python content
        python_content = self._generate_python_content(service_name, package_name, methods)

        service = GRPCService(
            service_name=service_name,
            package_name=package_name,
            proto_content=proto_content,
            python_content=python_content,
            status=ServiceStatus.DEFINED,
            metadata={
                "method_count": len(methods),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        self.services[service_name] = service
        self.methods[service_name] = methods
        self.total_services_defined += 1
        self.total_methods_defined += len(methods)

        logger.info(f"Created gRPC service: {service_name}")

        return service

    def _generate_proto_content(
        self,
        service_name: str,
        package_name: str,
        methods: List[GRPCMethod],
        messages: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate proto file content

        Args:
            service_name: Service name
            package_name: Package name
            methods: Service methods
            messages: Message definitions

        Returns:
            Proto content
        """
        lines = []

        # Header
        lines.append(self.proto_templates["service_header"].format(package_name=package_name))

        # Messages
        if messages:
            for message_name, fields in messages.items():
                field_lines = []
                for idx, (field_type, field_name) in enumerate(fields.items(), 1):
                    field_lines.append(
                        self.proto_templates["field"].format(
                            field_type=field_type, field_name=field_name, field_number=idx
                        )
                    )
                lines.append(
                    self.proto_templates["message"].format(
                        message_name=message_name, fields="\n".join(field_lines)
                    )
                )

        # Service
        method_lines = []
        for method in methods:
            template_key = f"method_{method.streaming_type}"
            template = self.proto_templates.get(template_key, self.proto_templates["method_unary"])
            method_lines.append(
                template.format(
                    method_name=method.method_name,
                    request_type=method.request_type,
                    response_type=method.response_type,
                )
            )

        lines.append(
            self.proto_templates["service_definition"].format(
                service_name=service_name, methods="\n".join(method_lines)
            )
        )

        return "\n".join(lines)

    def _generate_python_content(
        self, service_name: str, package_name: str, methods: List[GRPCMethod]
    ) -> str:
        """
        Generate Python service implementation content

        Args:
            service_name: Service name
            package_name: Package name
            methods: Service methods

        Returns:
            Python content
        """
        lines = []

        lines.append("# -*- coding: utf-8 -*-")
        lines.append('"""')
        lines.append(f"{service_name} gRPC Service Implementation")
        lines.append('"""')
        lines.append("")
        lines.append("import asyncio")
        lines.append("from typing import AsyncIterator")
        lines.append("import grpc")
        lines.append("from loguru import logger")
        lines.append("")
        lines.append("# Import generated protobuf classes")
        lines.append(f"# import {package_name}_pb2")
        lines.append(f"# import {package_name}_pb2_grpc")
        lines.append("")

        # Service class
        lines.append(f"class {service_name}Servicer:")
        lines.append('    """')
        lines.append(f"    {service_name} service implementation")
        lines.append('    """')
        lines.append("")

        # Methods
        for method in methods:
            lines.append(f"    async def {method.method_name}(self, request, context):")
            lines.append('        """')
            lines.append(f"        {method.description or method.method_name}")
            lines.append('        """')
            lines.append(f'        logger.info(f"{method.method_name} called")')
            lines.append("        pass")
            lines.append("")

        # Server setup
        lines.append(f"async def serve_{service_name.lower()}(port: int = 50051):")
        lines.append('    """')
        lines.append(f"    Start {service_name} gRPC server")
        lines.append('    """')
        lines.append("    server = grpc.aio.server()")
        lines.append(f"    # {package_name}_pb2_grpc.add_{service_name}Servicer_to_server(")
        lines.append(f"    #     {service_name}Servicer(), server")
        lines.append("    # )")
        lines.append("    server.add_insecure_port(f'[::]:{{port}}')")
        lines.append("    await server.start()")
        lines.append(f"    logger.info(f'{service_name} server started on port {{port}}')")
        lines.append("    await server.wait_for_termination()")
        lines.append("")

        # Main
        lines.append("if __name__ == '__main__':")
        lines.append(f"    asyncio.run(serve_{service_name.lower()}())")

        return "\n".join(lines)

    def create_monitoring_service(self) -> GRPCService:
        """
        Create monitoring service

        Returns:
            Monitoring service
        """
        methods = [
            GRPCMethod(
                method_name="GetMetrics",
                request_type="MetricsRequest",
                response_type="MetricsResponse",
                streaming_type="unary",
                description="Get service metrics",
            ),
            GRPCMethod(
                method_name="StreamMetrics",
                request_type="MetricsRequest",
                response_type="MetricsResponse",
                streaming_type="server_streaming",
                description="Stream service metrics",
            ),
            GRPCMethod(
                method_name="GetAlerts",
                request_type="AlertsRequest",
                response_type="AlertsResponse",
                streaming_type="unary",
                description="Get service alerts",
            ),
        ]

        messages = {
            "MetricsRequest": {
                "service_name": "string",
                "time_range": "string",
                "metric_type": "string",
            },
            "MetricsResponse": {"metrics": "repeated Metric", "timestamp": "int64"},
            "AlertsRequest": {"service_name": "string", "severity": "string"},
            "AlertsResponse": {"alerts": "repeated Alert", "total_count": "int32"},
            "Metric": {"name": "string", "value": "double", "labels": "map<string, string>"},
            "Alert": {
                "id": "string",
                "severity": "string",
                "message": "string",
                "timestamp": "int64",
            },
        }

        return self.create_service(
            service_name="MonitoringService",
            package_name="monitoring",
            methods=methods,
            messages=messages,
        )

    def create_alert_service(self) -> GRPCService:
        """
        Create alert service

        Returns:
            Alert service
        """
        methods = [
            GRPCMethod(
                method_name="SendAlert",
                request_type="AlertRequest",
                response_type="AlertResponse",
                streaming_type="unary",
                description="Send alert",
            ),
            GRPCMethod(
                method_name="StreamAlerts",
                request_type="AlertStreamRequest",
                response_type="AlertResponse",
                streaming_type="server_streaming",
                description="Stream alerts",
            ),
        ]

        messages = {
            "AlertRequest": {
                "service_name": "string",
                "severity": "string",
                "message": "string",
                "metadata": "map<string, string>",
            },
            "AlertResponse": {"success": "bool", "alert_id": "string", "message": "string"},
            "AlertStreamRequest": {"service_name": "string", "filter": "string"},
        }

        return self.create_service(
            service_name="AlertService", package_name="alert", methods=methods, messages=messages
        )

    def create_repair_service(self) -> GRPCService:
        """
        Create repair service

        Returns:
            Repair service
        """
        methods = [
            GRPCMethod(
                method_name="ExecuteRepair",
                request_type="RepairRequest",
                response_type="RepairResponse",
                streaming_type="unary",
                description="Execute repair operation",
            ),
            GRPCMethod(
                method_name="StreamRepairProgress",
                request_type="RepairRequest",
                response_type="RepairProgress",
                streaming_type="server_streaming",
                description="Stream repair progress",
            ),
        ]

        messages = {
            "RepairRequest": {
                "repair_id": "string",
                "target_service": "string",
                "repair_type": "string",
                "parameters": "map<string, string>",
            },
            "RepairResponse": {
                "success": "bool",
                "repair_id": "string",
                "status": "string",
                "message": "string",
            },
            "RepairProgress": {
                "repair_id": "string",
                "progress": "double",
                "status": "string",
                "message": "string",
            },
        }

        return self.create_service(
            service_name="RepairService", package_name="repair", methods=methods, messages=messages
        )

    def get_service_summary(self) -> Dict[str, Any]:
        """
        Get service summary

        Returns:
            Service summary
        """
        return {
            "total_services": len(self.services),
            "total_methods": self.total_methods_defined,
            "services": [
                {
                    "name": service.service_name,
                    "package": service.package_name,
                    "status": service.status.value,
                    "method_count": len(self.methods.get(service.service_name, [])),
                }
                for service in self.services.values()
            ],
        }

    def export_proto_file(self, service_name: str, filename: str) -> None:
        """
        Export proto file

        Args:
            service_name: Service name
            filename: Output filename
        """
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not found")

        service = self.services[service_name]

        try:
            with open(filename, "w") as f:
                f.write(service.proto_content)
            logger.info(f"Exported proto file for {service_name} to {filename}")
        except Exception as e:
            logger.error(f"Error exporting proto file: {e}")
            raise

    def export_python_file(self, service_name: str, filename: str) -> None:
        """
        Export Python implementation file

        Args:
            service_name: Service name
            filename: Output filename
        """
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not found")

        service = self.services[service_name]

        try:
            with open(filename, "w") as f:
                f.write(service.python_content)
            logger.info(f"Exported Python file for {service_name} to {filename}")
        except Exception as e:
            logger.error(f"Error exporting Python file: {e}")
            raise


# Global instance
_grpc_service_manager: Optional[GRPCServiceManager] = None


def get_grpc_service_manager() -> GRPCServiceManager:
    """
    Get the global gRPC service manager instance

    Returns:
        GRPCServiceManager instance
    """
    global _grpc_service_manager
    if _grpc_service_manager is None:
        _grpc_service_manager = GRPCServiceManager()
    return _grpc_service_manager
