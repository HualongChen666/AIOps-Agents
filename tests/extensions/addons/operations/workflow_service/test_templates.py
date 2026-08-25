# -*- coding: utf-8 -*-
"""Tests for workflow_service templates module."""

import pytest
from schemas import WorkflowTemplate
from templates import TemplateManager


class TestTemplateManager:
    """Test cases for TemplateManager class."""

    def test_template_manager_initialization(self):
        """Test that TemplateManager initializes correctly."""
        manager = TemplateManager()
        assert len(manager._templates) == 0

    @pytest.mark.asyncio
    async def test_register_template(self, template_manager, workflow_template):
        """Test registering a workflow template."""
        template_id = await template_manager.register(workflow_template)
        assert template_id == workflow_template.template_id
        assert workflow_template.template_id in template_manager._templates

    @pytest.mark.asyncio
    async def test_register_multiple_templates(self, template_manager):
        """Test registering multiple templates."""
        for i in range(5):
            template = WorkflowTemplate(
                template_id=f"template-{i}",
                name=f"Template {i}",
                source="echo test",
            )
            await template_manager.register(template)

        assert len(template_manager._templates) == 5

    @pytest.mark.asyncio
    async def test_register_overwrites_existing(self, template_manager, workflow_template):
        """Test that registering with same ID overwrites existing."""
        await template_manager.register(workflow_template)

        # Update and register again
        workflow_template.name = "Updated Name"
        await template_manager.register(workflow_template)

        stored = await template_manager.get(workflow_template.template_id)
        assert stored.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_get_template(self, template_manager, workflow_template):
        """Test retrieving a registered template."""
        await template_manager.register(workflow_template)
        retrieved = await template_manager.get(workflow_template.template_id)

        assert retrieved is not None
        assert retrieved.template_id == workflow_template.template_id
        assert retrieved.name == workflow_template.name

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_manager):
        """Test retrieving a non-existent template returns None."""
        retrieved = await template_manager.get("non-existent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, template_manager):
        """Test listing templates when none are registered."""
        templates = await template_manager.list_templates()
        assert templates == []

    @pytest.mark.asyncio
    async def test_list_templates_with_data(self, template_manager, workflow_template):
        """Test listing templates with data."""
        await template_manager.register(workflow_template)
        templates = await template_manager.list_templates()

        assert len(templates) == 1
        assert templates[0].template_id == workflow_template.template_id

    @pytest.mark.asyncio
    async def test_list_templates_with_limit(self, template_manager):
        """Test listing templates with limit parameter."""
        for i in range(10):
            template = WorkflowTemplate(
                template_id=f"template-{i}",
                name=f"Template {i}",
                source="echo test",
            )
            await template_manager.register(template)

        templates = await template_manager.list_templates(limit=5)
        assert len(templates) == 5

    @pytest.mark.asyncio
    async def test_list_templates_limit_zero(self, template_manager):
        """Test listing templates with limit=0."""
        template = WorkflowTemplate(template_id="template-1", name="Test", source="echo test")
        await template_manager.register(template)

        templates = await template_manager.list_templates(limit=0)
        assert templates == []

    @pytest.mark.asyncio
    async def test_render_template(self, template_manager, workflow_template):
        """Test rendering a template with parameters."""
        await template_manager.register(workflow_template)
        params = {"message": "Hello World", "user": "TestUser"}

        rendered = await template_manager.render(workflow_template.template_id, params)

        assert "Hello World" in rendered
        assert "TestUser" in rendered

    @pytest.mark.asyncio
    async def test_render_template_not_found(self, template_manager):
        """Test rendering a non-existent template raises ValueError."""
        with pytest.raises(ValueError, match="Template .* not found"):
            await template_manager.render("non-existent", {})

    @pytest.mark.asyncio
    async def test_render_template_with_default_params(self, template_manager):
        """Test rendering with template default parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{ message }} from {{ user }}",
            default_params={"user": "system"},
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"message": "Hello"})

        assert "Hello" in rendered
        assert "system" in rendered

    @pytest.mark.asyncio
    async def test_render_template_params_override_defaults(self, template_manager):
        """Test that render params override template defaults."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{ message }} from {{ user }}",
            default_params={"user": "system", "message": "default"},
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"user": "custom"})

        # Should use custom user and default message
        assert "custom" in rendered
        assert "default" in rendered

    @pytest.mark.asyncio
    async def test_render_template_no_params(self, template_manager):
        """Test rendering template with no parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo static text",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", None)

        assert rendered == "echo static text"

    @pytest.mark.asyncio
    async def test_render_template_empty_params(self, template_manager):
        """Test rendering template with empty params dict."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo static text",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {})

        assert rendered == "echo static text"

    @pytest.mark.asyncio
    async def test_render_template_with_multiple_placeholders(self, template_manager):
        """Test rendering template with multiple placeholders."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="{{ a }} + {{ b }} = {{ c }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"a": 1, "b": 2, "c": 3})

        assert "1" in rendered
        assert "2" in rendered
        assert "3" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_special_characters(self, template_manager):
        """Test rendering template with special characters in params."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{ message }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render(
            "template-1", {"message": "Hello @#$%^&*() World!"}
        )

        assert "Hello @#$%^&*() World!" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_unicode(self, template_manager):
        """Test rendering template with unicode characters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{ message }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"message": "测试中文"})

        assert "测试中文" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_numbers(self, template_manager):
        """Test rendering template with numeric parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="count={{ count }}, value={{ value }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"count": 42, "value": 3.14})

        assert "42" in rendered
        assert "3.14" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_booleans(self, template_manager):
        """Test rendering template with boolean parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="enabled={{ enabled }}, active={{ active }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"enabled": True, "active": False})

        assert "True" in rendered
        assert "False" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_lists(self, template_manager):
        """Test rendering template with list parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="items={{ items }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"items": [1, 2, 3]})

        assert "[1, 2, 3]" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_dicts(self, template_manager):
        """Test rendering template with dict parameters."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="config={{ config }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"config": {"key": "value"}})

        assert "key" in rendered
        assert "value" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_whitespace_in_placeholder(self, template_manager):
        """Test rendering template with whitespace in placeholders."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{  message  }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"message": "test"})

        assert "test" in rendered

    @pytest.mark.asyncio
    async def test_render_template_partial_placeholder_match(self, template_manager):
        """Test that only exact placeholder matches are replaced."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="{{ message }} {{ message_id }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"message": "test"})

        assert "test" in rendered
        # message_id should not be replaced
        assert "{{ message_id }}" in rendered

    @pytest.mark.asyncio
    async def test_render_template_no_matching_placeholder(self, template_manager):
        """Test rendering when params don't match placeholders."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="echo {{ message }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"other": "value"})

        # Placeholder should remain unchanged
        assert "{{ message }}" in rendered

    @pytest.mark.asyncio
    async def test_render_source_directly(self, template_manager):
        """Test _render_source method directly."""
        source = "Hello {{ name }}, welcome to {{ place }}"
        params = {"name": "World", "place": "AIOPS"}

        rendered = template_manager._render_source(source, params)

        assert "Hello World" in rendered
        assert "welcome to AIOPS" in rendered

    @pytest.mark.asyncio
    async def test_render_source_empty_string(self, template_manager):
        """Test rendering empty source string."""
        rendered = template_manager._render_source("", {"key": "value"})
        assert rendered == ""

    @pytest.mark.asyncio
    async def test_render_source_no_placeholders(self, template_manager):
        """Test rendering source with no placeholders."""
        source = "static text with no placeholders"
        rendered = template_manager._render_source(source, {})

        assert rendered == source

    @pytest.mark.asyncio
    async def test_render_source_empty_params(self, template_manager):
        """Test rendering source with empty params."""
        source = "Hello {{ name }}"
        rendered = template_manager._render_source(source, {})

        # Placeholder should remain
        assert "{{ name }}" in rendered

    @pytest.mark.asyncio
    async def test_render_source_case_sensitive(self, template_manager):
        """Test that placeholder replacement is case-sensitive."""
        source = "{{ Name }} vs {{ name }}"
        params = {"name": "lower"}

        rendered = template_manager._render_source(source, params)

        # Only lowercase should be replaced
        assert "lower" in rendered
        assert "{{ Name }}" in rendered

    @pytest.mark.asyncio
    async def test_template_manager_isolation(self):
        """Test that different template manager instances are isolated."""
        manager1 = TemplateManager()
        manager2 = TemplateManager()

        template = WorkflowTemplate(template_id="template-1", name="Test", source="echo test")
        await manager1.register(template)

        assert "template-1" in manager1._templates
        assert "template-1" not in manager2._templates

    @pytest.mark.asyncio
    async def test_render_complex_template(self, template_manager):
        """Test rendering a complex template with multiple features."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Complex Template",
            source="""
            Workflow: {{ workflow_name }}
            Owner: {{ owner }}
            Environment: {{ env }}
            Timeout: {{ timeout }}s
            """,
            default_params={"env": "production", "timeout": 300},
        )
        await template_manager.register(template)

        rendered = await template_manager.render(
            "template-1", {"workflow_name": "TestWorkflow", "owner": "TeamA"}
        )

        assert "TestWorkflow" in rendered
        assert "TeamA" in rendered
        assert "production" in rendered
        assert "300" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_newlines(self, template_manager):
        """Test rendering template with newlines."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="line1\nline2\nline3",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {})

        assert "line1" in rendered
        assert "line2" in rendered
        assert "line3" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_tabs(self, template_manager):
        """Test rendering template with tabs."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="item1\titem2\titem3",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {})

        assert "item1" in rendered
        assert "item2" in rendered
        assert "item3" in rendered

    @pytest.mark.asyncio
    async def test_render_template_very_long_source(self, template_manager):
        """Test rendering template with very long source."""
        long_source = "echo " + " ".join([f"{{ item{i }}}" for i in range(100)])
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source=long_source,
        )
        await template_manager.register(template)

        params = {f"item{i}": f"value{i}" for i in range(100)}
        rendered = await template_manager.render("template-1", params)

        assert "value0" in rendered
        assert "value99" in rendered

    @pytest.mark.asyncio
    async def test_render_template_with_nested_braces(self, template_manager):
        """Test rendering template with nested braces."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="{{ key }}: {{ value }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render(
            "template-1", {"key": "test", "value": "{{ nested }}"}
        )

        assert "test:" in rendered
        # The nested {{ should be preserved as it's in the value
        assert "{{ nested }}" in rendered

    @pytest.mark.asyncio
    async def test_list_templates_order(self, template_manager):
        """Test that list_templates returns templates in registration order."""
        for i in range(5):
            template = WorkflowTemplate(
                template_id=f"template-{i}",
                name=f"Template {i}",
                source="echo test",
            )
            await template_manager.register(template)

        templates = await template_manager.list_templates()
        template_ids = [t.template_id for t in templates]

        assert template_ids == [
            "template-0",
            "template-1",
            "template-2",
            "template-3",
            "template-4",
        ]

    @pytest.mark.asyncio
    async def test_render_template_with_none_value(self, template_manager):
        """Test rendering template with None parameter value."""
        template = WorkflowTemplate(
            template_id="template-1",
            name="Test",
            source="value={{ value }}",
        )
        await template_manager.register(template)

        rendered = await template_manager.render("template-1", {"value": None})

        assert "None" in rendered
