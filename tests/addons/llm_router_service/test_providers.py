# -*- coding: utf-8 -*-
"""Unit tests for providers.py - LLM provider adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from extensions.addons.ai_plus.llm_router_service.providers import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    OpenSourceProvider,
    LocalProvider,
    ProviderFactory,
)
from extensions.addons.ai_plus.llm_router_service.schemas import ProviderType


class TestBaseLLMProvider:
    """Test BaseLLMProvider abstract class."""

    def test_base_provider_initialization(self):
        """Test base provider initialization."""
        # Can't instantiate abstract class directly
        with pytest.raises(TypeError):
            BaseLLMProvider(
                name="test",
                model_id="test-model",
            )

    def test_base_provider_subclass_initialization(self):
        """Test base provider subclass initialization."""
        class TestProvider(BaseLLMProvider):
            provider_type = ProviderType.OPENAI

            async def call(self, prompt, model=None, max_tokens=1024, temperature=0.7):
                from extensions.addons.ai_plus.llm_router_service.schemas import GenerateResponse
                return GenerateResponse(
                    content="test",
                    model=model or self.model_id,
                    provider=self.provider_type,
                    tokens=10,
                    latency_ms=100,
                    cost=0.01,
                )

        provider = TestProvider(
            name="test",
            model_id="test-model",
            cost_per_1k=0.03,
            max_tokens=128000,
            context_window=128000,
            api_key="sk-test",
            base_url="https://api.test.com",
        )

        assert provider.name == "test"
        assert provider.model_id == "test-model"
        assert provider.cost_per_1k == 0.03
        assert provider.max_tokens == 128000
        assert provider.context_window == 128000
        assert provider.api_key == "sk-test"
        assert provider.base_url == "https://api.test.com"

    def test_base_provider_default_values(self):
        """Test base provider with default values."""
        class TestProvider(BaseLLMProvider):
            provider_type = ProviderType.OPENAI

            async def call(self, prompt, model=None, max_tokens=1024, temperature=0.7):
                from extensions.addons.ai_plus.llm_router_service.schemas import GenerateResponse
                return GenerateResponse(
                    content="test",
                    model=model or self.model_id,
                    provider=self.provider_type,
                    tokens=10,
                    latency_ms=100,
                    cost=0.01,
                )

        provider = TestProvider(name="test", model_id="test-model")

        assert provider.cost_per_1k == 0.0
        assert provider.max_tokens == 0
        assert provider.context_window == 0
        assert provider.api_key == ""
        assert provider.base_url == ""

    def test_build_messages(self):
        """Test _build_messages method."""
        class TestProvider(BaseLLMProvider):
            provider_type = ProviderType.OPENAI

            async def call(self, prompt, model=None, max_tokens=1024, temperature=0.7):
                from extensions.addons.ai_plus.llm_router_service.schemas import GenerateResponse
                return GenerateResponse(
                    content="test",
                    model=model or self.model_id,
                    provider=self.provider_type,
                    tokens=10,
                    latency_ms=100,
                    cost=0.01,
                )

        provider = TestProvider(name="test", model_id="test-model")
        messages = provider._build_messages("Hello, world!")

        assert messages == [{"role": "user", "content": "Hello, world!"}]

    def test_estimate_cost(self):
        """Test _estimate_cost method."""
        class TestProvider(BaseLLMProvider):
            provider_type = ProviderType.OPENAI

            async def call(self, prompt, model=None, max_tokens=1024, temperature=0.7):
                from extensions.addons.ai_plus.llm_router_service.schemas import GenerateResponse
                return GenerateResponse(
                    content="test",
                    model=model or self.model_id,
                    provider=self.provider_type,
                    tokens=10,
                    latency_ms=100,
                    cost=0.01,
                )

        provider = TestProvider(name="test", model_id="test-model", cost_per_1k=0.03)

        assert provider._estimate_cost(1000) == 0.03
        assert provider._estimate_cost(2000) == 0.06
        assert provider._estimate_cost(500) == 0.015
        assert provider._estimate_cost(0) == 0.0


class TestOpenAIProvider:
    """Test OpenAIProvider class."""

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(
            name="openai-test",
            model_id="gpt-4",
            cost_per_1k=0.03,
            max_tokens=128000,
            context_window=128000,
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )

        assert provider.name == "openai-test"
        assert provider.model_id == "gpt-4"
        assert provider.cost_per_1k == 0.03
        assert provider.max_tokens == 128000
        assert provider.context_window == 128000
        assert provider.api_key == "sk-test"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.provider_type == ProviderType.OPENAI

    def test_openai_provider_default_base_url(self):
        """Test OpenAI provider default base URL."""
        provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")

        assert provider.base_url == "https://api.openai.com/v1"

    def test_openai_provider_custom_base_url(self):
        """Test OpenAI provider custom base URL."""
        provider = OpenAIProvider(
            name="test",
            model_id="gpt-4",
            api_key="sk-test",
            base_url="https://custom.api.com/v1",
        )

        assert provider.base_url == "https://custom.api.com/v1"

    @pytest.mark.asyncio
    async def test_openai_call_success(self):
        """Test OpenAI provider successful call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")
            result = await provider.call("Hello, world!")

            assert result.content == "Test response"
            assert result.model == "gpt-4"
            assert result.provider == ProviderType.OPENAI
            assert result.tokens == 100

    @pytest.mark.asyncio
    async def test_openai_call_with_custom_model(self):
        """Test OpenAI provider call with custom model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")
            result = await provider.call("Hello", model="gpt-3.5-turbo")

            assert result.model == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_openai_call_with_custom_params(self):
        """Test OpenAI provider call with custom parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")
            result = await provider.call("Hello", max_tokens=2048, temperature=0.5)

            assert result.tokens == 100

    @pytest.mark.asyncio
    async def test_openai_call_error(self):
        """Test OpenAI provider call with error."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = Exception("API error")

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")

            with pytest.raises(Exception, match="API error"):
                await provider.call("Hello")

    @pytest.mark.asyncio
    async def test_openai_call_http_error(self):
        """Test OpenAI provider call with HTTP error."""
        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP error", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")

            with pytest.raises(httpx.HTTPStatusError):
                await provider.call("Hello")

    @pytest.mark.asyncio
    async def test_openai_call_missing_usage(self):
        """Test OpenAI provider call with missing usage data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = OpenAIProvider(name="test", model_id="gpt-4", api_key="sk-test")
            result = await provider.call("Hello")

            assert result.tokens == 0


