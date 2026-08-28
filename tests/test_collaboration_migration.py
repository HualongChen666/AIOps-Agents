# -*- coding: utf-8 -*-
"""
测试协作高级路由数据库迁移
验证所有端点都使用数据库存储，不再使用JSON文件
"""

import pytest
from sqlalchemy.orm import Session
from core.models import CollaborationTeamDB, CollaborationMemberDB, CollaborationPermissionDB, CollaborationActivityDB
from core.database import get_db


class TestCollaborationMigration:
    """测试协作数据库迁移"""

    def test_database_tables_exist(self):
        """验证数据库表存在"""
        db = next(get_db())
        try:
            # 检查表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            assert "collaboration_teams" in tables, "collaboration_teams表不存在"
            assert "collaboration_members" in tables, "collaboration_members表不存在"
            assert "collaboration_permissions" in tables, "collaboration_permissions表不存在"
            assert "collaboration_activities" in tables, "collaboration_activities表不存在"
        finally:
            db.close()

    def test_no_json_file_references(self):
        """验证代码中不再引用JSON文件"""
        import api.collaboration_advanced_router as router_module
        import inspect
        
        # 读取路由模块的源代码
        source = inspect.getsource(router_module)
        
        # 检查是否还有JSON文件引用
        assert "TEAMS_FILE" not in source, "代码中仍有TEAMS_FILE引用"
        assert "MEMBERS_FILE" not in source, "代码中仍有MEMBERS_FILE引用"
        assert "PERMISSIONS_FILE" not in source, "代码中仍有PERMISSIONS_FILE引用"
        assert "ACTIVITIES_FILE" not in source, "代码中仍有ACTIVITIES_FILE引用"
        assert "_load_json_file" not in source, "代码中仍有_load_json_file函数"
        assert "_save_json_file" not in source, "代码中仍有_save_json_file函数"

    def test_database_models_match(self):
        """验证数据库模型与预期一致"""
        db = next(get_db())
        try:
            # 检查CollaborationTeamDB的字段
            team = CollaborationTeamDB.__table__.columns
            required_fields = ['id', 'team_name', 'team_description', 'team_status']
            for field in required_fields:
                assert field in [c.name for c in team], f"CollaborationTeamDB缺少字段: {field}"
            
            # 检查CollaborationMemberDB的字段
            member = CollaborationMemberDB.__table__.columns
            required_fields = ['id', 'team_id', 'member_name', 'member_role']
            for field in required_fields:
                assert field in [c.name for c in member], f"CollaborationMemberDB缺少字段: {field}"
            
            # 检查CollaborationPermissionDB的字段
            permission = CollaborationPermissionDB.__table__.columns
            required_fields = ['id', 'team_id', 'permission_type', 'permission_level']
            for field in required_fields:
                assert field in [c.name for c in permission], f"CollaborationPermissionDB缺少字段: {field}"
            
            # 检查CollaborationActivityDB的字段
            activity = CollaborationActivityDB.__table__.columns
            required_fields = ['id', 'team_id', 'member_id', 'activity_type']
            for field in required_fields:
                assert field in [c.name for c in activity], f"CollaborationActivityDB缺少字段: {field}"
        finally:
            db.close()

    def test_create_team_uses_database(self):
        """测试创建团队使用数据库"""
        db = next(get_db())
        try:
            # 创建测试团队
            team = CollaborationTeamDB(
                id="TEST-TEAM-001",
                team_name="Test Team",
                team_description="Test team for migration",
                team_status="active"
            )
            db.add(team)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_team = db.query(CollaborationTeamDB).filter(
                CollaborationTeamDB.id == "TEST-TEAM-001"
            ).first()
            
            assert saved_team is not None, "团队未保存到数据库"
            assert saved_team.team_name == "Test Team", "团队名称不匹配"
            
            # 清理测试数据
            db.delete(saved_team)
            db.commit()
        finally:
            db.close()

    def test_create_member_uses_database(self):
        """测试创建成员使用数据库"""
        db = next(get_db())
        try:
            # 创建测试成员
            member = CollaborationMemberDB(
                id="TEST-MEMBER-001",
                team_id="TEST-TEAM-001",
                member_name="Test User",
                member_role="admin"
            )
            db.add(member)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_member = db.query(CollaborationMemberDB).filter(
                CollaborationMemberDB.id == "TEST-MEMBER-001"
            ).first()
            
            assert saved_member is not None, "成员未保存到数据库"
            assert saved_member.member_role == "admin", "角色不匹配"
            
            # 清理测试数据
            db.delete(saved_member)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])