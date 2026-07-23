# -*- coding: utf-8 -*-
"""
User Training System (Phase 5)
Enterprise-grade user training system with learning management
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class TrainingType(Enum):
    """Training type"""

    ONBOARDING = "onboarding"
    TECHNICAL = "technical"
    OPERATIONAL = "operational"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    ADVANCED = "advanced"


class TrainingStatus(Enum):
    """Training status"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnrollmentStatus(Enum):
    """Enrollment status"""

    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"


@dataclass
class TrainingCourse:
    """Training course configuration"""

    course_id: str
    course_name: str
    training_type: TrainingType
    description: str
    duration_hours: int = 0
    difficulty_level: str = "intermediate"
    prerequisites: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    status: TrainingStatus = TrainingStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingModule:
    """Training module"""

    module_id: str
    module_name: str
    course_id: str
    content: str = ""
    duration_minutes: int = 0
    order: int = 0
    quiz: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserEnrollment:
    """User enrollment"""

    enrollment_id: str
    user_id: str
    course_id: str
    status: EnrollmentStatus = EnrollmentStatus.ENROLLED
    enrolled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class UserTrainingSystem:
    """Enterprise-grade user training system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize user training system

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Training courses
        self.training_courses: Dict[str, TrainingCourse] = {}
        self._initialize_default_courses()

        # Training modules
        self.training_modules: Dict[str, TrainingModule] = {}

        # User enrollments
        self.user_enrollments: Dict[str, UserEnrollment] = {}

        # Storage
        self.training_dir = Path(self.config.get("training_dir", "./training"))
        self.training_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.total_courses = 0
        self.total_enrollments = 0
        self.completed_enrollments = 0

        logger.info("User training system initialized")

    def _initialize_default_courses(self):
        """Initialize default training courses"""
        # Onboarding course
        self.training_courses["onboarding"] = TrainingCourse(
            course_id="onboarding",
            course_name="System Onboarding",
            training_type=TrainingType.ONBOARDING,
            description="Introduction to the AIOps Agent system",
            duration_hours=4,
            difficulty_level="beginner",
            modules=["onboarding_module_1", "onboarding_module_2", "onboarding_module_3"],
            status=TrainingStatus.PUBLISHED,
        )

        # Technical training
        self.training_courses["technical_basics"] = TrainingCourse(
            course_id="technical_basics",
            course_name="Technical Basics",
            training_type=TrainingType.TECHNICAL,
            description="Technical fundamentals of the system",
            duration_hours=8,
            difficulty_level="intermediate",
            modules=["tech_module_1", "tech_module_2"],
            status=TrainingStatus.PUBLISHED,
        )

        # Operational training
        self.training_courses["operations"] = TrainingCourse(
            course_id="operations",
            course_name="Operational Training",
            training_type=TrainingType.OPERATIONAL,
            description="Day-to-day operations training",
            duration_hours=6,
            difficulty_level="intermediate",
            modules=["ops_module_1", "ops_module_2"],
            status=TrainingStatus.PUBLISHED,
        )

        # Security training
        self.training_courses["security"] = TrainingCourse(
            course_id="security",
            course_name="Security Training",
            training_type=TrainingType.SECURITY,
            description="Security best practices and compliance",
            duration_hours=4,
            difficulty_level="intermediate",
            modules=["security_module_1"],
            status=TrainingStatus.PUBLISHED,
        )

        logger.info(f"Initialized {len(self.training_courses)} default training courses")

    def register_course(self, course: TrainingCourse) -> None:
        """
        Register training course

        Args:
            course: Training course
        """
        self.training_courses[course.course_id] = course
        self.total_courses += 1
        logger.info(f"Registered training course: {course.course_id}")

    def register_module(self, module: TrainingModule) -> None:
        """
        Register training module

        Args:
            module: Training module
        """
        self.training_modules[module.module_id] = module
        logger.info(f"Registered training module: {module.module_id}")

    async def enroll_user(self, user_id: str, course_id: str) -> str:
        """
        Enroll user in training course

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            Enrollment ID
        """
        if course_id not in self.training_courses:
            raise ValueError(f"Course not found: {course_id}")

        enrollment_id = (
            f"enroll_{user_id}_{course_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        enrollment = UserEnrollment(
            enrollment_id=enrollment_id,
            user_id=user_id,
            course_id=course_id,
            status=EnrollmentStatus.ENROLLED,
        )

        self.user_enrollments[enrollment_id] = enrollment
        self.total_enrollments += 1

        logger.info(f"Enrolled user {user_id} in course {course_id}")

        return enrollment_id

    async def update_progress(
        self, enrollment_id: str, progress: float, score: Optional[float] = None
    ) -> bool:
        """
        Update enrollment progress

        Args:
            enrollment_id: Enrollment ID
            progress: Progress percentage (0-100)
            score: Score (optional)

        Returns:
            Success status
        """
        if enrollment_id not in self.user_enrollments:
            return False

        enrollment = self.user_enrollments[enrollment_id]
        enrollment.progress = progress

        if score is not None:
            enrollment.score = score

        # Update status based on progress
        if progress == 100.0:
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.completed_at = datetime.now(timezone.utc)
            self.completed_enrollments += 1
        elif progress > 0:
            enrollment.status = EnrollmentStatus.IN_PROGRESS

        logger.info(f"Updated progress for enrollment {enrollment_id}: {progress}%")

        return True

    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get training course details

        Args:
            course_id: Course ID

        Returns:
            Course details
        """
        if course_id not in self.training_courses:
            return None

        course = self.training_courses[course_id]

        return {
            "course_id": course.course_id,
            "course_name": course.course_name,
            "training_type": course.training_type.value,
            "description": course.description,
            "duration_hours": course.duration_hours,
            "difficulty_level": course.difficulty_level,
            "prerequisites": course.prerequisites,
            "modules": course.modules,
            "status": course.status.value,
            "created_at": course.created_at.isoformat(),
            "updated_at": course.updated_at.isoformat() if course.updated_at else None,
        }

    def list_courses(
        self, training_type: Optional[TrainingType] = None, status: Optional[TrainingStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        List training courses with filters

        Args:
            training_type: Filter by type
            status: Filter by status

        Returns:
            List of courses
        """
        courses = []

        for course in self.training_courses.values():
            if training_type and course.training_type != training_type:
                continue
            if status and course.status != status:
                continue

            courses.append(
                {
                    "course_id": course.course_id,
                    "course_name": course.course_name,
                    "training_type": course.training_type.value,
                    "duration_hours": course.duration_hours,
                    "difficulty_level": course.difficulty_level,
                    "status": course.status.value,
                }
            )

        return courses

    def get_user_enrollments(
        self,
        user_id: Optional[str] = None,
        course_id: Optional[str] = None,
        status: Optional[EnrollmentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get user enrollments with filters

        Args:
            user_id: Filter by user ID
            course_id: Filter by course ID
            status: Filter by status

        Returns:
            List of enrollments
        """
        enrollments = []

        for enrollment in self.user_enrollments.values():
            if user_id and enrollment.user_id != user_id:
                continue
            if course_id and enrollment.course_id != course_id:
                continue
            if status and enrollment.status != status:
                continue

            enrollments.append(
                {
                    "enrollment_id": enrollment.enrollment_id,
                    "user_id": enrollment.user_id,
                    "course_id": enrollment.course_id,
                    "status": enrollment.status.value,
                    "enrolled_at": enrollment.enrolled_at.isoformat(),
                    "completed_at": (
                        enrollment.completed_at.isoformat() if enrollment.completed_at else None
                    ),
                    "progress": enrollment.progress,
                    "score": enrollment.score,
                }
            )

        return enrollments

    async def generate_training_report(
        self, user_id: Optional[str] = None, course_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate training report

        Args:
            user_id: Filter by user ID
            course_id: Filter by course ID

        Returns:
            Training report
        """
        enrollments = self.get_user_enrollments(user_id, course_id)

        total = len(enrollments)
        completed = len([e for e in enrollments if e["status"] == EnrollmentStatus.COMPLETED.value])
        in_progress = len(
            [e for e in enrollments if e["status"] == EnrollmentStatus.IN_PROGRESS.value]
        )

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "course_id": course_id,
            "summary": {
                "total_enrollments": total,
                "completed": completed,
                "in_progress": in_progress,
                "completion_rate": completed / total if total > 0 else 0.0,
            },
            "enrollments": enrollments,
        }

        # Save report
        report_path = (
            self.training_dir
            / f"training_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Generated training report: {report_path}")

        return report

    def get_statistics(self) -> Dict[str, Any]:
        """Get training statistics"""
        return {
            "total_courses": self.total_courses,
            "published_courses": len(
                [c for c in self.training_courses.values() if c.status == TrainingStatus.PUBLISHED]
            ),
            "total_enrollments": self.total_enrollments,
            "completed_enrollments": self.completed_enrollments,
            "completion_rate": (
                self.completed_enrollments / self.total_enrollments
                if self.total_enrollments > 0
                else 0.0
            ),
        }


def get_user_training_system(config: Optional[Dict[str, Any]] = None) -> UserTrainingSystem:
    """
    Factory function to get user training system instance

    Args:
        config: Optional configuration dictionary

    Returns:
        UserTrainingSystem: System instance
    """
    return UserTrainingSystem(config)
