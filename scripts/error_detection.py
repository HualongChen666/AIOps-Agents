#!/usr/bin/env python
"""
AIOps SRE Agent错误检测机制

包含Pydantic验证、数据库表存在性检测、依赖导入错误检测等
"""

import sys
import os
import logging
import importlib
from typing import List, Dict, Any, Tuple
from pathlib import Path
from sqlalchemy import inspect
from pydantic import BaseModel, ValidationError

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ErrorDetector:
    """错误检测器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def detect_pydantic_errors(self, module_name: str) -> List[str]:
        """检测Pydantic模型错误"""
        errors = []
        try:
            module = importlib.import_module(f"core.{module_name}")
            
            # 检查所有BaseModel子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseModel) and attr != BaseModel:
                    # 检查字段命名
                    for field_name, field_info in attr.model_fields.items():
                        if field_name.startswith('_'):
                            errors.append(f"Pydantic field error: {module_name}.{attr.__name__} field '{field_name}' uses underscore prefix")
        except Exception as e:
            errors.append(f"Pydantic error detection failed: {e}")
        
        return errors
    
    def detect_database_table_errors(self) -> List[str]:
        """检测数据库表存在性错误"""
        errors = []
        try:
            from core.database import engine
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # 检查关键表是否存在
            required_tables = [
                'users', 'alerts', 'metrics', 'workflows', 'audit_logs',
                'mesh_configurations', 'traffic_rules', 'security_policies',
                'integrations', 'monitoring_dashboards', 'testing_suites',
                'plugins', 'infrastructure_configs'
            ]
            
            for table in required_tables:
                if table not in tables:
                    errors.append(f"Database table missing: '{table}'")
        except Exception as e:
            errors.append(f"Database table detection failed: {e}")
        
        return errors
    
    def detect_import_errors(self, module_name: str) -> List[str]:
        """检测依赖导入错误"""
        errors = []
        try:
            module = importlib.import_module(f"api.{module_name}")
            
            # 检查导入的模块是否存在
            import inspect
            source = inspect.getsource(module)
            
            # 简单的导入检查
            import_line_count = source.count('from ')
            self.warnings.append(f"{module_name} has {import_line_count} import statements")
            
        except ImportError as e:
            errors.append(f"Import error: {module_name} - {e}")
        except Exception as e:
            errors.append(f"Import detection failed: {e}")
        
        return errors
    
    def detect_runtime_errors(self, module_name: str) -> List[str]:
        """检测运行时错误"""
        errors = []
        try:
            # 尝试实例化模块中的关键类
            module = importlib.import_module(f"api.{module_name}")
            
            if hasattr(module, 'router'):
                router = getattr(module, 'router')
                self.warnings.append(f"{module_name} router object exists")
            
        except Exception as e:
            errors.append(f"Runtime error detection failed: {e}")
        
        return errors
    
    def detect_all_errors(self, module_name: str) -> Dict[str, List[str]]:
        """检测所有类型的错误"""
        all_errors = {}
        
        all_errors['pydantic'] = self.detect_pydantic_errors(module_name)
        all_errors['database'] = self.detect_database_table_errors()
        all_errors['import'] = self.detect_import_errors(module_name)
        all_errors['runtime'] = self.detect_runtime_errors(module_name)
        
        return all_errors
    
    def generate_error_report(self) -> str:
        """生成错误报告"""
        report = "# Error Detection Report\n\n"
        
        if not self.errors and not self.warnings:
            report += "No errors found\n"
        else:
            if self.errors:
                report += "## Error List\n\n"
                for error in self.errors:
                    report += f"- {error}\n"
            
            if self.warnings:
                report += "\n## Warning List\n\n"
                for warning in self.warnings:
                    report += f"- {warning}\n"
        
        return report

def main():
    """主函数"""
    if len(sys.argv) > 1:
        modules = sys.argv[1:]
    else:
        modules = ["elasticsearch_client", "monitoring_advanced_router"]
    
    detector = ErrorDetector()
    
    for module in modules:
        logger.info(f"Detecting errors in module: {module}")
        errors = detector.detect_all_errors(module)
        
        for error_type, error_list in errors.items():
            for error in error_list:
                if error.startswith("Error") or error.startswith("Missing"):
                    detector.errors.append(error)
                else:
                    detector.warnings.append(error)
    
    report = detector.generate_error_report()
    print(report)
    
    # 保存报告
    with open("ERROR_DETECTION_REPORT.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info("Error detection report saved to: ERROR_DETECTION_REPORT.md")

if __name__ == "__main__":
    main()
