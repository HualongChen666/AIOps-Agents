# -*- coding: utf-8 -*-
"""
Tests for gRPC Service Manager
Tests for core.grpc_service_manager.py
"""

import pytest
from datetime import datetime, timezone
from core.grpc_service_manager import (
    GRPCService,
    GRPCMethod,
    GRPCServiceManager,
    ServiceStatus,
    get_grpc_service_manager,
)


class TestServiceStatus:
    """Test ServiceStatus enum"""

    def test_service_status_values(self):
        """Test ServiceStatus enum values"""
        assert ServiceStatus.DEFINED.value == "defined"
        assert ServiceStatus.IMPLEMENTED.value == "implemented"
        assert ServiceStatus.DEPLOYED.value == "deployed"
        assert ServiceStatus.ERROR.value == "error"


class TestGRPCMethod:
    """Test GRPCMethod dataclass"""

    def test_grpc_method_creation(self):
        """Test GRPCMethod creation"""
        method = GRPCMethod(
            method_name="TestMethod",
            request_type="TestRequest",
            response_type="TestResponse",
            streaming_type="unary",
            description="Test method",
        )
        assert method.method_name == "TestMethod"
        assert method.request_type == "TestRequest"
        assert method.response_type == "TestResponse"
        assert method.streaming_type == "unary"
        assert method.description == "Test method"

    def test_grpc_method_default_description(self):
        """Test GRPCMethod with default description"""
        method = GRPCMethod(
            method_name="TestMethod",
            request_type="TestRequest",
            response_type="TestResponse",
            streaming_type="server_streaming",
        )
        assert method.description == ""

    def test_grpc_method_streaming_types(self):
        """Test different streaming types"""
        streaming_types = ["unary", "server_streaming", "client_streaming", "bidi_streaming"]
        for stype in streaming_types:
            method = GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type=stype,
            )
            assert method.streaming_type == stype


class TestGRPCService:
    """Test GRPCService dataclass"""

    def test_grpc_service_creation(self):
        """Test GRPCService creation"""
        service = GRPCService(
            service_name="TestService",
            package_name="test",
            proto_content="syntax = \"proto3\";",
            python_content="# Test service",
            status=ServiceStatus.DEFINED,
            metadata={"key": "value"},
        )
        assert service.service_name == "TestService"
        assert service.package_name == "test"
        assert service.proto_content == "syntax = \"proto3\";"
        assert service.python_content == "# Test service"
        assert service.status == ServiceStatus.DEFINED
        assert service.metadata == {"key": "value"}

    def test_grpc_service_default_status(self):
        """Test GRPCService with default status"""
        service = GRPCService(
            service_name="TestService",
            package_name="test",
            proto_content="proto",
            python_content="python",
        )
        assert service.status == ServiceStatus.DEFINED

    def test_grpc_service_default_metadata(self):
        """Test GRPCService with default metadata"""
        service = GRPCService(
            service_name="TestService",
            package_name="test",
            proto_content="proto",
            python_content="python",
        )
        assert service.metadata == {}


class TestGRPCServiceManagerInit:
    """Test GRPCServiceManager initialization"""

    def test_manager_initialization_default(self):
        """Test manager initialization with default config"""
        manager = GRPCServiceManager()
        assert manager.config == {}
        assert manager.services == {}
        assert manager.methods == {}
        assert manager.total_services_defined == 0
        assert manager.total_methods_defined == 0

    def test_manager_initialization_with_config(self):
        """Test manager initialization with config"""
        config = {"key": "value"}
        manager = GRPCServiceManager(config=config)
        assert manager.config == config

    def test_manager_proto_templates_loaded(self):
        """Test that proto templates are loaded"""
        manager = GRPCServiceManager()
        assert "service_header" in manager.proto_templates
        assert "service_definition" in manager.proto_templates
        assert "method_unary" in manager.proto_templates
        assert "message" in manager.proto_templates
        assert "field" in manager.proto_templates


