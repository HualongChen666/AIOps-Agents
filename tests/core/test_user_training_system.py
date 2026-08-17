# -*- coding: utf-8 -*-
"""Tests for core/user_training_system.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.user_training_system import (
    TrainingCourse,
    TrainingModule,
    TrainingType,
    UserTrainingSystem,
    get_user_training_system,
)


def test_get_user_training_system():
    system = get_user_training_system()
    assert isinstance(system, UserTrainingSystem)


def test_list_and_get_courses():
    system = UserTrainingSystem()
    assert system.get_course("onboarding") is not None
    courses = system.list_courses()
    assert len(courses) >= 1
    filtered = system.list_courses(training_type=TrainingType.TECHNICAL)
    assert all(c["training_type"] == "technical" for c in filtered)


def test_register_course_and_module():
    system = UserTrainingSystem()
    course = TrainingCourse(
        course_id="c1",
        course_name="C1",
        training_type=TrainingType.TECHNICAL,
        description="desc",
    )
    system.register_course(course)
    module = TrainingModule(module_id="m1", module_name="M1", course_id="c1")
    system.register_module(module)
    assert system.get_course("c1")["course_name"] == "C1"


@pytest.mark.asyncio
async def test_enroll_and_update_progress(tmp_path):
    system = UserTrainingSystem({"training_dir": str(tmp_path)})
    enrollment_id = await system.enroll_user("u1", "onboarding")
    assert enrollment_id is not None
    assert len(system.get_user_enrollments(user_id="u1")) == 1
    assert await system.update_progress(enrollment_id, 100.0, score=95.0) is True
    assert system.completed_enrollments == 1
    assert await system.generate_training_report(user_id="u1") is not None


def test_statistics():
    system = UserTrainingSystem()
    stats = system.get_statistics()
    assert "total_courses" in stats
    assert "total_enrollments" in stats
