# -*- coding: utf-8 -*-
"""中危台账批次 23 回归测试（extensions/ 域，2026-09-16）。

覆盖条目（全部经 HEAD 回读源码核验后修复）：
- EXT-002 extensions/plugin_loader.py
           加载失败的插件模块残留在 sys.modules（半初始化污染后续导入）
- EXT-015 extensions/addons/ai_plus/access_control_service/access_control_manager.py
           未知 action 默认降级为 READ（fail-open）→ 改为如实映射/失败即拒
- EXT-033 extensions/addons/ai_plus/automated_testing_service/test_runner.py
           _parse_text_results 以子串计数（汇总行/堆栈里的词也被计入）
- EXT-042 extensions/addons/ai_plus/certificate_management_service/certificate_validator.py
           _check_signature 对自签/CA 签一律 valid=True（签名校验未执行）
- EXT-069 extensions/addons/ai_plus/dependency_management_service/dependency_scanner.py
           _parse_pipdeptree_output children 恒 []（不解析嵌套依赖）
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ADDONS_ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"
ROOT_PKG = "__batch23_addons"


def _sanitized_name(part: str) -> str:
    return part.replace("-", "_").replace(".", "_")


def _ensure_package_chain(rel_dir: Path) -> str:
    parts = [_sanitized_name(p) for p in rel_dir.parts]
    root_pkg = sys.modules.setdefault(ROOT_PKG, types.ModuleType(ROOT_PKG))
    root_pkg.__path__ = [str(ADDONS_ROOT)]
    current = ROOT_PKG
    for i, part in enumerate(parts):
        current += f".{part}"
        pkg = sys.modules.setdefault(current, types.ModuleType(current))
        pkg.__path__ = [str(ADDONS_ROOT / Path(*rel_dir.parts[: i + 1]))]
    return current


def _load_module(rel_path: str):
    path = ADDONS_ROOT / rel_path
    rel = path.relative_to(ADDONS_ROOT)
    package = _ensure_package_chain(rel.parent)
    module_name = f"{package}.{_sanitized_name(path.stem)}"
    spec = importlib.util.spec_from_file_location(
        module_name, str(path), submodule_search_locations=None
    )
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {rel_path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - dependency issue in this env
        sys.modules.pop(module_name, None)
        pytest.skip(f"Failed to load {rel_path}: {exc}")
    return module


# ---------------------------------------------------------------------------
# EXT-002 — plugin_loader must not leave half-initialised modules behind
# ---------------------------------------------------------------------------
class TestPluginLoaderEviction:
    def test_failed_load_is_evicted_from_sys_modules(self, tmp_path):
        from extensions.plugin_loader import _load_one

        bad = tmp_path / "batch23_bad.py"
        bad.write_text("import a_module_that_does_not_exist_batch23\n")

        module, ok, err = _load_one(bad, "batch23_bad")
        assert ok is False
        assert "ModuleNotFoundError" in err or "ImportError" in err
        # The half-initialised module must not linger in sys.modules.
        assert "batch23_bad" not in sys.modules
        assert module is not None

    def test_retry_after_import_failure_succeeds(self, tmp_path):
        """A dependency that appears later must let the next pass load cleanly."""
        from extensions.plugin_loader import _load_one

        dep = tmp_path / "batch23_dep.py"
        dep.write_text("value = 7\n")
        target = tmp_path / "batch23_target.py"
        target.write_text("from batch23_dep import value\nresult = value + 1\n")

        _, ok, _ = _load_one(target, "batch23_target")
        assert ok is False
        assert "batch23_target" not in sys.modules

        _, dep_ok, _ = _load_one(dep, "batch23_dep")
        assert dep_ok is True

        module, ok, err = _load_one(target, "batch23_target")
        assert ok is True, err
        assert module.result == 8

    def test_successful_load_stays_in_sys_modules(self, tmp_path):
        from extensions.plugin_loader import _load_one

        good = tmp_path / "batch23_good.py"
        good.write_text("flag = True\n")

        _, ok, _ = _load_one(good, "batch23_good")
        assert ok is True
        assert "batch23_good" in sys.modules
        sys.modules.pop("batch23_good", None)


# ---------------------------------------------------------------------------
# EXT-015 — unknown action must not be downgraded to READ (fail closed)
# ---------------------------------------------------------------------------
class TestAccessControlActionMapping:
    def _manager(self):
        mod = _load_module("ai_plus/access_control_service/access_control_manager.py")
        from unittest.mock import MagicMock

        mgr = mod.AccessControlManager(storage=MagicMock())
        mgr._is_initialized = True
        mgr.rbac_manager = MagicMock()
        mgr.rbac_manager.check_permission.return_value = False
        mgr.rbac_manager.get_subject_roles.return_value = []
        mgr.abac_engine = MagicMock()
        mgr.abac_engine.evaluate.return_value = True
        return mod, mgr

    def test_known_action_maps_to_enum(self):
        mod, mgr = self._manager()
        assert mgr._map_action("read") is mod.ActionType.READ
        assert mgr._map_action("DELETE") is mod.ActionType.DELETE

    def test_unknown_action_returns_none(self):
        _, mgr = self._manager()
        assert mgr._map_action("frobnicate") is None

    def test_unknown_action_fails_closed(self):
        _, mgr = self._manager()

        kwargs = dict(
            subject_type="user",
            subject_attributes={},
            subject_roles=[],
            subject_groups=[],
            resource_id="r1",
            resource_type="metric",
            resource_attributes={},
            resource_owner=None,
            environment_attributes={},
        )
        allowed = mgr.check_access(subject_id="u1", action="read", **kwargs)
        assert allowed["allowed"] is True  # ABAC grants a known action

        denied = mgr.check_access(subject_id="u1", action="frobnicate", **kwargs)
        # Unknown action is never silently treated as READ.
        assert denied["allowed"] is False


# ---------------------------------------------------------------------------
# EXT-033 — text result parsing must not match bare substrings
# ---------------------------------------------------------------------------
class TestPytestTextParsing:
    def _runner(self):
        mod = _load_module("ai_plus/automated_testing_service/test_runner.py")
        return mod

    def test_counts_only_real_result_lines(self):
        mod = self._runner()
        report = mod.TestReport(suite_id="s1")
        output = "\n".join(
            [
                "tests/test_a.py::test_one PASSED [ 50%]",
                "tests/test_a.py::test_two FAILED [100%]",
                "=========================== short test summary info ============================",
                "FAILED tests/test_a.py::test_two - AssertionError: PASSED was expected",
                "1 failed, 1 passed in 0.12s",
            ]
        )
        mod.TestRunner()._parse_text_results(output, report, "s1")
        assert report.passed == 1
        assert report.failed == 1
        assert report.total_tests == 2
        assert {r.test_case_id for r in report.results} == {
            "tests/test_a.py::test_one",
            "tests/test_a.py::test_two",
        }

    def test_summary_only_output_counts_nothing(self):
        mod = self._runner()
        report = mod.TestReport(suite_id="s1")
        mod.TestRunner()._parse_text_results("3 passed, 1 skipped in 1.23s", report, "s1")
        assert report.total_tests == 0
        assert report.passed == 0


# ---------------------------------------------------------------------------
# EXT-042 — signature verification must be real
# ---------------------------------------------------------------------------
class TestCertificateSignature:
    @staticmethod
    def _build_chain():
        import datetime as _dt

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        def _name(cn):
            return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

        now = _dt.datetime.now(_dt.timezone.utc)
        root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        root = (
            x509.CertificateBuilder()
            .subject_name(_name("Batch23 Root CA"))
            .issuer_name(_name("Batch23 Root CA"))
            .public_key(root_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - _dt.timedelta(days=1))
            .not_valid_after(now + _dt.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(root_key, hashes.SHA256())
        )
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        leaf = (
            x509.CertificateBuilder()
            .subject_name(_name("Batch23 Leaf"))
            .issuer_name(root.subject)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - _dt.timedelta(days=1))
            .not_valid_after(now + _dt.timedelta(days=30))
            .sign(root_key, hashes.SHA256())
        )
        return root, leaf

    def _validator(self):
        mod = _load_module("ai_plus/certificate_management_service/certificate_validator.py")
        return mod.CertificateValidator()

    def test_self_signed_signature_verified(self):
        root, _ = self._build_chain()
        validator = self._validator()
        result = validator._check_signature(root)
        assert result["valid"] is True
        assert result["status"] == "valid"

    def test_ca_signed_without_issuer_is_unverified(self):
        root, leaf = self._build_chain()
        validator = self._validator()
        result = validator._check_signature(leaf)
        # No issuer available → must not claim "valid".
        assert result["valid"] is None
        assert result["status"] == "unverified"

    def test_ca_signed_with_issuer_is_verified(self):
        root, leaf = self._build_chain()
        validator = self._validator()
        result = validator._check_signature(leaf, issuer_cert=root)
        assert result["valid"] is True

    def test_tampered_signature_is_invalid(self):
        root, leaf = self._build_chain()
        validator = self._validator()
        # Verify the leaf against a different key (the leaf's own) → must fail.
        result = validator._check_signature(leaf, issuer_cert=leaf)
        assert result["valid"] is False
        assert result["status"] == "invalid_signature"


# ---------------------------------------------------------------------------
# EXT-069 — dependency tree must parse nested dependencies
# ---------------------------------------------------------------------------
class TestDependencyTreeParsing:
    SAMPLE = "\n".join(
        [
            "pytest==7.4.0",
            "├── iniconfig [required: Any, installed: 2.0.0]",
            "├── packaging [required: >=20.0, installed: 23.1]",
            "│   └── pyparsing [required: >=2.0.2, installed: 3.1.1]",
            "└── pluggy [required: >=0.12, installed: 1.2.0]",
        ]
    )

    def _scanner(self):
        mod = _load_module("ai_plus/dependency_management_service/dependency_scanner.py")
        return mod.DependencyScanner()

    def test_nested_children_are_parsed(self):
        scanner = self._scanner()
        tree = scanner._parse_pipdeptree_output(self.SAMPLE, depth=3)
        assert tree["name"] == "pytest"
        assert tree["version"] == "7.4.0"
        names = [c["name"] for c in tree["children"]]
        assert names == ["iniconfig", "packaging", "pluggy"]
        packaging = tree["children"][1]
        assert packaging["version"] == "23.1"
        assert [c["name"] for c in packaging["children"]] == ["pyparsing"]
        assert tree["children"][0]["children"] == []

    def test_depth_limit_is_respected(self):
        scanner = self._scanner()
        tree = scanner._parse_pipdeptree_output(self.SAMPLE, depth=1)
        assert [c["name"] for c in tree["children"]] == [
            "iniconfig",
            "packaging",
            "pluggy",
        ]
        assert all(c["children"] == [] for c in tree["children"])

    def test_empty_output_is_honest(self):
        scanner = self._scanner()
        tree = scanner._parse_pipdeptree_output("", depth=3)
        assert tree == {"name": "unknown", "version": "unknown", "children": []}
