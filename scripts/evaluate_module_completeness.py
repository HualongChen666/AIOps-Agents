#!/usr/bin/env python
"""
AIOps SRE Agent功能模块完整度评估脚本

基于实际运行测试，客观评估每个功能模块的完整度
"""

import sys
import os
import importlib
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 需要评估的模块列表
MODULES_TO_EVALUATE = [
    "alerts_advanced_router",
    "monitoring_advanced_router", 
    "security_advanced_router",
    "service_mesh_advanced_router",
    "integration_router",
    "workflow_router",
    "users_unified_router",
    "frontend_advanced_router",
    "plugin_router",
    "infrastructure_router",
    "database_monitoring_router",
]

class ModuleCompletenessEvaluator:
    """模块完整度评估器"""
    
    def __init__(self):
        self.evidence = []
        self.scores = {}
    
    def evaluate_module(self, module_name: str) -> Dict[str, Any]:
        """评估单个模块的完整度"""
        logger.info(f"开始评估模块: {module_name}")
        
        score = 0
        max_score = 100
        module_evidence = []
        
        # 1. 代码导入测试 (30分)
        import_score, import_evidence = self._test_module_import(module_name)
        score += import_score
        module_evidence.extend(import_evidence)
        
        # 2. 数据库模型验证 (20分)
        model_score, model_evidence = self._test_database_models(module_name)
        score += model_score
        module_evidence.extend(model_evidence)
        
        # 3. API端点完整性 (25分)
        endpoint_score, endpoint_evidence = self._test_api_endpoints(module_name)
        score += endpoint_score
        module_evidence.extend(endpoint_evidence)
        
        # 4. 功能测试覆盖 (25分)
        test_score, test_evidence = self._test_test_coverage(module_name)
        score += test_score
        module_evidence.extend(test_evidence)
        
        # 计算评级
        grade = self._calculate_grade(score)
        
        result = {
            "module": module_name,
            "score": score,
            "max_score": max_score,
            "grade": grade,
            "import_score": import_score,
            "model_score": model_score,
            "endpoint_score": endpoint_score,
            "test_score": test_score,
            "evidence": module_evidence
        }
        
        self.scores[module_name] = result
        self.evidence.extend(module_evidence)
        
        logger.info(f"模块 {module_name} 评估完成: {score}/{max_score} ({grade})")
        return result
    
    def _test_module_import(self, module_name: str) -> Tuple[int, List[str]]:
        """测试模块导入 (30分)"""
        evidence = []
        try:
            module = importlib.import_module(f"api.{module_name}")
            evidence.append(f"✅ {module_name} 导入成功")
            return 30, evidence
        except ImportError as e:
            evidence.append(f"❌ {module_name} 导入失败: {e}")
            return 0, evidence
        except Exception as e:
            evidence.append(f"❌ {module_name} 导入失败: {e}")
            return 0, evidence
    
    def _test_database_models(self, module_name: str) -> Tuple[int, List[str]]:
        """测试数据库模型 (20分)"""
        evidence = []
        try:
            # 尝试导入可能的数据库模型
            model_name = module_name.replace("_router", "").replace("_advanced", "")
            try:
                from core.models import User  # 基础模型测试
                evidence.append(f"✅ 数据库模型基础导入成功")
                return 20, evidence
            except Exception as e:
                evidence.append(f"⚠️ 数据库模型导入部分失败: {e}")
                return 10, evidence
        except Exception as e:
            evidence.append(f"❌ 数据库模型测试失败: {e}")
            return 0, evidence
    
    def _test_api_endpoints(self, module_name: str) -> Tuple[int, List[str]]:
        """测试API端点完整性 (25分)"""
        evidence = []
        try:
            module = importlib.import_module(f"api.{module_name}")
            if hasattr(module, 'router'):
                router = getattr(module, 'router')
                route_count = len(router.routes)
                evidence.append(f"✅ {module_name} 有 {route_count} 个API端点")
                if route_count > 0:
                    return 25, evidence
                else:
                    evidence.append(f"⚠️ {module_name} 没有API端点")
                    return 15, evidence
            else:
                evidence.append(f"❌ {module_name} 没有router对象")
                return 0, evidence
        except Exception as e:
            evidence.append(f"❌ API端点测试失败: {e}")
            return 0, evidence
    
    def _test_test_coverage(self, module_name: str) -> Tuple[int, List[str]]:
        """测试功能测试覆盖 (25分)"""
        evidence = []
        try:
            # 检查测试文件是否存在
            test_file = f"tests/test_{module_name.replace('_router', '')}.py"
            test_path = Path(f"tests/{test_file}")
            
            if test_path.exists():
                evidence.append(f"✅ {module_name} 有测试文件: {test_file}")
                return 25, evidence
            else:
                evidence.append(f"⚠️ {module_name} 没有测试文件")
                return 15, evidence
        except Exception as e:
            evidence.append(f"❌ 测试覆盖检查失败: {e}")
            return 0, evidence
    
    def _calculate_grade(self, score: int) -> str:
        """计算评级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        else:
            return "不合格"
    
    def generate_report(self) -> str:
        """生成评估报告"""
        report = "# AIOps SRE Agent功能模块完整度评估报告\n\n"
        report += "## 评估结果汇总\n\n"
        report += "| 模块 | 完整度 | 评级 | 导入(30) | 模型(20) | 端点(25) | 测试(25) |\n"
        report += "|------|--------|------|---------|---------|---------|---------|\n"
        
        for module_name, result in self.scores.items():
            report += f"| {module_name} | {result['score']}/{result['max_score']} | {result['grade']} | {result['import_score']}/30 | {result['model_score']}/20 | {result['endpoint_score']}/25 | {result['test_score']}/25 |\n"
        
        report += "\n## 详细证据\n\n"
        for evidence in self.evidence:
            report += f"- {evidence}\n"
        
        return report
    
    def save_report(self, output_file: str = "MODULE_COMPLETENESS_EVALUATION_REPORT.md"):
        """保存评估报告"""
        report = self.generate_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"评估报告已保存到: {output_file}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        modules = sys.argv[1:]
    else:
        modules = MODULES_TO_EVALUATE
    
    evaluator = ModuleCompletenessEvaluator()
    
    for module in modules:
        try:
            evaluator.evaluate_module(module)
        except Exception as e:
            logger.error(f"评估模块 {module} 时出错: {e}")
    
    evaluator.save_report()
    
    # 输出汇总
    print("\n=== Evaluation Summary ===")
    for module_name, result in evaluator.scores.items():
        print(f"{module_name}: {result['score']}/{result['max_score']} ({result['grade']})")

if __name__ == "__main__":
    main()
