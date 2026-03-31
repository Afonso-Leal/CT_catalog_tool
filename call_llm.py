"""
Furia LLM Wrapper - Generalized multi-provider LLM interface
Reads configuration from config.yaml
"""

import os
import json
import requests
from typing import Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str = ""
    api_key: str = ""
    default_model: str = ""
    local: bool = False
    port: int = 0
    headers: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    model: str
    raw_response: Optional[dict] = None


class LLMWrapper:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: str = "config.yaml",
    ):
        self.config = self._load_config(config_path)

        # Load providers from config FIRST
        self.providers = self._load_providers()

        # Determine provider
        if provider:
            self.provider = provider
        elif self.config.get("active_provider"):
            self.provider = self.config["active_provider"]
        else:
            self.provider = self._auto_detect()

        # Determine model (needs providers loaded first)
        self.model = model or self._get_default_model()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def _load_providers(self) -> dict[str, ProviderConfig]:
        """Load providers from config."""
        providers = {}
        config_providers = self.config.get("providers", {})

        for name, config in config_providers.items():
            if not config.get("enabled", True):
                continue

            pc = ProviderConfig(
                name=name,
                base_url=config.get("base_url", ""),
                api_key_env=config.get("api_key_env", ""),
                api_key=config.get("api_key", ""),  # Load from config
                default_model=config.get("default_model", ""),
                local=config.get("local", False),
                port=config.get("port", 0),
                headers=config.get("headers", {}),
            )
            providers[name] = pc

        return providers

    def _auto_detect(self) -> str:
        """Auto-detect best available provider."""
        # Try local providers first
        for name, pc in self.providers.items():
            if pc.local:
                if self._check_local_available(pc):
                    return name

        # Try cloud providers with API keys
        for name, pc in self.providers.items():
            if not pc.local and pc.api_key_env:
                if os.environ.get(pc.api_key_env):
                    return name

        # Fallback: first available provider
        if self.providers:
            return list(self.providers.keys())[0]

        return "ollama"  # Ultimate fallback

    def _check_local_available(self, pc: ProviderConfig) -> bool:
        if pc.port:
            try:
                r = requests.get(f"http://localhost:{pc.port}/api/tags", timeout=2)
                return r.status_code == 200
            except Exception:
                pass
            try:
                r = requests.get(f"http://localhost:{pc.port}/api/v0/models", timeout=2)
                return r.status_code == 200
            except Exception:
                pass
        return False

    def _get_default_model(self) -> str:
        # First try config-level default
        config_default = self.config.get("default_model")
        if config_default:
            # Try to get first available model
            models = self.list_models()
            if models:
                return models[0]
            return config_default

        # Then try provider-specific default
        pc = self.providers.get(self.provider)
        if pc and pc.default_model:
            models = self.list_models()
            if models:
                return models[0]
            return pc.default_model

        # Fallback
        return "llama3.2"

    def _get_headers(self) -> dict:
        pc = self.providers.get(self.provider)
        headers = {"Content-Type": "application/json"}

        if pc and pc.api_key_env:
            # First try environment variable
            api_key = os.environ.get(pc.api_key_env, "")
            # Then try config file (for cloud providers)
            if not api_key and pc.api_key:
                api_key = pc.api_key
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

        # Add custom headers from config
        if pc and pc.headers:
            headers.update(pc.headers)

        return headers

    def _get_base_url(self) -> str:
        pc = self.providers.get(self.provider)
        if pc:
            return pc.base_url
        return "http://localhost:11434"

    def _is_local(self) -> bool:
        pc = self.providers.get(self.provider)
        return pc.local if pc else False

    def _supports_tools_natively(self) -> bool:
        # LM Studio (via /v1/chat/completions) - OpenAI compatible
        if self.provider == "lmstudio":
            return True
        # Cloud providers suportam tool calling nativo
        return not self._is_local()

    def _get_endpoint(self, endpoint_type: str = "chat") -> str:
        base = self._get_base_url()

        # LM Studio - OpenAI-compatible endpoint (/v1/chat/completions)
        if self.provider == "lmstudio":
            return f"{base}/chat/completions"

        # Ollama - custom API
        if self.provider == "ollama":
            return f"{base}/api/chat"

        # Cloud providers (OpenAI-compatible)
        return f"{base}/chat/completions"

    def _build_system_prompt(self, tools: Optional[list[dict]] = None) -> str:
        """Build system prompt with tool definitions for providers without native support."""
        if not tools:
            return ""

        tool_descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            required = params.get("required", [])
            props = params.get("properties", {})

            param_str = ", ".join(required) if required else "none"

            desc = f"- {func['name']}: {func['description']} (params: {param_str})"
            tool_descriptions.append(desc)

        system = f"""Você é um assistente helpful com acesso a ferramentas.

                Quando precisar usar uma ferramenta, responda NO FORMATO JSON EXATO:
                {{"tool": "nome_da_funcao", "arguments": {{"param1": "valor1"}}}}
                
                Não use outro formato! Responda apenas com o JSON quando precisar de ferramenta.
                
                Ferramentas disponíveis:
                {chr(10).join(tool_descriptions)}
                
                Caso contrário, responda normalmente em texto."""

        return system

    def _parse_tool_call(self, content: str) -> Optional[tuple[str, dict]]:
        """Parse tool call from response content (for local providers)."""
        import re

        # Try to find JSON in response
        json_match = re.search(
            r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*"arguments"\s*:\s*(\{[^}]*\})',
            content,
        )
        if json_match:
            try:
                tool_name = json_match.group(1)
                args = json.loads(json_match.group(2))
                return tool_name, args
            except Exception:
                pass

        # Alternative format
        json_match = re.search(r"\{[^}]+\}", content)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "tool" in data and "arguments" in data:
                    return data["tool"], data["arguments"]
            except Exception:
                pass

        return None

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[object] = None,
    ) -> LLMResponse:
        model = model or self.model

        # Check if we need to handle tools manually
        use_native_tools = tools and self._supports_tools_natively()

        if self._is_local():
            # Local providers
            if self.provider == "lmstudio":
                # LM Studio supports tools natively via its API
                return self._chat_local(
                    messages,
                    model,
                    temperature,
                    max_tokens,
                    tools if use_native_tools else None,
                )
            else:
                # Ollama: inject system prompt for tool calling
                system_prompt = self._build_system_prompt(tools) if tools else ""
                if system_prompt:
                    if not any(m.get("role") == "system" for m in messages):
                        messages = [
                            {"role": "system", "content": system_prompt}
                        ] + messages

                return self._chat_local(messages, model, temperature, max_tokens, None)
        else:
            # Cloud providers: native tool calling
            return self._chat_cloud(
                messages,
                model,
                temperature,
                max_tokens,
                tools if use_native_tools else None,
                tool_choice,
            )

    def _chat_local(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[list] = None,
    ) -> LLMResponse:
        url = self._get_endpoint("chat")

        if self.provider == "lmstudio":
            # LM Studio - OpenAI-compatible format
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
        else:
            # Ollama API
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }

        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Parse response
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        return LLMResponse(content=content, model=model, raw_response=data)

    def _chat_cloud(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[list],
        tool_choice: Optional[object] = None,
    ) -> LLMResponse:
        url = self._get_endpoint("chat")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        resp = requests.post(
            url, json=payload, headers=self._get_headers(), timeout=120
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # Ajuda a depurar 400/401/403 retornando o body do provider
            body = ""
            try:
                body = resp.text
            except Exception:
                body = "<no body>"
            raise requests.HTTPError(f"{e} | response_body={body[:2000]}") from e
        data = resp.json()

        choice = data.get("choices", [{}])[0].get("message", {})
        content = choice.get("content", "")

        return LLMResponse(content=content, model=model, raw_response=data)

    def list_models(self) -> list[str]:
        pc = self.providers.get(self.provider)
        if not pc:
            return []

        base = self._get_base_url()

        if self.provider == "ollama":
            try:
                r = requests.get(f"{base}/api/tags", timeout=5)
                return [m["name"] for m in r.json().get("models", [])]
            except Exception:
                return []

        elif self.provider == "lmstudio":
            try:
                r = requests.get(f"{base}/api/v0/models", timeout=5)
                return [m["id"] for m in r.json().get("data", [])]
            except Exception:
                return []

        # Cloud providers - try generic endpoint
        try:
            headers = self._get_headers()
            r = requests.get(f"{base}/models", headers=headers, timeout=15)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            pass

        return []

    def get_provider_info(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self._get_base_url(),
            "available": len(self.list_models()),
        }


LLMCaller = LLMWrapper


if __name__ == "__main__":
    print("Testing LLMWrapper...")
    try:
        llm = LLMWrapper()
        print(f"Provider: {llm.provider}")
        print(f"Model: {llm.model}")
        print(f"Base URL: {llm._get_base_url()}")

        resp = llm.chat([{"role": "user", "content": "oi"}])
        print(f"Response: {resp.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
