#!/usr/bin/env python3
"""
Furia Setup Configuration - Gerencia configuração de provedores LLM
Chamado por setup_config.sh e setup_config.bat
"""

import os
import sys
import getpass
import yaml
import requests


PROVIDERS = {
    "ollama": {
        "name": "Ollama",
        "type": "local",
        "base_url": "http://localhost:11434",
        "api_key_env": "",
        "default_model": None,
        "port": 11434,
        "check_endpoint": "/api/tags",
    },
    "lmstudio": {
        "name": "LM Studio",
        "type": "local",
        "base_url": "http://localhost:1234/v1",
        "api_key_env": "",
        "default_model": None,
        "port": 1234,
        "check_endpoint": "/models",
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "cloud",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "cloud",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "google/gemini-2.0-flash-exp:free",
        "headers": {"HTTP-Referer": "https://github.com/furia-ct"},
    },
    "openai": {
        "name": "OpenAI",
        "type": "cloud",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
}


def print_colored(text, color="default"):
    colors = {
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "cyan": "\033[0;36m",
        "default": "\033[0m",
    }
    print(f"{colors.get(color, '')}{text}\033[0m")


def check_provider(name, config):
    """Check if provider is available."""
    port = config.get("port")
    if port:
        try:
            r = requests.get(
                f"http://localhost:{port}{config['check_endpoint']}", timeout=2
            )
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def detect_providers():
    """Detect available local providers."""
    available = {}
    for name, config in PROVIDERS.items():
        if config["type"] == "local" and check_provider(name, config):
            available[name] = config
            print_colored(f"[{len(available)}] {config['name']}", "green")
            print(f"     - {config['base_url']} (local)")
    return available


def get_model_list(provider, base_url):
    """Get list of available models."""
    try:
        if provider == "ollama":
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            return [m["name"] for m in r.json().get("models", [])]
        elif provider == "lmstudio":
            r = requests.get(f"{base_url}/models", timeout=5)
            return [m.get("id", m.get("name", "")) for m in r.json().get("data", [])]
    except Exception:
        pass
    return []


def main():
    print_colored("=" * 40, "cyan")
    print_colored("  Furia - Configuração", "cyan")
    print_colored("=" * 40, "cyan")
    print()

    # Check if config exists
    if os.path.exists("config.yaml"):
        print("config.yaml já existe. Sobrescrever? (s/n)")
        response = input("> ").lower().strip()
        if response != "s":
            print("Abortado.")
            return

    print("Detectando provedores locais...")
    print()

    available = detect_providers()

    # Show menu
    print()
    print("Selecione o provedor:")
    for i, (name, config) in enumerate(PROVIDERS.items(), 1):
        status = "✓" if name in available else "○"
        print(
            f"  {i} - {config['name']:12} [{status}] - {'Grátis, local' if config['type'] == 'local' else 'Requer API key'}"
        )

    print()
    choice = input("Escolha [1-5]: ").strip()

    provider_map = {str(i): name for i, name in enumerate(PROVIDERS.keys(), 1)}
    provider_name = provider_map.get(choice, "ollama")

    provider_config = PROVIDERS[provider_name]
    print()
    print_colored(f"Provedor selecionado: {provider_config['name']}", "green")

    # Ask for API key if cloud provider
    api_key = None
    api_key_saved = False
    if provider_config["type"] == "cloud":
        api_key_env = provider_config.get("api_key_env")
        print(f"\n{provider_config['name']} requer API key.")

        # Check if already exists in env
        existing_key = os.environ.get(api_key_env, "")
        if existing_key:
            print_colored("✓ API key já configurada no ambiente", "green")
            api_key_saved = True
        else:
            print("(A key será salva em config.yaml para uso futuro)")
            api_key = getpass.getpass("Cole sua API key: ").strip()

            if api_key:
                os.environ[api_key_env] = api_key
                print_colored("✓ API key configurada!", "green")
                api_key_saved = True
            else:
                print_colored("Aviso: API key não fornecida", "yellow")

    # Get models
    models = get_model_list(provider_name, provider_config["base_url"])
    default_model = provider_config.get("default_model")

    if models:
        print()
        print(f"Modelos disponíveis ({len(models)}):")
        for m in models[:10]:
            print(f"  - {m}")
        if len(models) > 10:
            print(f"  ... e mais {len(models) - 10}")

    print()
    model_input = input(f"Modelo (Enter para padrão: {default_model}): ").strip()
    model = model_input or default_model or "llama3.2"

    print(f"Modelo: {model}")
    print()

    # Generate config.yaml
    config_data = {
        "active_provider": provider_name,
        "default_model": model,
        "providers": {},
        "mcp": {
            "server_url": "http://127.0.0.1:8000/sse",
            "enabled": True,
        },
    }

    for name, pc in PROVIDERS.items():
        config_data["providers"][name] = {
            "enabled": True,
            "base_url": pc["base_url"],
            "local": pc["type"] == "local",
            "port": pc.get("port", 0),
            "api_key_env": pc.get("api_key_env", ""),
            "api_key": api_key
            if name == provider_name and api_key
            else "",  # Save key for selected provider
            "default_model": pc.get("default_model", ""),
            "headers": pc.get("headers", {}),
        }

    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    print_colored("✓ config.yaml criado com sucesso!", "green")
    print()
    print("=" * 40)
    print("  Próximos passos:")
    print("=" * 40)
    print("  python tui.py         # Iniciar TUI")
    print()


if __name__ == "__main__":
    main()