class TestAnthropicProvider:
    """Test AnthropicProvider class."""

    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider(
            name="anthropic-test",
            model_id="claude-3-opus",
            cost_per_1k=0.03,
            max_tokens=200000,
            context_window=200000,
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com/v1",
        )

        assert provider.name == "anthropic-test"
        assert provider.model_id == "claude-3-opus"
        assert provider.cost_per_1k == 0.03
        assert provider.max_tokens == 200000
        assert provider.context_window == 200000
        assert provider.api_key == "sk-ant-test"
        assert provider.base_url == "https://api.anthropic.com/v1"
        assert provider.provider_type == ProviderType.ANTHROPIC

    def test_anthropic_provider_default_base_url(self):
        """Test Anthropic provider default base URL."""
        provider = AnthropicProvider(name="test", model_id="claude-3", api_key="sk-ant-test")

        assert provider.base_url == "https://api.anthropic.com/v1"

    @pytest.mark.asyncio
    async def test_anthropic_call_success(self):
        """Test Anthropic provider successful call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Test response"}],
            "usage": {"input_tokens": 50, "output_tokens": 50},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = AnthropicProvider(name="test", model_id="claude-3", api_key="sk-ant-test")
            result = await provider.call("Hello, world!")

            assert result.content == "Test response"
            assert result.model == "claude-3"
            assert result.provider == ProviderType.ANTHROPIC
            assert result.tokens == 100

    @pytest.mark.asyncio
    async def test_anthropic_call_with_custom_model(self):
        """Test Anthropic provider call with custom model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Test response"}],
            "usage": {"input_tokens": 50, "output_tokens": 50},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = AnthropicProvider(name="test", model_id="claude-3", api_key="sk-ant-test")
            result = await provider.call("Hello", model="claude-3-sonnet")

            assert result.model == "claude-3-sonnet"

    @pytest.mark.asyncio
    async def test_anthropic_call_error(self):
        """Test Anthropic provider call with error."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = Exception("API error")

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = AnthropicProvider(name="test", model_id="claude-3", api_key="sk-ant-test")

            with pytest.raises(Exception, match="API error"):
                await provider.call("Hello")

    @pytest.mark.asyncio
    async def test_anthropic_call_missing_usage(self):
        """Test Anthropic provider call with missing usage data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Test response"}],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        with patch("extensions.addons.ai_plus.llm_router_service.providers.AsyncClient", return_value=mock_client):
            provider = AnthropicProvider(name="test", model_id="claude-3", api_key="sk-ant-test")
            result = await provider.call("Hello")

            assert result.tokens == 0


