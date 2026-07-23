# -*- coding: utf-8 -*-
"""测试用户培训系统模块"""

import pytest


class TestUserTrainingSystemModule:
    """测试用户培训系统模块"""

    def test_user_training_system_module_exists(self):
        """测试用户培训系统模块存在"""
        from core import user_training_system

        assert user_training_system is not None

    def test_user_training_system_has_enums(self):
        """测试用户培训系统模块有枚举"""
        from core import user_training_system

        # 检查模块有枚举
        assert hasattr(user_training_system, "TrainingType")
        assert hasattr(user_training_system, "TrainingStatus")
        assert hasattr(user_training_system, "EnrollmentStatus")

    def test_user_training_system_has_dataclasses(self):
        """测试用户培训系统模块有数据类"""
        from core import user_training_system

        # 检查模块有数据类
        assert hasattr(user_training_system, "TrainingCourse")
        assert hasattr(user_training_system, "TrainingModule")
        assert hasattr(user_training_system, "UserEnrollment")

    def test_user_training_system_has_classes(self):
        """测试用户培训系统模块有类"""
        from core import user_training_system

        # 检查模块有类
        assert hasattr(user_training_system, "UserTrainingSystem")

    def test_user_training_system_has_functions(self):
        """测试用户培训系统模块有函数"""
        from core import user_training_system

        # 检查模块有函数
        assert hasattr(user_training_system, "get_user_training_system")


class TestTrainingType:
    """测试培训类型枚举"""

    def test_training_type_values(self):
        """测试培训类型值"""
        from core.user_training_system import TrainingType

        assert TrainingType.ONBOARDING.value == "onboarding"
        assert TrainingType.TECHNICAL.value == "technical"
        assert TrainingType.OPERATIONAL.value == "operational"
        assert TrainingType.SECURITY.value == "security"
        assert TrainingType.COMPLIANCE.value == "compliance"
        assert TrainingType.ADVANCED.value == "advanced"


class TestTrainingStatus:
    """测试培训状态枚举"""

    def test_training_status_values(self):
        """测试培训状态值"""
        from core.user_training_system import TrainingStatus

        assert TrainingStatus.DRAFT.value == "draft"
        assert TrainingStatus.PUBLISHED.value == "published"
        assert TrainingStatus.ARCHIVED.value == "archived"


class TestEnrollmentStatus:
    """测试注册状态枚举"""

    def test_enrollment_status_values(self):
        """测试注册状态值"""
        from core.user_training_system import EnrollmentStatus

        assert EnrollmentStatus.ENROLLED.value == "enrolled"
        assert EnrollmentStatus.IN_PROGRESS.value == "in_progress"
        assert EnrollmentStatus.COMPLETED.value == "completed"
        assert EnrollmentStatus.FAILED.value == "failed"
        assert EnrollmentStatus.WITHDRAWN.value == "withdrawn"


class TestTrainingCourse:
    """测试培训课程数据类"""

    def test_training_course_creation(self):
        """测试培训课程创建"""
        from core.user_training_system import TrainingCourse, TrainingStatus, TrainingType

        course = TrainingCourse(
            course_id="test_course",
            course_name="Test Course",
            training_type=TrainingType.TECHNICAL,
            description="Test description",
        )

        assert course.course_id == "test_course"
        assert course.course_name == "Test Course"
        assert course.training_type == TrainingType.TECHNICAL
        assert course.description == "Test description"
        assert course.status == TrainingStatus.DRAFT


class TestTrainingModule:
    """测试培训模块数据类"""

    def test_training_module_creation(self):
        """测试培训模块创建"""
        from core.user_training_system import TrainingModule

        module = TrainingModule(
            module_id="test_module",
            module_name="Test Module",
            course_id="test_course",
            content="Test content",
        )

        assert module.module_id == "test_module"
        assert module.module_name == "Test Module"
        assert module.course_id == "test_course"
        assert module.content == "Test content"


class TestUserEnrollment:
    """测试用户注册数据类"""

    def test_user_enrollment_creation(self):
        """测试用户注册创建"""
        from core.user_training_system import EnrollmentStatus, UserEnrollment

        enrollment = UserEnrollment(
            enrollment_id="test_enrollment",
            user_id="test_user",
            course_id="test_course",
        )

        assert enrollment.enrollment_id == "test_enrollment"
        assert enrollment.user_id == "test_user"
        assert enrollment.course_id == "test_course"
        assert enrollment.status == EnrollmentStatus.ENROLLED