class TestGRPCServiceManagerCreateService:
    """Test service creation"""

    def test_create_service_basic(self):
        """Test basic service creation"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert service.service_name == "TestService"
        assert service.package_name == "test"
        assert service.status == ServiceStatus.DEFINED
        assert "TestService" in manager.services
        assert "TestService" in manager.methods
        assert manager.total_services_defined == 1
        assert manager.total_methods_defined == 1

    def test_create_service_with_messages(self):
        """Test service creation with messages"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]
        messages = {
            "TestRequest": {"field1": "string", "field2": "int32"},
            "TestResponse": {"result": "string"},
        }

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
            messages=messages,
        )

        assert "TestRequest" in service.proto_content
        assert "TestResponse" in service.proto_content

    def test_create_service_multiple_methods(self):
        """Test service creation with multiple methods"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name=f"Method{i}",
                request_type=f"Request{i}",
                response_type=f"Response{i}",
                streaming_type="unary",
            )
            for i in range(5)
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert manager.total_methods_defined == 5
        assert len(manager.methods["TestService"]) == 5

    def test_create_service_metadata(self):
        """Test that service metadata is set correctly"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "method_count" in service.metadata
        assert service.metadata["method_count"] == 1
        assert "created_at" in service.metadata

    def test_create_service_proto_content(self):
        """Test that proto content is generated"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "syntax = \"proto3\"" in service.proto_content
        assert "package test;" in service.proto_content
        assert "service TestService" in service.proto_content
        assert "rpc TestMethod" in service.proto_content

    def test_create_service_python_content(self):
        """Test that Python content is generated"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
                description="Test method description",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "TestService gRPC Service Implementation" in service.python_content
        assert "class TestServiceServicer:" in service.python_content
        assert "async def TestMethod" in service.python_content
        assert "Test method description" in service.python_content


class TestGRPCServiceManagerStreamingTypes:
    """Test different streaming types in proto generation"""

    def test_server_streaming_proto(self):
        """Test server streaming in proto generation"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="StreamMethod",
                request_type="Request",
                response_type="Response",
                streaming_type="server_streaming",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "returns (stream Response)" in service.proto_content

    def test_client_streaming_proto(self):
        """Test client streaming in proto generation"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="StreamMethod",
                request_type="Request",
                response_type="Response",
                streaming_type="client_streaming",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "rpc StreamMethod(stream Request) returns (Response)" in service.proto_content

    def test_bidi_streaming_proto(self):
        """Test bidirectional streaming in proto generation"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="StreamMethod",
                request_type="Request",
                response_type="Response",
                streaming_type="bidi_streaming",
            )
        ]

        service = manager.create_service(
            service_name="TestService",
            package_name="test",
            methods=methods,
        )

        assert "rpc StreamMethod(stream Request) returns (stream Response)" in service.proto_content


class TestGRPCServiceManagerPredefinedServices:
    """Test predefined service creation methods"""

    def test_create_monitoring_service(self):
        """Test monitoring service creation"""
        manager = GRPCServiceManager()
        service = manager.create_monitoring_service()

        assert service.service_name == "MonitoringService"
        assert service.package_name == "monitoring"
        assert service.status == ServiceStatus.DEFINED
        assert "GetMetrics" in service.proto_content
        assert "StreamMetrics" in service.proto_content
        assert "GetAlerts" in service.proto_content

    def test_create_alert_service(self):
        """Test alert service creation"""
        manager = GRPCServiceManager()
        service = manager.create_alert_service()

        assert service.service_name == "AlertService"
        assert service.package_name == "alert"
        assert service.status == ServiceStatus.DEFINED
        assert "SendAlert" in service.proto_content
        assert "StreamAlerts" in service.proto_content

    def test_create_repair_service(self):
        """Test repair service creation"""
        manager = GRPCServiceManager()
        service = manager.create_repair_service()

        assert service.service_name == "RepairService"
        assert service.package_name == "repair"
        assert service.status == ServiceStatus.DEFINED
        assert "ExecuteRepair" in service.proto_content
        assert "StreamRepairProgress" in service.proto_content


class TestGRPCServiceManagerGetServiceSummary:
    """Test service summary retrieval"""

    def test_get_service_summary_empty(self):
        """Test summary when no services exist"""
        manager = GRPCServiceManager()
        summary = manager.get_service_summary()

        assert summary["total_services"] == 0
        assert summary["total_methods"] == 0
        assert summary["services"] == []

    def test_get_service_summary_with_services(self):
        """Test summary with services"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]
        manager.create_service("Service1", "pkg1", methods)
        manager.create_service("Service2", "pkg2", methods)

        summary = manager.get_service_summary()

        assert summary["total_services"] == 2
        assert summary["total_methods"] == 2
        assert len(summary["services"]) == 2
        assert summary["services"][0]["name"] == "Service1"
        assert summary["services"][1]["name"] == "Service2"


