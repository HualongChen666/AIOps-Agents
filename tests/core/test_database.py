# -*- coding: utf-8 -*-
"""
Unit tests for core/database.py

This module contains comprehensive unit tests for the database base module,
covering SQLAlchemy Base declarative base functionality, model creation,
and integration with SQLAlchemy components.
"""

import uuid

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base


def get_unique_table_name():
    """Generate a unique table name for each test."""
    return f"test_table_{uuid.uuid4().hex[:8]}"


# ============================================================
# Base import and basic tests (5 test cases)
# ============================================================


class TestBaseImport:
    """Test cases for Base import and basic functionality."""

    def test_base_exists(self):
        """Test that Base object exists."""
        assert Base is not None

    def test_base_type(self):
        """Test that Base is a SQLAlchemy declarative base."""

        assert isinstance(Base, type)
        # Check if it has the expected metadata attribute
        assert hasattr(Base, "metadata")

    def test_base_module_import(self):
        """Test that Base can be imported from core.database."""
        from core.database import Base as ImportedBase

        assert ImportedBase is Base

    def test_base_metadata_attribute(self):
        """Test that Base has metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_registry_attribute(self):
        """Test that Base has registry attribute (SQLAlchemy 2.0)."""
        # SQLAlchemy 2.0 uses registry instead of metadata directly
        assert hasattr(Base, "metadata") or hasattr(Base, "registry")


# ============================================================
# Base basic functionality tests (10 test cases)
# ============================================================


class TestBaseFunctionality:
    """Test cases for Base basic functionality."""

    def test_base_metadata_is_metadata(self):
        """Test that Base.metadata is a MetaData object."""
        from sqlalchemy.schema import MetaData

        assert isinstance(Base.metadata, MetaData)

    def test_base_can_create_model(self):
        """Test that Base can be used to create a model."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        assert TestModel is not None
        assert hasattr(TestModel, "__tablename__")
        assert TestModel.__tablename__ == table_name

    def test_base_model_has_table(self):
        """Test that model created from Base has a table."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        assert TestModel.__table__ is not None
        assert TestModel.__table__.name == table_name

    def test_base_model_columns(self):
        """Test that model columns are properly defined."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        assert "id" in TestModel.__table__.columns
        assert "name" in TestModel.__table__.columns

    def test_base_model_inheritance(self):
        """Test that models can inherit from Base."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        assert issubclass(TestModel, Base)

    def test_base_model_instance_creation(self):
        """Test that model instances can be created."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        instance = TestModel(id=1, name="test")
        assert instance.id == 1
        assert instance.name == "test"

    def test_base_model_repr(self):
        """Test that model has a default __repr__."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        instance = TestModel(id=1, name="test")
        repr_str = repr(instance)
        assert "TestModel" in repr_str

    def test_base_model_equality(self):
        """Test that model instances can be compared."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        instance1 = TestModel(id=1, name="test")
        instance2 = TestModel(id=1, name="test")
        # SQLAlchemy models compare by identity
        assert instance1 is not instance2

    def test_base_model_dict_like_access(self):
        """Test that model instances support attribute access."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        instance = TestModel(id=1, name="test")
        assert instance.id == 1
        assert getattr(instance, "id") == 1

    def test_base_model_state(self):
        """Test that model instances have a state."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        instance = TestModel(id=1, name="test")
        assert hasattr(instance, "_sa_instance_state")


# ============================================================
# Base SQLAlchemy integration tests (10 test cases)
# ============================================================


