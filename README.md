# Furia - CT Catalog Tool

Ferramenta para catalogar centros terapêuticos legais e ilegais usando LLMs e scraping.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                            FURIA                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │  search_tool │    │  read_pdf    │    │  scrap_bot   │        │
│  │   (busca)    │    │  (PDF)       │    │  (análise)   │        │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘        │
│         │                   │                   │                  │
│         └───────────────────┼───────────────────┘                  │
│                             │                                      │
│                      ┌──────▼──────┐                               │
│                      │ call_llm.py│                               │
│                      │  (LLM API)  │                               │
│                      └──────┬──────┘                               │
│                             │                                      │
│         ┌───────────────────┼───────────────────┐                  │
│         │                   │                   │                  │
│  ┌──────▼──────┐    ┌───────▼──────┐    ┌──────▼──────┐         │
│  │   Ollama    │    │  LM Studio   │    │   Cloud     │         │
│  │ localhost   │    │  localhost   │    │ OpenRouter  │         │
│  │   :11434    │    │   :1234      │    │  DeepSeek   │         │
│  └─────────────┘    └──────────────┘    └─────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Uso

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  1. Setup   │ ───▶ │  2. Extract │ ───▶ │  3. Search  │
│  (config)   │      │  (PDF data) │      │  (sites)    │
└─────────────┘      └─────────────┘      └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  4. Analyze │
                                         │  (LLM+tools)│
                                         └─────────────┘
```

## Instalação

```bash
# Clone o repositório
cd CT_catalog_tool

# Crie ambiente virtual (opcional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt
```

## Configuração

### Setup Automático (Recomendado)

```bash
# Linux/Mac
./setup_config.sh

# Windows
setup_config.bat
```

O script detecta provedores disponíveis e permite selecionar:

- **Ollama** (local, porta 11434)
- **LM Studio** (local, porta 1234)
- **DeepSeek** (cloud, requer API key)
- **OpenRouter** (cloud, requer API key)
- **OpenAI** (cloud, requer API key)

### Variáveis de Ambiente

```bash
# Cloud providers
export DEEPSEEK_API_KEY="sua-chave"
export OPENROUTER_API_KEY="sua-chave"
export OPENAI_API_KEY="sua-chave"

# Override provider
export FURIA_PROVIDER=openrouter
export FURIA_MODEL=openai/gpt-4o-mini
```

## Uso

### TUI Interativo (Chatbot com Tools)

```bash
python tui.py
```

Comandos:
- `@<mensagem>` - Chat com LLM (auto tool calling)
- `/search <termo>` - Busca no Brave
- `/kb_headings` - Lista seções (headings) da base de conhecimento
- `/kb_search <termo>` - Busca literal na base de conhecimento (com contexto)
- `/kb_section <trecho_do_titulo>` - Mostra uma seção da base de conhecimento
- `/extract <pdf>` - Extrai info de PDF
- `/analyze <url>` - Analisa site
- `/analyze_bulk <n>` - Analisa em lote `n` entradas de `analyzer/output/ct_contents.json`
- `/status` - Status dos provedores
- `/models` - Lista modelos
- `/verbose on|off` - Observabilidade
- `/help` - Ajuda

### Scripts Individuais

```bash
# 1. Extrair dados do PDF de referência
python read_pdf.py

# 2. Buscar sites
python search_tool.py

# 3. Analisar sites
python scrap_bot.py
```

## Ferramentas

| Tool | Descrição |
|------|-----------|
| `call_llm.py` | Wrapper LLM multi-provider |
| `mcp_client.py` | Cliente MCP |
| `search_tool.py` | Busca no Brave |
| `read_pdf.py` | Extração de PDF |
| `scrap_bot.py` | Análise de sites |
| `kb_tools.py` | Navegação/consulta da base legal (KB) |
| `tools_templates.py` | “Tools” locais (fetch de URL, sem MCP) |
| `tui.py` | Interface interativa |
| `analyzer/run_analysis.py` | Pipeline de análise em lote + salvamento de outputs |

## Provedores Suportados

| Provider | Tipo | Porta/URL | API Key |
|----------|------|-----------|---------|
| Ollama | Local | 11434 | ✗ |
| LM Studio | Local | 1234 | ✗ |
| DeepSeek | Cloud | api.deepseek.com | ✓ |
| OpenRouter | Cloud | openrouter.ai | ✓ |
| OpenAI | Cloud | api.openai.com | ✓ |

## Observabilidade

Ative o modo verbose para ver requests/responses:

```
Furia> /verbose on
Verbose: ON
Furia> @busque centros terapeuticos em sp
→ Request: {"model": "...", "messages": [...]}
← Response: {"choices": [...]}
🔧 Executando tool: search_brave
Args: {"query": "...", "max_pages": 1}
```

## Estrutura

```
CT_catalog_tool/
├── call_llm.py          # Wrapper LLM
├── mcp_client.py        # Cliente MCP
├── search_tool.py       # Busca web
├── read_pdf.py          # Processamento PDF
├── scrap_bot.py         # Análise de sites
├── tui.py               # Chatbot TUI
├── setup_config.sh      # Setup Linux/Mac
├── setup_config.bat     # Setup Windows
├── config.yaml          # Configuração
├── requirements.txt     # Dependências
├── README.md            # Este arquivo
└── AGENTS.md            # Docs para agents
```

## Troubleshooting

### MCP não funciona
- Instale: `pip install mcp`
- Ou use sem MCP (o TUI funciona mesmo assim)

### Provedor não encontrado
- Execute `./setup_config.sh` para configurar
- Verifique variáveis de ambiente

### Erro de scraping
- Alguns sites podem bloquear scrapers
- Use `/verbose on` para debug

### Rate limit (HTTP 429) no Brave
- Se algumas queries retornarem `429`, reduza volume/velocidade de buscas ou use termos mais específicos
- O `search_tool.py` salva relatório em `ct_search_report.md` quando rodado como script

### Erros de contexto/token (OpenRouter)
- Se ocorrer erro de `max_tokens`/contexto após uso de tools, reduza o volume de resultados e/ou use queries mais específicas
- O TUI trunca automaticamente respostas de tools para evitar estourar o contexto