class TestGRPCServiceManagerExportProto:
    """Test proto file export"""

    def test_export_proto_file_success(self, tmp_path):
        """Test successful proto file export"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]
        manager.create_service("TestService", "test", methods)

        output_file = tmp_path / "test.proto"
        manager.export_proto_file("TestService", str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "syntax = \"proto3\"" in content
        assert "service TestService" in content

    def test_export_proto_file_not_found(self, tmp_path):
        """Test export for non-existent service"""
        manager = GRPCServiceManager()
        output_file = tmp_path / "test.proto"

        with pytest.raises(ValueError, match="Service .* not found"):
            manager.export_proto_file("NonExistent", str(output_file))


class TestGRPCServiceManagerExportPython:
    """Test Python file export"""

    def test_export_python_file_success(self, tmp_path):
        """Test successful Python file export"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]
        manager.create_service("TestService", "test", methods)

        output_file = tmp_path / "test_service.py"
        manager.export_python_file("TestService", str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "TestService gRPC Service Implementation" in content
        assert "class TestServiceServicer:" in content

    def test_export_python_file_not_found(self, tmp_path):
        """Test export for non-existent service"""
        manager = GRPCServiceManager()
        output_file = tmp_path / "test.py"

        with pytest.raises(ValueError, match="Service .* not found"):
            manager.export_python_file("NonExistent", str(output_file))


class TestGRPCServiceManagerGlobalInstance:
    """Test global instance management"""

    def test_get_grpc_service_manager_singleton(self):
        """Test that get_grpc_service_manager returns singleton"""
        manager1 = get_grpc_service_manager()
        manager2 = get_grpc_service_manager()

        assert manager1 is manager2

    def test_get_grpc_service_manager_initialization(self):
        """Test that global instance is initialized on first call"""
        # Reset global instance
        import core.grpc_service_manager as gsm_module
        gsm_module._grpc_service_manager = None

        manager = get_grpc_service_manager()

        assert manager is not None
        assert isinstance(manager, GRPCServiceManager)


class TestGRPCServiceManagerIntegration:
    """Integration tests for service manager"""

    def test_full_service_lifecycle(self, tmp_path):
        """Test full service lifecycle: create -> export -> delete"""
        manager = GRPCServiceManager()
        methods = [
            GRPCMethod(
                method_name="TestMethod",
                request_type="TestRequest",
                response_type="TestResponse",
                streaming_type="unary",
            )
        ]

        # Create service
        service = manager.create_service("TestService", "test", methods)
        assert service.service_name == "TestService"

        # Export proto
        proto_file = tmp_path / "test.proto"
        manager.export_proto_file("TestService", str(proto_file))
        assert proto_file.exists()

        # Export Python
        python_file = tmp_path / "test.py"
        manager.export_python_file("TestService", str(python_file))
        assert python_file.exists()

        # Get summary
        summary = manager.get_service_summary()
        assert summary["total_services"] == 1

        # Delete service
        del manager.services["TestService"]
        del manager.methods["TestService"]
        manager.total_services_defined -= 1

        summary = manager.get_service_summary()
        assert summary["total_services"] == 0

    def test_multiple_services_management(self):
        """Test managing multiple services"""
        manager = GRPCServiceManager()

        # Create multiple services
        for i in range(3):
            methods = [
                GRPCMethod(
                    method_name=f"Method{i}",
                    request_type=f"Request{i}",
                    response_type=f"Response{i}",
                    streaming_type="unary",
                )
            ]
            manager.create_service(f"Service{i}", f"pkg{i}", methods)

        assert manager.total_services_defined == 3
        assert manager.total_methods_defined == 3

        # Get summary
        summary = manager.get_service_summary()
        assert len(summary["services"]) == 3

        # Delete one service
        del manager.services["Service1"]
        del manager.methods["Service1"]
        manager.total_services_defined -= 1

        summary = manager.get_service_summary()
        assert summary["total_services"] == 2