class TestOpenSourceProvider:
    """Test OpenSourceProvider class."""

    def test_open_source_provider_initialization(self):
        """Test OpenSource provider initialization."""
        provider = OpenSourceProvider(
            name="open-source-test",
            model_id="llama2-7b",
            cost_per_1k=0.0005,
            max_tokens=4096,
            context_window=4096,
            api_key="",
            base_url="http://localhost:8000/v1",
        )

        assert provider.name == "open-source-test"
        assert provider.model_id == "llama2-7b"
        assert provider.cost_per_1k == 0.0005
        assert provider.max_tokens == 4096
        assert provider.context_window == 4096
        assert provider.api_key == ""
        assert provider.base_url == "http://localhost:8000/v1"
        assert provider.provider_type == ProviderType.OPEN_SOURCE

    def test_open_source_provider_default_base_url(self):
        """Test OpenSource provider default base URL."""
        provider = OpenSourceProvider(name="test", model_id="llama2")

        assert provider.base_url == "http://localhost:8000/v1"

    def test_open_source_provider_inherits_openai(self):
        """Test that OpenSourceProvider inherits from OpenAIProvider."""
        provider = OpenSourceProvider(name="test", model_id="llama2")

        assert isinstance(provider, OpenAIProvider)


class TestLocalProvider:
    """Test LocalProvider class."""

    def test_local_provider_initialization(self):
        """Test Local provider initialization."""
        provider = LocalProvider(
            name="local-test",
            model_id="local-llm",
            cost_per_1k=0.0,
            max_tokens=4096,
            context_window=4096,
            api_key="",
            base_url="http://localhost:8080/v1",
        )

        assert provider.name == "local-test"
        assert provider.model_id == "local-llm"
        assert provider.cost_per_1k == 0.0
        assert provider.max_tokens == 4096
        assert provider.context_window == 4096
        assert provider.api_key == ""
        assert provider.base_url == "http://localhost:8080/v1"
        assert provider.provider_type == ProviderType.LOCAL

    def test_local_provider_default_base_url(self):
        """Test Local provider default base URL."""
        provider = LocalProvider(name="test", model_id="local-llm")

        assert provider.base_url == "http://localhost:8080/v1"

    def test_local_provider_inherits_openai(self):
        """Test that LocalProvider inherits from OpenAIProvider."""
        provider = LocalProvider(name="test", model_id="local-llm")

        assert isinstance(provider, OpenAIProvider)


