# -*- coding: utf-8 -*-
"""测试GitOps管理器模块"""

import pytest


class TestGitOpsManagerModule:
    """测试GitOps管理器模块"""

    def test_gitops_manager_module_exists(self):
        """测试GitOps管理器模块存在"""
        from core import gitops_manager

        assert gitops_manager is not None

    def test_gitops_manager_has_functions(self):
        """测试GitOps管理器模块有函数"""
        from core import gitops_manager

        # 检查模块有函数或类
        assert len(dir(gitops_manager)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
