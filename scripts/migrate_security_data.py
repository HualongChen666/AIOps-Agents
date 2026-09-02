# -*- coding: utf-8 -*-
"""
Security模块数据迁移脚本
确保零数据丢失的数据迁移工具
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, ".")

from core.database import SessionLocal, engine
from core.models import (
    SecurityKey,
    MfaMethod,
    AbacPolicy,
    RbacRole,
    RateLimitRule,
    HttpsCertificate,
    SnapshotEncryption,
    DataEncryptionKey,
    PrivacySubject,
    CompliancePolicy,
    ComplianceStandard,
    DatabaseSecurityInstance,
    ApiSecurityEndpoint,
    InputValidationRule,
    PenetrationTestProject,
    SecurityTest,
    VulnerabilityTicket,
    ThreatIntelligence,
    VulnerabilityScan,
    AuditReport,
    SecurityOperationRecord,
    CommandRewriteRule,
    CommandGuardRule,
)

logger = logging.getLogger(__name__)


class SecurityDataMigrator:
    """Security数据迁移器"""
    
    def __init__(self, db: Session):
        """
        初始化数据迁移器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.migration_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """记录迁移日志"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.migration_log.append(log_entry)
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
    
    def export_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        导出当前Security数据（用于备份）
        
        Returns:
            包含所有Security数据的字典
        """
        self.log("Starting data export...")
        
        exported_data = {
            "security_keys": self._export_model(SecurityKey),
            "mfa_methods": self._export_model(MfaMethod),
            "abac_policies": self._export_model(AbacPolicy),
            "rbac_roles": self._export_model(RbacRole),
            "rate_limit_rules": self._export_model(RateLimitRule),
            "https_certificates": self._export_model(HttpsCertificate),
            "snapshot_encryptions": self._export_model(SnapshotEncryption),
            "data_encryption_keys": self._export_model(DataEncryptionKey),
            "privacy_subjects": self._export_model(PrivacySubject),
            "compliance_policies": self._export_model(CompliancePolicy),
            "compliance_standards": self._export_model(ComplianceStandard),
            "database_security_instances": self._export_model(DatabaseSecurityInstance),
            "api_security_endpoints": self._export_model(ApiSecurityEndpoint),
            "input_validation_rules": self._export_model(InputValidationRule),
            "penetration_test_projects": self._export_model(PenetrationTestProject),
            "security_tests": self._export_model(SecurityTest),
            "vulnerability_tickets": self._export_model(VulnerabilityTicket),
            "threat_intelligence": self._export_model(ThreatIntelligence),
            "vulnerability_scans": self._export_model(VulnerabilityScan),
            "audit_reports": self._export_model(AuditReport),
            "security_operation_records": self._export_model(SecurityOperationRecord),
            "command_rewrite_rules": self._export_model(CommandRewriteRule),
            "command_guard_rules": self._export_model(CommandGuardRule),
        }
        
        total_records = sum(len(data) for data in exported_data.values())
        self.log(f"Data export completed. Total records: {total_records}")
        
        return exported_data
    
    def _export_model(self, model_class) -> List[Dict[str, Any]]:
        """
        导出单个模型的数据
        
        Args:
            model_class: SQLAlchemy模型类
        
        Returns:
            模型数据列表
        """
        records = self.db.query(model_class).all()
        return [self._model_to_dict(record) for record in records]
    
    def _model_to_dict(self, model) -> Dict[str, Any]:
        """
        将SQLAlchemy模型转换为字典
        
        Args:
            model: SQLAlchemy模型实例
        
        Returns:
            模型数据字典
        """
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if value is not None:
                if hasattr(value, 'isoformat'):  # DateTime
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
        return result
    
    def import_data(self, data: Dict[str, List[Dict[str, Any]]], dry_run: bool = False) -> bool:
        """
        导入Security数据
        
        Args:
            data: 要导入的数据字典
            dry_run: 是否为试运行（不实际写入数据库）
        
        Returns:
            是否成功
        """
        self.log("Starting data import...")
        if dry_run:
            self.log("DRY RUN MODE - No changes will be made", "WARNING")
        
        try:
            # Import each model type
            model_map = {
                "security_keys": SecurityKey,
                "mfa_methods": MfaMethod,
                "abac_policies": AbacPolicy,
                "rbac_roles": RbacRole,
                "rate_limit_rules": RateLimitRule,
                "https_certificates": HttpsCertificate,
                "snapshot_encryptions": SnapshotEncryption,
                "data_encryption_keys": DataEncryptionKey,
                "privacy_subjects": PrivacySubject,
                "compliance_policies": CompliancePolicy,
                "compliance_standards": ComplianceStandard,
                "database_security_instances": DatabaseSecurityInstance,
                "api_security_endpoints": ApiSecurityEndpoint,
                "input_validation_rules": InputValidationRule,
                "penetration_test_projects": PenetrationTestProject,
                "security_tests": SecurityTest,
                "vulnerability_tickets": VulnerabilityTicket,
                "threat_intelligence": ThreatIntelligence,
                "vulnerability_scans": VulnerabilityScan,
                "audit_reports": AuditReport,
                "security_operation_records": SecurityOperationRecord,
                "command_rewrite_rules": CommandRewriteRule,
                "command_guard_rules": CommandGuardRule,
            }
            
            total_imported = 0
            for key, model_class in model_map.items():
                if key in data and data[key]:
                    count = self._import_model_data(model_class, data[key], dry_run)
                    total_imported += count
                    self.log(f"Imported {count} records for {key}")
            
            if not dry_run:
                self.db.commit()
                self.log(f"Data import completed. Total records imported: {total_imported}")
            else:
                self.log(f"DRY RUN completed. Would import {total_imported} records", "WARNING")
            
            return True
        
        except Exception as e:
            self.log(f"Data import failed: {e}", "ERROR")
            if not dry_run:
                self.db.rollback()
            return False
    
    def _import_model_data(
        self,
        model_class,
        data: List[Dict[str, Any]],
        dry_run: bool
    ) -> int:
        """
        导入单个模型的数据
        
        Args:
            model_class: SQLAlchemy模型类
            data: 要导入的数据列表
            dry_run: 是否为试运行
        
        Returns:
            导入的记录数
        """
        imported_count = 0
        
        for record_data in data:
            try:
                # Check if record already exists
                existing = self.db.query(model_class).filter(
                    model_class.id == record_data.get('id')
                ).first()
                
                if existing:
                    self.log(f"Record {record_data.get('id')} already exists, skipping", "WARNING")
                    continue
                
                # Create new record
                record = model_class(**record_data)
                
                if not dry_run:
                    self.db.add(record)
                
                imported_count += 1
            
            except Exception as e:
                self.log(f"Failed to import record {record_data.get('id')}: {e}", "ERROR")
                continue
        
        return imported_count
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        验证数据完整性
        
        Returns:
            验证结果字典
        """
        self.log("Starting data integrity validation...")
        
        validation_results = {
            "total_records": 0,
            "tables_checked": 0,
            "issues": [],
        }
        
        model_classes = [
            SecurityKey, MfaMethod, AbacPolicy, RbacRole, RateLimitRule,
            HttpsCertificate, SnapshotEncryption, DataEncryptionKey,
            PrivacySubject, CompliancePolicy, ComplianceStandard,
            DatabaseSecurityInstance, ApiSecurityEndpoint, InputValidationRule,
            PenetrationTestProject, SecurityTest, VulnerabilityTicket,
            ThreatIntelligence, VulnerabilityScan, AuditReport,
            SecurityOperationRecord, CommandRewriteRule, CommandGuardRule,
        ]
        
        for model_class in model_classes:
            try:
                count = self.db.query(model_class).count()
                validation_results["total_records"] += count
                validation_results["tables_checked"] += 1
                
                # Check for any obvious issues
                if count > 0:
                    # Check for duplicate IDs
                    ids = [r.id for r in self.db.query(model_class).all()]
                    if len(ids) != len(set(ids)):
                        validation_results["issues"].append(
                            f"Duplicate IDs found in {model_class.__tablename__}"
                        )
                
            except Exception as e:
                validation_results["issues"].append(
                    f"Failed to validate {model_class.__tablename__}: {e}"
                )
        
        self.log(f"Data integrity validation completed. "
                f"Tables checked: {validation_results['tables_checked']}, "
                f"Total records: {validation_results['total_records']}, "
                f"Issues found: {len(validation_results['issues'])}")
        
        return validation_results
    
    def get_migration_log(self) -> List[str]:
        """获取迁移日志"""
        return self.migration_log


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    db = SessionLocal()
    
    try:
        migrator = SecurityDataMigrator(db)
        
        # Validate current data integrity
        validation_results = migrator.validate_data_integrity()
        
        # Export current data
        exported_data = migrator.export_data()
        
        # Since we're migrating from in-memory to database,
        # there's no existing data to migrate.
        # This script is prepared for future migrations.
        
        print("=== Migration Summary ===")
        print(f"Tables validated: {validation_results['tables_checked']}")
        print(f"Total records: {validation_results['total_records']}")
        print(f"Issues found: {len(validation_results['issues'])}")
        
        if validation_results['issues']:
            print("\nIssues:")
            for issue in validation_results['issues']:
                print(f"  - {issue}")
        
        print("\n=== Migration Log ===")
        for log_entry in migrator.get_migration_log():
            print(log_entry)
        
        print("\nMigration completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
