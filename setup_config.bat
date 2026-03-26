@echo off
REM Furia Setup Configuration Script (Windows)
echo ==========================================
echo   Furia - Configuracao Interativa
echo ==========================================

if exist config.yaml (
    echo config.yaml ja existe. Sobrescrever? (S/N)
    set /p r=
    if /i not "%r%"=="S" exit /b 0
)

echo.
echo Detectando provedores...
echo.

REM Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 echo [1] Ollama        - localhost:11434 (local)

REM Check LM Studio
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% equ 0 echo [2] LM Studio      - localhost:1234/v1 (local)

echo.
echo Selecione o provedor:
echo   1 - Ollama (local) - Gratis, no seu computador
echo   2 - LM Studio (local) - Gratis, no seu computador
echo   3 - DeepSeek (cloud) - Requer API key
echo   4 - OpenRouter (cloud) - Requer API key
echo   5 - OpenAI (cloud) - Requer API key
echo.

set /p PROVIDER="Escolha [1-5]: "

if "%PROVIDER%"=="1" set PROVIDER_NAME=ollama
if "%PROVIDER%"=="2" set PROVIDER_NAME=lmstudio
if "%PROVIDER%"=="3" set PROVIDER_NAME=deepseek
if "%PROVIDER%"=="4" set PROVIDER_NAME=openrouter
if "%PROVIDER%"=="5" set PROVIDER_NAME=openai

if "%PROVIDER_NAME%"=="" (
    echo Entrada invalida. Usando Ollama como padrao.
    set PROVIDER_NAME=ollama
)

echo.
echo Provedor selecionado: %PROVIDER_NAME%

REM Ask for API key if cloud provider
set API_KEY=
if "%PROVIDER_NAME%"=="deepseek" (
    echo DeepSeek requer API key.
    set /p API_KEY="Cole sua DeepSeek API key: "
    set DEEPSEEK_API_KEY=%API_KEY%
)
if "%PROVIDER_NAME%"=="openrouter" (
    echo OpenRouter requer API key.
    set /p API_KEY="Cole sua OpenRouter API key: "
    set OPENROUTER_API_KEY=%API_KEY%
)
if "%PROVIDER_NAME%"=="openai" (
    echo OpenAI requer API key.
    set /p API_KEY="Cole sua OpenAI API key: "
    set OPENAI_API_KEY=%API_KEY%
)

echo.
set /p MODEL="Modelo (Enter para padrao): "

if "%MODEL%"=="" (
    if "%PROVIDER_NAME%"=="ollama" set MODEL=qwen3.5:27b
    if "%PROVIDER_NAME%"=="lmstudio" set MODEL=qwen3.5:27b
    if "%PROVIDER_NAME%"=="openrouter" set MODEL=google/gemini-2.0-flash-exp:free
    if "%PROVIDER_NAME%"=="deepseek" set MODEL=deepseek-chat
    if "%PROVIDER_NAME%"=="openai" set MODEL=gpt-4o-mini
)

echo Modelo: %MODEL%
echo.

REM Generate config.yaml
(
echo # Furia Configuration File
echo # Gerado por setup_config.bat
echo.
echo active_provider: "%PROVIDER_NAME%"
echo default_model: "%MODEL%"
echo.
echo providers:
echo   ollama:
echo     enabled: true
echo     base_url: "http://localhost:11434"
echo     local: true
echo     port: 11434
echo.
echo   lmstudio:
echo     enabled: true
echo     base_url: "http://localhost:1234/v1"
echo     local: true
echo     port: 1234
echo.
echo   deepseek:
echo     enabled: true
echo     base_url: "https://api.deepseek.com/v1"
echo     api_key_env: "DEEPSEEK_API_KEY"
echo     default_model: "deepseek-chat"
echo.
echo   openrouter:
echo     enabled: true
echo     base_url: "https://openrouter.ai/api/v1"
echo     api_key_env: "OPENROUTER_API_KEY"
echo     default_model: "google/gemini-2.0-flash-exp:free"
echo     headers:
echo       HTTP-Referer: "https://github.com/furia-ct"
echo.
echo   openai:
echo     enabled: true
echo     base_url: "https://api.openai.com/v1"
echo     api_key_env: "OPENAI_API_KEY"
echo     default_model: "gpt-4o-mini"
echo.
echo mcp:
echo   server_url: "http://127.0.0.1:8000/sse"
) > config.yaml

echo [OK] config.yaml criado!
echo.
echo ==========================================
echo   Proximos passos:
echo ==========================================
echo   python tui.py           # Iniciar TUI
echo.
echo Comandos do TUI:
echo   @Ola mundo            # Chat com LLM
echo   /search centro sp    # Buscar
echo   /help                 # Ajuda
echo.