class TestUserTrainingSystem:
    """测试用户培训系统类"""

    def test_user_training_system_initialization(self):
        """测试用户培训系统初始化"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        assert system.config == {}
        assert len(system.training_courses) > 0
        assert len(system.training_modules) == 0
        assert len(system.user_enrollments) == 0

    def test_user_training_system_initialization_with_config(self):
        """测试用户培训系统初始化（带配置）"""
        from core.user_training_system import UserTrainingSystem

        config = {"training_dir": "./test_training"}
        system = UserTrainingSystem(config)

        assert system.config == config

    def test_user_training_system_default_courses(self):
        """测试用户培训系统默认课程"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        assert "onboarding" in system.training_courses
        assert "technical_basics" in system.training_courses
        assert "operations" in system.training_courses
        assert "security" in system.training_courses

    def test_register_course(self):
        """测试注册课程"""
        from core.user_training_system import (
            TrainingCourse,
            TrainingType,
            UserTrainingSystem,
        )

        system = UserTrainingSystem()
        initial_count = system.total_courses
        course = TrainingCourse(
            course_id="new_course",
            course_name="New Course",
            training_type=TrainingType.TECHNICAL,
            description="New course description",
        )

        system.register_course(course)

        assert "new_course" in system.training_courses
        assert system.total_courses == initial_count + 1

    def test_register_module(self):
        """测试注册模块"""
        from core.user_training_system import TrainingModule, UserTrainingSystem

        system = UserTrainingSystem()
        module = TrainingModule(
            module_id="new_module",
            module_name="New Module",
            course_id="test_course",
            content="New module content",
        )

        system.register_module(module)

        assert "new_module" in system.training_modules

    @pytest.mark.asyncio
    async def test_enroll_user(self):
        """测试用户注册"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        enrollment_id = await system.enroll_user("user1", "onboarding")

        assert enrollment_id.startswith("enroll_user1_onboarding_")
        assert enrollment_id in system.user_enrollments
        assert system.total_enrollments == 1

    @pytest.mark.asyncio
    async def test_enroll_user_invalid_course(self):
        """测试用户注册（无效课程）"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        with pytest.raises(ValueError):
            await system.enroll_user("user1", "invalid_course")

    @pytest.mark.asyncio
    async def test_update_progress(self):
        """测试更新进度"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()
        enrollment_id = await system.enroll_user("user1", "onboarding")

        result = await system.update_progress(enrollment_id, 50.0, 80.0)

        assert result is True
        assert system.user_enrollments[enrollment_id].progress == 50.0
        assert system.user_enrollments[enrollment_id].score == 80.0

    @pytest.mark.asyncio
    async def test_update_progress_complete(self):
        """测试更新进度（完成）"""
        from core.user_training_system import EnrollmentStatus, UserTrainingSystem

        system = UserTrainingSystem()
        enrollment_id = await system.enroll_user("user1", "onboarding")

        result = await system.update_progress(enrollment_id, 100.0)

        assert result is True
        assert system.user_enrollments[enrollment_id].status == EnrollmentStatus.COMPLETED
        assert system.user_enrollments[enrollment_id].completed_at is not None
        assert system.completed_enrollments == 1

    @pytest.mark.asyncio
    async def test_update_progress_invalid_enrollment(self):
        """测试更新进度（无效注册）"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        result = await system.update_progress("invalid_enrollment", 50.0)

        assert result is False

    def test_get_course(self):
        """测试获取课程"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        course = system.get_course("onboarding")

        assert course is not None
        assert course["course_id"] == "onboarding"
        assert course["course_name"] == "System Onboarding"

    def test_get_course_invalid(self):
        """测试获取课程（无效）"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        course = system.get_course("invalid_course")

        assert course is None

    def test_list_courses(self):
        """测试列出课程"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        courses = system.list_courses()

        assert len(courses) > 0
        assert any(c["course_id"] == "onboarding" for c in courses)

    def test_list_courses_with_filter(self):
        """测试列出课程（带过滤器）"""
        from core.user_training_system import TrainingType, UserTrainingSystem

        system = UserTrainingSystem()

        courses = system.list_courses(training_type=TrainingType.ONBOARDING)

        assert len(courses) > 0
        assert all(c["training_type"] == "onboarding" for c in courses)

    def test_get_user_enrollments(self):
        """测试获取用户注册"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        enrollments = system.get_user_enrollments()

        assert isinstance(enrollments, list)

    @pytest.mark.asyncio
    async def test_get_user_enrollments_with_filter(self):
        """测试获取用户注册（带过滤器）"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()
        await system.enroll_user("user1", "onboarding")

        enrollments = system.get_user_enrollments(user_id="user1")

        assert len(enrollments) == 1
        assert enrollments[0]["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_generate_training_report(self):
        """测试生成培训报告"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()
        await system.enroll_user("user1", "onboarding")

        report = await system.generate_training_report()

        assert "generated_at" in report
        assert "summary" in report
        assert "enrollments" in report

    def test_get_statistics(self):
        """测试获取统计信息"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        stats = system.get_statistics()

        assert "total_courses" in stats
        assert "published_courses" in stats
        assert "total_enrollments" in stats
        assert "completed_enrollments" in stats
        assert "completion_rate" in stats


class TestGetUserTrainingSystem:
    """测试获取用户培训系统"""

    def test_get_user_training_system(self):
        """测试获取用户培训系统"""
        from core.user_training_system import get_user_training_system

        system = get_user_training_system()

        assert system is not None
        assert hasattr(system, "training_courses")

    def test_get_user_training_system_with_config(self):
        """测试获取用户培训系统（带配置）"""
        from core.user_training_system import get_user_training_system

        config = {"training_dir": "./test_training"}
        system = get_user_training_system(config)

        assert system.config == config


class TestUserTrainingSystemIntegration:
    """测试用户培训系统集成"""

    @pytest.mark.asyncio
    async def test_complete_training_workflow(self):
        """测试完整培训工作流"""
        from core.user_training_system import UserTrainingSystem

        system = UserTrainingSystem()

        # Enroll user
        enrollment_id = await system.enroll_user("user1", "onboarding")
        assert enrollment_id in system.user_enrollments

        # Update progress
        await system.update_progress(enrollment_id, 50.0)
        assert system.user_enrollments[enrollment_id].progress == 50.0

        # Complete course
        await system.update_progress(enrollment_id, 100.0)
        assert system.user_enrollments[enrollment_id].status.value == "completed"

        # Get statistics
        stats = system.get_statistics()
        assert stats["completed_enrollments"] == 1

        # Generate report
        report = await system.generate_training_report()
        assert report["summary"]["completed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