class TestProviderFactory:
    """Test ProviderFactory class."""

    def test_factory_create_openai_provider(self):
        """Test factory creates OpenAI provider."""
        config = {
            "provider": "openai",
            "name": "gpt-4",
            "model": "gpt-4",
            "cost_per_1k": 0.03,
            "api_key": "sk-test",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_type == ProviderType.OPENAI

    def test_factory_create_openai_provider_with_enum(self):
        """Test factory creates OpenAI provider with enum."""
        config = {
            "provider": ProviderType.OPENAI,
            "name": "gpt-4",
            "model": "gpt-4",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenAIProvider)

    def test_factory_create_anthropic_provider(self):
        """Test factory creates Anthropic provider."""
        config = {
            "provider": "anthropic",
            "name": "claude-3",
            "model": "claude-3-opus",
            "api_key": "sk-ant-test",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, AnthropicProvider)
        assert provider.provider_type == ProviderType.ANTHROPIC

    def test_factory_create_anthropic_provider_with_enum(self):
        """Test factory creates Anthropic provider with enum."""
        config = {
            "provider": ProviderType.ANTHROPIC,
            "name": "claude-3",
            "model": "claude-3-opus",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, AnthropicProvider)

    def test_factory_create_open_source_provider(self):
        """Test factory creates OpenSource provider."""
        config = {
            "provider": "open_source",
            "name": "llama2",
            "model": "llama2-7b",
            "base_url": "http://localhost:8000/v1",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenSourceProvider)
        assert provider.provider_type == ProviderType.OPEN_SOURCE

    def test_factory_create_open_source_provider_with_enum(self):
        """Test factory creates OpenSource provider with enum."""
        config = {
            "provider": ProviderType.OPEN_SOURCE,
            "name": "llama2",
            "model": "llama2-7b",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenSourceProvider)

    def test_factory_create_local_provider(self):
        """Test factory creates Local provider."""
        config = {
            "provider": "local",
            "name": "local-llm",
            "model": "local-llm",
            "base_url": "http://localhost:8080/v1",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, LocalProvider)
        assert provider.provider_type == ProviderType.LOCAL

    def test_factory_create_local_provider_default(self):
        """Test factory creates Local provider as default."""
        config = {
            "provider": "unknown_provider",
            "name": "test",
            "model": "test-model",
        }

        provider = ProviderFactory.create(config)

        assert isinstance(provider, LocalProvider)

    def test_factory_config_with_model_id(self):
        """Test factory config with model_id field."""
        config = {
            "provider": "openai",
            "name": "gpt-4",
            "model_id": "gpt-4-turbo",
        }

        provider = ProviderFactory.create(config)

        assert provider.model_id == "gpt-4-turbo"

    def test_factory_config_without_model(self):
        """Test factory config without model field."""
        config = {
            "provider": "openai",
            "name": "gpt-4",
        }

        provider = ProviderFactory.create(config)

        # When model is not provided, it defaults to "unknown"
        assert provider.model_id == "unknown"

    def test_factory_config_without_name(self):
        """Test factory config without name field."""
        config = {
            "provider": "openai",
            "model": "gpt-4",
        }

        provider = ProviderFactory.create(config)

        assert provider.name == "gpt-4"

    def test_factory_config_all_fields(self):
        """Test factory config with all fields."""
        config = {
            "provider": "openai",
            "name": "gpt-4",
            "model_id": "gpt-4-turbo",
            "cost_per_1k": 0.03,
            "max_tokens": 128000,
            "context_window": 128000,
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
        }

        provider = ProviderFactory.create(config)

        assert provider.name == "gpt-4"
        assert provider.model_id == "gpt-4-turbo"
        assert provider.cost_per_1k == 0.03
        assert provider.max_tokens == 128000
        assert provider.context_window == 128000
        assert provider.api_key == "sk-test"
        assert provider.base_url == "https://api.openai.com/v1"

    def test_factory_config_zero_values(self):
        """Test factory config with zero values."""
        config = {
            "provider": "openai",
            "name": "test",
            "cost_per_1k": 0.0,
            "max_tokens": 0,
            "context_window": 0,
        }

        provider = ProviderFactory.create(config)

        assert provider.cost_per_1k == 0.0
        assert provider.max_tokens == 0
        assert provider.context_window == 0

    def test_factory_config_empty_strings(self):
        """Test factory config with empty strings."""
        config = {
            "provider": "openai",
            "name": "test",
            "api_key": "",
            "base_url": "",
        }

        provider = ProviderFactory.create(config)

        assert provider.api_key == ""
        # OpenAI provider has a default base_url, so empty string gets overridden
        assert provider.base_url == "https://api.openai.com/v1"

    def test_factory_config_none_base_url(self):
        """Test factory config with None base_url."""
        config = {
            "provider": "openai",
            "name": "test",
            "base_url": None,
        }

        provider = ProviderFactory.create(config)

        assert provider.base_url == "https://api.openai.com/v1"

    def test_factory_different_provider_strings(self):
        """Test factory with different provider string values."""
        provider_strings = ["openai", "anthropic", "open_source", "local", "unknown"]

        for provider_str in provider_strings:
            config = {"provider": provider_str, "name": "test", "model": "test-model"}
            provider = ProviderFactory.create(config)
            assert provider is not None

    def test_factory_case_sensitivity(self):
        """Test factory provider string case sensitivity."""
        config = {"provider": "OPENAI", "name": "test", "model": "test-model"}

        # Should default to LocalProvider for unknown provider
        provider = ProviderFactory.create(config)
        assert isinstance(provider, LocalProvider)
