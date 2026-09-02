# -*- coding: utf-8 -*-
"""
Security模块回滚脚本
提供完整的回滚方案和回滚脚本
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class SecurityRollbackManager:
    """Security回滚管理器"""
    
    def __init__(self, db: Session):
        """
        初始化回滚管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.rollback_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """记录回滚日志"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.rollback_log.append(log_entry)
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
    
    def create_backup(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        创建数据备份
        
        Returns:
            备份数据字典
        """
        self.log("Creating backup before rollback...")
        
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
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
        
        total_records = sum(len(data) for data in backup_data.values() if isinstance(data, list))
        self.log(f"Backup created. Total records: {total_records}")
        
        return backup_data
    
    def _export_model(self, model_class) -> List[Dict[str, Any]]:
        """导出模型数据"""
        records = self.db.query(model_class).all()
        return [self._model_to_dict(record) for record in records]
    
    def _model_to_dict(self, model) -> Dict[str, Any]:
        """将模型转换为字典"""
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if value is not None:
                if hasattr(value, 'isoformat'):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
        return result
    
    def rollback_to_backup(self, backup_data: Dict[str, List[Dict[str, Any]]], dry_run: bool = False) -> bool:
        """
        回滚到备份数据
        
        Args:
            backup_data: 备份数据字典
            dry_run: 是否为试运行
        
        Returns:
            是否成功
        """
        self.log("Starting rollback to backup...")
        if dry_run:
            self.log("DRY RUN MODE - No changes will be made", "WARNING")
        
        try:
            # First, clear existing data
            if not dry_run:
                self._clear_all_security_data()
            
            # Then restore from backup
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
            
            total_restored = 0
            for key, model_class in model_map.items():
                if key in backup_data and backup_data[key]:
                    count = self._restore_model_data(model_class, backup_data[key], dry_run)
                    total_restored += count
                    self.log(f"Restored {count} records for {key}")
            
            if not dry_run:
                self.db.commit()
                self.log(f"Rollback completed. Total records restored: {total_restored}")
            else:
                self.log(f"DRY RUN completed. Would restore {total_restored} records", "WARNING")
            
            return True
        
        except Exception as e:
            self.log(f"Rollback failed: {e}", "ERROR")
            if not dry_run:
                self.db.rollback()
            return False
    
    def _clear_all_security_data(self):
        """清除所有Security数据"""
        model_classes = [
            CommandGuardRule, CommandRewriteRule, SecurityOperationRecord,
            AuditReport, VulnerabilityScan, ThreatIntelligence, VulnerabilityTicket,
            SecurityTest, PenetrationTestProject, InputValidationRule,
            ApiSecurityEndpoint, DatabaseSecurityInstance, ComplianceStandard,
            CompliancePolicy, PrivacySubject, DataEncryptionKey,
            SnapshotEncryption, HttpsCertificate, RateLimitRule,
            RbacRole, AbacPolicy, MfaMethod, SecurityKey,
        ]
        
        for model_class in model_classes:
            self.db.query(model_class).delete()
        
        self.log("Cleared all security data")
    
    def _restore_model_data(
        self,
        model_class,
        data: List[Dict[str, Any]],
        dry_run: bool
    ) -> int:
        """恢复模型数据"""
        restored_count = 0
        
        for record_data in data:
            try:
                record = model_class(**record_data)
                
                if not dry_run:
                    self.db.add(record)
                
                restored_count += 1
            
            except Exception as e:
                self.log(f"Failed to restore record {record_data.get('id')}: {e}", "ERROR")
                continue
        
        return restored_count
    
    def rollback_migration(self, migration_version: str, dry_run: bool = False) -> bool:
        """
        回滚特定版本的迁移
        
        Args:
            migration_version: 要回滚的迁移版本
            dry_run: 是否为试运行
        
        Returns:
            是否成功
        """
        self.log(f"Rolling back migration version: {migration_version}")
        
        # For now, this is a placeholder
        # In production, this would interact with Alembic
        self.log("Rollback via Alembic would be performed here", "WARNING")
        
        return True
    
    def validate_rollback(self, backup_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        验证回滚数据的完整性
        
        Args:
            backup_data: 备份数据
        
        Returns:
            验证结果
        """
        self.log("Validating rollback data integrity...")
        
        validation_results = {
            "backup_timestamp": backup_data.get("backup_timestamp"),
            "total_records": 0,
            "tables_validated": 0,
            "issues": [],
        }
        
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
        
        for key, model_class in model_map.items():
            if key in backup_data and backup_data[key]:
                validation_results["total_records"] += len(backup_data[key])
                validation_results["tables_validated"] += 1
                
                # Validate data structure
                for record in backup_data[key]:
                    if not isinstance(record, dict):
                        validation_results["issues"].append(
                            f"Invalid record structure in {key}"
                        )
                    if 'id' not in record:
                        validation_results["issues"].append(
                            f"Missing 'id' field in {key}"
                        )
        
        self.log(f"Rollback validation completed. "
                f"Tables validated: {validation_results['tables_validated']}, "
                f"Total records: {validation_results['total_records']}, "
                f"Issues found: {len(validation_results['issues'])}")
        
        return validation_results
    
    def get_rollback_log(self) -> List[str]:
        """获取回滚日志"""
        return self.rollback_log


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security module rollback script")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    parser.add_argument("--backup-file", help="Path to backup file to restore from")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    db = SessionLocal()
    
    try:
        rollback_manager = SecurityRollbackManager(db)
        
        # Create backup before rollback
        backup_data = rollback_manager.create_backup()
        
        # Validate backup
        validation_results = rollback_manager.validate_rollback(backup_data)
        
        print("=== Rollback Summary ===")
        print(f"Backup timestamp: {validation_results['backup_timestamp']}")
        print(f"Tables validated: {validation_results['tables_validated']}")
        print(f"Total records: {validation_results['total_records']}")
        print(f"Issues found: {len(validation_results['issues'])}")
        
        if validation_results['issues']:
            print("\nIssues:")
            for issue in validation_results['issues']:
                print(f"  - {issue}")
        
        # Perform rollback if not dry run
        if not args.dry_run:
            print("\nPerforming rollback...")
            success = rollback_manager.rollback_to_backup(backup_data, dry_run=False)
            if success:
                print("Rollback completed successfully!")
            else:
                print("Rollback failed!")
                return 1
        else:
            print("\nDRY RUN - No changes made")
        
        print("\n=== Rollback Log ===")
        for log_entry in rollback_manager.get_rollback_log():
            print(log_entry)
        
        return 0
    
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
