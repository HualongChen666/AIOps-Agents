# -*- coding: utf-8 -*-
"""
参数验证器
Parameter Validator

提供多层次参数验证，包括数据结构、必需字段、字段类型、工具白名单等验证。
"""

import os
import re
from typing import Any, Dict, List, Optional


class ParameterValidator:
    """
    参数验证器
    
    提供多层次参数验证，确保工具调用的参数符合预期。
    """
    
    def __init__(self):
        """初始化参数验证器"""
        # 工具类型注册表
        self.tool_type_registry = self._get_tool_type_registry()
        
        # 危险工具列表
        self.dangerous_tools = ["eval", "exec", "compile", "__import__"]
    
    def validate(self, context: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        验证context参数
        
        Args:
            context: 上下文字典
            available_tools: 可用工具列表
        
        Returns:
            验证结果字典 {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        
        # 第一层：数据结构验证
        if not isinstance(context, dict):
            return {
                "valid": False,
                "errors": ["context必须是字典类型"],
                "warnings": []
            }
        
        # 第二层：必需字段验证
        required_fields = ["tool", "params"]
        for field in required_fields:
            if field not in context:
                errors.append(f"context中缺少必需字段'{field}'")
        
        # 第三层：字段类型验证
        if "tool" in context:
            if not isinstance(context["tool"], str):
                errors.append("tool字段必须是字符串类型")
            elif not context["tool"].strip():
                errors.append("tool字段不能为空")
        
        if "params" in context:
            if not isinstance(context["params"], dict):
                errors.append("params字段必须是字典类型")
        
        # 第四层：工具白名单验证
        if "tool" in context and isinstance(context["tool"], str):
            tool_name = context["tool"]
            if tool_name not in available_tools:
                errors.append(f"工具'{tool_name}'不在可用工具列表中: {available_tools}")
            
            # 危险工具检查
            if tool_name in self.dangerous_tools:
                errors.append(f"工具'{tool_name}'被标记为危险工具，禁止使用")
        
        # 第五层：工具特定参数验证
        if "tool" in context and "params" in context:
            tool_name = context["tool"]
            params = context["params"]
            tool_specific_errors = self._validate_tool_specific_params(tool_name, params)
            errors.extend(tool_specific_errors)
        
        # 第六层：可选参数验证
        if "timeout" in context:
            timeout = context["timeout"]
            if not isinstance(timeout, (int, float)):
                errors.append("timeout必须是数字类型")
            elif timeout <= 0:
                errors.append("timeout必须大于0")
            elif timeout > 600:
                warnings.append("timeout超过10分钟，可能导致长时间阻塞")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_tool_specific_params(self, tool_name: str, params: Dict[str, Any]) -> List[str]:
        """
        工具特定参数验证
        
        Args:
            tool_name: 工具名称
            params: 参数字典
        
        Returns:
            错误信息列表
        """
        errors = []
        
        # 获取工具定义
        tool_definition = self.tool_type_registry.get(tool_name)
        if not tool_definition:
            # 如果工具未定义，跳过特定验证
            return errors
        
        # 验证必需参数
        required_params = tool_definition.get("required_params", [])
        for param in required_params:
            if param not in params:
                errors.append(f"工具'{tool_name}'缺少必需参数'{param}'")
        
        # 验证参数类型和范围
        param_validators = tool_definition.get("param_validators", {})
        for param_name, param_value in params.items():
            if param_name in param_validators:
                validator = param_validators[param_name]
                try:
                    if not validator(param_value):
                        errors.append(f"参数'{param_name}'的值'{param_value}'验证失败")
                except Exception as e:
                    errors.append(f"参数'{param_name}'验证时发生异常: {str(e)}")
        
        return errors
    
    def _get_tool_type_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        获取工具类型注册表
        
        Returns:
            工具类型注册表
        """
        return {
            "read_file": {
                "type": "file_operation",
                "required_params": ["file_path"],
                "optional_params": ["encoding", "offset", "limit"],
                "param_validators": {
                    "file_path": self._validate_file_path,
                    "encoding": lambda x: x in ["utf-8", "gbk", "ascii"],
                    "offset": lambda x: isinstance(x, int) and x >= 0,
                    "limit": lambda x: isinstance(x, int) and x > 0 and x <= 10000
                }
            },
            "write_to_file": {
                "type": "file_operation",
                "required_params": ["file_path", "content"],
                "optional_params": ["encoding", "mode"],
                "param_validators": {
                    "file_path": self._validate_file_path,
                    "content": lambda x: isinstance(x, str),
                    "encoding": lambda x: x in ["utf-8", "gbk", "ascii"],
                    "mode": lambda x: x in ["write", "append", "overwrite"]
                }
            },
            "edit": {
                "type": "file_operation",
                "required_params": ["file_path", "old_str", "new_str"],
                "optional_params": ["encoding"],
                "param_validators": {
                    "file_path": self._validate_file_path,
                    "old_str": lambda x: isinstance(x, str),
                    "new_str": lambda x: isinstance(x, str),
                    "encoding": lambda x: x in ["utf-8", "gbk", "ascii"]
                }
            },
            "bash": {
                "type": "command_execution",
                "required_params": ["command"],
                "optional_params": ["timeout", "working_directory"],
                "param_validators": {
                    "command": self._validate_bash_command,
                    "timeout": lambda x: isinstance(x, (int, float)) and x > 0,
                    "working_directory": self._validate_directory_path
                }
            }
        }
    
    def _validate_file_path(self, file_path: str) -> bool:
        """
        验证文件路径
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否有效
        """
        if not isinstance(file_path, str):
            return False
        
        if not file_path.strip():
            return False
        
        # 检查路径穿越
        if "../" in file_path or "..\\" in file_path:
            return False
        
        # 检查路径长度
        if len(file_path) > 500:
            return False
        
        return True
    
    def _validate_bash_command(self, command: str) -> bool:
        """
        验证bash命令
        
        Args:
            command: bash命令
        
        Returns:
            是否有效
        """
        if not isinstance(command, str):
            return False
        
        if not command.strip():
            return False
        
        # 检查命令注入
        dangerous_chars = [";", "|", "&", "$", "`", "$(", "&&", "||"]
        if any(char in command for char in dangerous_chars):
            return False
        
        # 检查命令长度
        if len(command) > 1000:
            return False
        
        return True
    
    def _validate_directory_path(self, directory_path: str) -> bool:
        """
        验证目录路径
        
        Args:
            directory_path: 目录路径
        
        Returns:
            是否有效
        """
        if not isinstance(directory_path, str):
            return False
        
        if not directory_path.strip():
            return False
        
        # 检查路径穿越
        if "../" in directory_path or "..\\" in directory_path:
            return False
        
        # 检查路径长度
        if len(directory_path) > 500:
            return False
        
        return True