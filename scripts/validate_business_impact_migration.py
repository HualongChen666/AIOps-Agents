# -*- coding: utf-8 -*-
"""
Business Impact Migration Validation Script
业务影响迁移验证脚本

验证JSON文件和数据库表的数据一致性
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def validate_migration(
    json_file: str, table_name: str, primary_key: str, db_url: str = None
) -> bool:
    """验证JSON文件和数据库表的数据一致性

    Args:
        json_file: JSON文件路径
        table_name: 数据库表名
        primary_key: 主键字段名
        db_url: 数据库连接URL (可选，默认使用config中的DATABASE_URL)

    Returns:
        bool: 数据一致性验证结果
    """
    # 读取JSON
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"JSON文件不存在: {json_file}")
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if not isinstance(json_data, list):
                json_data = []
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return False

    # 读取数据库
    try:
        if db_url is None:
            try:
                from config import DATABASE_URL
                db_url = DATABASE_URL
            except ImportError:
                print("无法导入DATABASE_URL，使用默认SQLite数据库")
                db_url = "sqlite:///data/aiops.db"

        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 使用SQLAlchemy ORM查询
        from core.models import (
            BusinessImpactAnalysisDB,
            BusinessImpactDependencyDB,
            BusinessImpactReportDB,
        )

        table_map = {
            "business_impact_analysis": BusinessImpactAnalysisDB,
            "business_impact_dependencies": BusinessImpactDependencyDB,
            "business_impact_reports": BusinessImpactReportDB,
        }

        model_class = table_map.get(table_name)
        if not model_class:
            print(f"未知的表名: {table_name}")
            session.close()
            return False

        db_data = session.query(model_class).all()
        session.close()
    except Exception as e:
        print(f"读取数据库失败: {e}")
        return False

    # 比较
    json_ids = set(item.get(primary_key) for item in json_data if item.get(primary_key))
    db_ids = set(getattr(item, primary_key) for item in db_data if hasattr(item, primary_key))

    missing_in_db = json_ids - db_ids
    extra_in_db = db_ids - json_ids

    total_json = len(json_ids)
    total_db = len(db_ids)

    print(f"=== 数据一致性验证: {table_name} ===")
    print(f"JSON记录数: {total_json}")
    print(f"数据库记录数: {total_db}")
    print(f"JSON中缺失: {len(missing_in_db)} 条")
    print(f"数据库中多余: {len(extra_in_db)} 条")

    if missing_in_db:
        print(f"JSON中缺失的ID: {list(missing_in_db)[:5]}...")  # 只显示前5个

    if extra_in_db:
        print(f"数据库中多余的ID: {list(extra_in_db)[:5]}...")  # 只显示前5个

    # 计算差异率
    if total_json > 0:
        diff_rate = (len(missing_in_db) + len(extra_in_db)) / total_json * 100
        print(f"差异率: {diff_rate:.2f}%")

        if diff_rate < 0.1:
            print("✅ 数据一致性验证通过（差异率 < 0.1%）")
            return True
        else:
            print(f"❌ 数据一致性验证失败（差异率 >= 0.1%）")
            return False
    else:
        print("⚠️ JSON文件为空，无法计算差异率")
        return True


def main():
    """主函数"""
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    # 验证业务影响分析
    analysis_file = data_dir / "business_impact_analysis.json"
    analysis_result = validate_migration(
        str(analysis_file), "business_impact_analysis", "id"
    )
    print()

    # 验证依赖关系
    dependencies_file = data_dir / "business_impact_dependencies.json"
    dependencies_result = validate_migration(
        str(dependencies_file), "business_impact_dependencies", "id"
    )
    print()

    # 验证报告
    reports_file = data_dir / "business_impact_reports.json"
    reports_result = validate_migration(str(reports_file), "business_impact_reports", "id")
    print()

    # 总体结果
    if analysis_result and dependencies_result and reports_result:
        print("✅ 所有数据一致性验证通过")
        sys.exit(0)
    else:
        print("❌ 数据一致性验证失败")
        sys.exit(1)


if __name__ == "__main__":
    main()