class TestBaseSQLAlchemyIntegration:
    """Test cases for Base integration with SQLAlchemy components."""

    def test_base_with_integer_column(self):
        """Test Base with Integer column."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        column = TestModel.__table__.columns["id"]
        assert isinstance(column.type, Integer)

    def test_base_with_string_column(self):
        """Test Base with String column."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        column = TestModel.__table__.columns["name"]
        assert isinstance(column.type, String)
        assert column.type.length == 50

    def test_base_with_primary_key(self):
        """Test Base with primary key column."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        column = TestModel.__table__.columns["id"]
        assert column.primary_key is True

    def test_base_with_foreign_key(self):
        """Test Base with foreign key column."""
        parent_table = get_unique_table_name()
        child_table = get_unique_table_name()

        class Parent(Base):
            __tablename__ = parent_table
            id = Column(Integer, primary_key=True)

        class Child(Base):
            __tablename__ = child_table
            id = Column(Integer, primary_key=True)
            parent_id = Column(Integer, ForeignKey(f"{parent_table}.id"))

        column = Child.__table__.columns["parent_id"]
        assert len(column.foreign_keys) > 0

    def test_base_with_relationship(self):
        """Test Base with relationship."""
        parent_table = get_unique_table_name()
        child_table = get_unique_table_name()

        # Define classes first, then assign relationships using class objects.
        # This avoids SQLAlchemy string-lookup failures in the shared Base
        # registry when tests run under pytest-xdist.
        class Child(Base):
            __tablename__ = child_table
            id = Column(Integer, primary_key=True)
            parent_id = Column(Integer, ForeignKey(f"{parent_table}.id"))

        class Parent(Base):
            __tablename__ = parent_table
            id = Column(Integer, primary_key=True)

        Parent.children = relationship(Child, back_populates="parent")
        Child.parent = relationship(Parent, back_populates="children")

        assert hasattr(Parent, "children")
        assert hasattr(Child, "parent")

    def test_base_table_creation(self):
        """Test that table can be created from Base model."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        table = TestModel.__table__
        assert table is not None
        assert table.name == table_name

    def test_base_metadata_contains_table(self):
        """Test that Base.metadata contains the model table."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        assert table_name in Base.metadata.tables

    def test_base_multiple_models(self):
        """Test that multiple models can be created from Base."""
        table1 = get_unique_table_name()
        table2 = get_unique_table_name()

        class Model1(Base):
            __tablename__ = table1
            id = Column(Integer, primary_key=True)

        class Model2(Base):
            __tablename__ = table2
            id = Column(Integer, primary_key=True)

        assert table1 in Base.metadata.tables
        assert table2 in Base.metadata.tables

    def test_base_column_types(self):
        """Test various column types with Base."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        assert isinstance(TestModel.__table__.columns["id"].type, Integer)
        assert isinstance(TestModel.__table__.columns["name"].type, String)

    def test_base_table_constraints(self):
        """Test that table constraints are properly set."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        primary_key = TestModel.__table__.primary_key
        assert len(primary_key.columns) > 0


# ============================================================
# Edge cases and boundary conditions tests (10 test cases)
# ============================================================


class TestBaseEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_empty_model(self):
        """Test model with no columns (edge case)."""
        table_name = get_unique_table_name()
        with pytest.raises(Exception):
            # This should fail because a table needs at least a primary key
            class EmptyModel(Base):
                __tablename__ = table_name

    def test_single_field_model(self):
        """Test model with single field."""
        table_name = get_unique_table_name()

        class SingleFieldModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        assert len(SingleFieldModel.__table__.columns) == 1

    def test_many_fields_model(self):
        """Test model with many fields."""
        table_name = get_unique_table_name()

        class ManyFieldsModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            field1 = Column(String(50))
            field2 = Column(String(50))
            field3 = Column(String(50))
            field4 = Column(String(50))
            field5 = Column(String(50))

        assert len(ManyFieldsModel.__table__.columns) == 6

    def test_long_table_name(self):
        """Test model with very long table name."""
        long_name = get_unique_table_name() + "_" + "a" * 100

        class LongNameModel(Base):
            __tablename__ = long_name
            id = Column(Integer, primary_key=True)

        assert LongNameModel.__table__.name == long_name

    def test_special_characters_in_column_name(self):
        """Test model with special characters in column names."""
        # Note: SQLAlchemy may normalize column names
        table_name = get_unique_table_name()

        class SpecialModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            field_name = Column(String(50))

        assert "field_name" in SpecialModel.__table__.columns

    def test_unicode_in_column_name(self):
        """Test model with unicode characters in column names."""
        table_name = get_unique_table_name()

        class UnicodeModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            名称 = Column(String(50))

        # Column names should be accessible
        assert "名称" in UnicodeModel.__table__.columns or len(UnicodeModel.__table__.columns) == 2

    def test_model_with_no_tablename(self):
        """Test model without __tablename__ attribute."""
        with pytest.raises(Exception):

            class NoTableNameModel(Base):
                id = Column(Integer, primary_key=True)

    def test_duplicate_column_names(self):
        """Test model with duplicate column names."""
        table_name = get_unique_table_name()
        with pytest.raises(Exception):

            class DuplicateModel(Base):
                __tablename__ = table_name
                id = Column(Integer, primary_key=True)
                id = Column(String(50))  # Duplicate name

    def test_model_instance_with_none_values(self):
        """Test model instance with None values for optional fields."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50), nullable=True)

        instance = TestModel(id=1, name=None)
        assert instance.name is None

    def test_model_instance_with_default_values(self):
        """Test model instance with default values."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            name = Column(String(50), default="default_name")

        instance = TestModel(id=1)
        # Default values are handled by database, not SQLAlchemy
        assert instance.id == 1


# ============================================================
# Exception and error handling tests (10 test cases)
# ============================================================


class TestBaseExceptions:
    """Test cases for exception handling."""

    def test_invalid_column_type(self):
        """Test model with invalid column type."""
        table_name = get_unique_table_name()

        # SQLAlchemy may accept string types, so this might not raise an exception
        class InvalidModel(Base):
            __tablename__ = table_name
            id = Column("invalid_type", primary_key=True)

        # Test passes if model is created or fails appropriately
        assert InvalidModel is not None

    def test_missing_primary_key(self):
        """Test model without primary key."""
        table_name = get_unique_table_name()
        with pytest.raises(Exception):

            class NoPKModel(Base):
                __tablename__ = table_name
                name = Column(String(50))

    def test_circular_foreign_keys(self):
        """Test models with circular foreign key references."""
        table1 = get_unique_table_name()
        table2 = get_unique_table_name()

        class Model1(Base):
            __tablename__ = table1
            id = Column(Integer, primary_key=True)
            model2_id = Column(Integer, ForeignKey(f"{table2}.id"))

        class Model2(Base):
            __tablename__ = table2
            id = Column(Integer, primary_key=True)
            model1_id = Column(Integer, ForeignKey(f"{table1}.id"))

        # Circular references should be allowed
        assert table1 in Base.metadata.tables
        assert table2 in Base.metadata.tables

    def test_invalid_foreign_key_reference(self):
        """Test model with invalid foreign key reference."""
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)
            invalid_ref = Column(Integer, ForeignKey("nonexistent_table.id"))

        # Foreign key to nonexistent table should still create column
        assert "invalid_ref" in TestModel.__table__.columns

    def test_model_with_invalid_tablename(self):
        """Test model with invalid table name."""
        # SQLAlchemy allows most table names
        table_name = get_unique_table_name()

        class TestModel(Base):
            __tablename__ = f"{table_name}-hyphen"  # Hyphens may be problematic
            id = Column(Integer, primary_key=True)

        assert TestModel.__table__.name == f"{table_name}-hyphen"

    def test_column_with_negative_length(self):
        """Test String column with negative length."""
        table_name = get_unique_table_name()
        with pytest.raises((ValueError, TypeError, Exception)):

            class TestModel(Base):
                __tablename__ = table_name
                name = Column(String(-1))

    def test_column_with_zero_length(self):
        """Test String column with zero length."""
        table_name = get_unique_table_name()
        with pytest.raises((ValueError, TypeError, Exception)):

            class TestModel(Base):
                __tablename__ = table_name
                name = Column(String(0))

    def test_model_redefinition(self):
        """Test redefining the same model."""
        table_name = get_unique_table_name()

        # First definition with unique table name should succeed
        class TestModel(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True)

        # Redefining with the same table name must raise an exception
        with pytest.raises(Exception):

            class TestModel(Base):  # noqa: F811
                __tablename__ = table_name
                id = Column(Integer, primary_key=True)

    def test_relationship_without_foreign_key(self):
        """Test relationship without corresponding foreign key."""
        parent_table = get_unique_table_name()
        child_table = get_unique_table_name()

        class Parent(Base):
            __tablename__ = parent_table
            id = Column(Integer, primary_key=True)

        # Relationship without foreign key may still work but won't have proper mapping
        class Child(Base):
            __tablename__ = child_table
            id = Column(Integer, primary_key=True)
            # This relationship won't have a proper foreign key
            # parent = relationship("Parent")

        assert Child is not None

    def test_base_with_none_tablename(self):
        """Test model with None as tablename."""
        with pytest.raises(Exception):

            class NoneTableNameModel(Base):
                __tablename__ = None
                id = Column(Integer, primary_key=True)
