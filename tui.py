"""
Furia TUI - Terminal User Interface with Chatbot and Tools
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

from call_llm import LLMWrapper
import search_tool
import read_pdf
import scrap_bot
import kb_tools
from analyzer import run_analysis as analyzer_run


console = Console()
VERBOSE = False


def _truncate_tool_content(text: str, max_chars: int = 8000) -> str:
    """Evita estourar contexto ao reenviar resultados de tools ao LLM."""

    if not isinstance(text, str):
        text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n...[truncado, {len(text)} chars no total]..."


def set_verbose(value: bool):
    global VERBOSE
    VERBOSE = value
    console.print(f"[yellow]Verbose: {'ON' if value else 'OFF'}[/yellow]")


def log_request(data: dict):
    if VERBOSE:
        console.print(
            Panel(
                Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json"),
                title="→ Request",
                border_style="blue",
            )
        )


def log_response(data: dict):
    if VERBOSE:
        console.print(
            Panel(
                Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json"),
                title="← Response",
                border_style="green",
            )
        )


def log_tool(name: str, args: dict, result: str):
    if VERBOSE:
        console.print(f"[cyan]🔧 Tool: {name}[/cyan]")
        console.print(f"[dim]Args: {json.dumps(args, ensure_ascii=False)[:200]}[/dim]")
        console.print(f"[dim]Result: {result[:200]}...[/dim]")


def show_status():
    """Show provider status."""
    table = Table(title="📡 Status dos Provedores", show_header=False)
    table.add_column("Provedor", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Modelos", style="yellow")

    for name in ["ollama", "lmstudio", "deepseek", "openrouter", "openai"]:
        try:
            llm = LLMWrapper(name)
            models = llm.list_models()
            status = f"✓ {len(models)} modelos"
        except Exception as e:
            status = f"✗ {str(e)[:30]}"

        table.add_row(
            name, status, str(len(llm.list_models())) if status.startswith("✓") else "0"
        )

    console.print(table)


def show_models():
    """Show available models."""
    llm = LLMWrapper()
    info = llm.get_provider_info()

    console.print(f"[cyan]Provedor:[/cyan] {info['provider']}")
    console.print(f"[cyan]Modelo:[/cyan] {info['model']}")

    models = llm.list_models()
    if models:
        console.print(f"[green]Modelos disponíveis ({len(models)}):[/green]")
        for m in models[:20]:
            console.print(f"  • {m}")
        if len(models) > 20:
            console.print(f"  ... e mais {len(models) - 20}")
    else:
        console.print("[yellow]Nenhum modelo encontrado[/yellow]")


def cmd_search(args: list) -> str:
    """Search command."""
    if not args:
        return "Uso: /search <termo> [--pages N] [--results N]"

    query = args[0]
    max_pages = 1
    max_results = 20

    i = 1
    while i < len(args):
        if args[i] == "--pages" and i + 1 < len(args):
            max_pages = int(args[i + 1])
            i += 2
        elif args[i] == "--results" and i + 1 < len(args):
            max_results = int(args[i + 1])
            i += 2
        else:
            i += 1

    console.print(f"[yellow]🔍 Buscando: {query}[/yellow]")
    results = search_tool.buscar_google_sync(query, max_pages)
    return json.dumps(results[:max_results], indent=2, ensure_ascii=False)


def cmd_extract(args: list) -> str:
    """Extract PDF command."""
    if not args:
        return "Uso: /extract <pdf> [output.json]"

    pdf_path = args[0]
    output_path = args[1] if len(args) > 1 else None

    if not Path(pdf_path).exists():
        return f"Arquivo não encontrado: {pdf_path}"

    console.print(f"[yellow]📄 Extraindo de: {pdf_path}[/yellow]")
    result = read_pdf.call_tool_extract_pdf(pdf_path)

    if output_path:
        read_pdf.salvar_json_em_arquivo(result, output_path)

    return json.dumps(result, indent=2, ensure_ascii=False)


def cmd_analyze(args: list) -> str:
    """Analyze site command."""
    if not args:
        return "Uso: /analyze <url> [title]"

    url = args[0]
    title = args[1] if len(args) > 1 else "Site"

    console.print(f"[yellow]🌐 Analisando: {url}[/yellow]")

    # Load reference data
    dados_pdf = {
        "lista_de_caracteristicas_gerais_cts": [],
        "lista_de_regras_que_devem_seguir": [],
    }
    if Path("ct_report.json").exists():
        dados_pdf = search_tool.ler_json("./ct_report.json")

    result = scrap_bot.call_to_scrap_site({"link": url, "title": title}, dados_pdf)
    return result or "Erro na análise"


def cmd_analyze_bulk(args: list) -> str:
    """Analyze bulk command (usa analyzer/output/ct_contents.json)."""

    if not args:
        return "Uso: /analyze_bulk <n>"

    try:
        n = int(args[0])
    except ValueError:
        return "Uso: /analyze_bulk <n> (n deve ser inteiro)"

    results = analyzer_run.run_analysis_bulk(n)
    output_dir = analyzer_run.save_all_results(results) if results else None

    from collections import Counter

    classes = Counter(r.classificacao.value for r in results)
    return json.dumps(
        {
            "n_requested": n,
            "n_analyzed": len(results),
            "output_dir": str(output_dir) if output_dir else None,
            "class_counts": dict(classes),
            "summary_md": f"{output_dir}/summary.md" if output_dir else None,
        },
        ensure_ascii=False,
        indent=2,
    )

def cmd_config(args: list) -> str:
    """Config command - change provider/model."""
    if not args:
        llm = LLMWrapper()
        info = llm.get_provider_info()
        return f"Provider: {info['provider']}\nModel: {info['model']}"

    # /config provider ollama
    # /config model llama3.2
    if len(args) >= 2:
        if args[0] == "provider":
            llm = LLMWrapper(args[1])
            console.print(f"[green]Provedor alterado para: {args[1]}[/green]")
            return f"OK: {args[1]}"
        elif args[0] == "model":
            console.print(f"[green]Modelo definido para: {args[1]}[/green]")
            return f"Model: {args[1]}"

    return "Uso: /config [provider <name>] [model <name>]"


def cmd_verbose(args: list) -> str:
    """Verbose toggle."""
    if not args or args[0] == "on":
        set_verbose(True)
    elif args[0] == "off":
        set_verbose(False)
    else:
        return "Uso: /verbose [on|off]"


def cmd_help(args: list) -> str:
    """Help command."""
    return """
# Comandos do Furia

## Chat
`@<mensagem>` - Envia para o LLM (com auto tool calling)

## Busca
`/search <termo>` - Busca no Brave Search
`/extract <pdf>` - Extrai info de PDF
`/analyze <url>` - Analisa site
`/analyze_bulk <n>` - Analisa em lote n entradas de analyzer/output/ct_contents.json

## Base de conhecimento (KB)
`/kb_headings` - Lista seções (headings) da KB
`/kb_search <termo>` - Busca termo na KB (com contexto)
`/kb_section <trecho_do_titulo>` - Mostra uma seção da KB

## Status
`/status` - Status dos provedores
`/models` - Lista modelos disponíveis
`/config` - Ver/alterar configuração

## Observabilidade
`/verbose on` - Ativar logs detalhados
`/verbose off` - Desativar logs

## Sistema
`/clear` - Limpar tela
`/help` - Esta ajuda
`/exit` - Sair
"""


COMMANDS = {
    "/search": cmd_search,
    "/extract": cmd_extract,
    "/analyze": cmd_analyze,
    "/analyze_bulk": cmd_analyze_bulk,
    "/kb_headings": lambda _: json.dumps(kb_tools.list_kb_headings(), ensure_ascii=False),
    "/kb_search": lambda args: json.dumps(
        kb_tools.search_kb(" ".join(args)), ensure_ascii=False, indent=2
    )
    if args
    else "Uso: /kb_search <termo>",
    "/kb_section": lambda args: json.dumps(
        kb_tools.get_kb_section(" ".join(args)), ensure_ascii=False, indent=2
    )
    if args
    else "Uso: /kb_section <trecho_do_titulo>",
    "/status": lambda _: show_status() or "",
    "/models": lambda _: show_models() or "",
    "/config": cmd_config,
    "/verbose": cmd_verbose,
    "/clear": lambda _: (console.clear(), ""),
    "/help": cmd_help,
}


def chat_with_llm(message: str) -> str:
    """Send message to LLM with tool calling."""
    llm = LLMWrapper()

    # Define tools available
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_brave",
                "description": "Busca no Brave Search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termo de busca"},
                        "max_pages": {
                            "type": "integer",
                            "description": "Número de páginas",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Máximo de resultados",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_brave_with_content",
                "description": "Busca no Brave e baixa conteúdo das primeiras URLs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termo de busca"},
                        "max_pages": {"type": "integer", "description": "Número de páginas"},
                        "max_results": {"type": "integer", "description": "Máximo de resultados"},
                        "max_fetch": {
                            "type": "integer",
                            "description": "Quantos resultados baixar conteúdo (content)",
                        },
                        "timeout": {"type": "integer", "description": "Timeout em segundos"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "Baixa uma URL e extrai texto limpo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL"},
                        "timeout": {"type": "integer", "description": "Timeout em segundos"},
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_search_report_md",
                "description": "Salva relatório Markdown de busca",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "description": "Caminho do .md"},
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de queries",
                        },
                        "results": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Resultados (lista de dicts)",
                        },
                        "max_preview_chars": {
                            "type": "integer",
                            "description": "Tamanho do preview por item",
                        },
                    },
                    "required": ["output_path", "queries", "results"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "kb_headings",
                "description": "Lista headings da base legal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_items": {"type": "integer", "description": "Máximo de headings"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "kb_search",
                "description": "Busca termo na base legal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termo"},
                        "max_hits": {"type": "integer", "description": "Máximo de hits"},
                        "context_lines": {"type": "integer", "description": "Linhas de contexto"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "kb_section",
                "description": "Mostra seção da base legal por parte do título",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title_contains": {"type": "string", "description": "Parte do título"},
                        "max_chars": {"type": "integer", "description": "Máximo de caracteres"},
                    },
                    "required": ["title_contains"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_pdf",
                "description": "Extrai informações de um PDF",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {"type": "string", "description": "Caminho do PDF"},
                        "output": {
                            "type": "string",
                            "description": "Arquivo de saída JSON",
                        },
                    },
                    "required": ["pdf_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_site",
                "description": "Analisa se um site é centro terapêutico",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL do site"},
                        "title": {"type": "string", "description": "Título do site"},
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_bulk",
                "description": "Analisa em lote n entradas de analyzer/output/ct_contents.json",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "n": {"type": "integer", "description": "Quantidade de amostras a analisar"}
                    },
                    "required": ["n"],
                },
            },
        },
    ]

    system = (
        "Você é o Furia TUI. Você TEM acesso a ferramentas.\n"
        "Regras:\n"
        "- Quando o usuário pedir informação atual (notícias, 'últimas', 'hoje', etc.), use search_brave.\n"
        "- Quando precisar abrir uma URL e extrair conteúdo, use fetch_url.\n"
        "- Responda ao usuário usando os resultados das ferramentas (cite títulos/links quando possível).\n"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]

    # First call
    log_request({"messages": messages, "tools": tools})
    # Heurística: para perguntas de notícias/atualidades, force a tool de busca.
    msg_low = message.lower()
    force_search = any(
        k in msg_low
        for k in [
            "últimas",
            "ultimas",
            "notícias",
            "noticias",
            "hoje",
            "agora",
            "breaking",
        ]
    )
    tool_choice = (
        {"type": "function", "function": {"name": "search_brave"}}
        if force_search
        else None
    )

    response = llm.chat(messages, tools=tools, tool_choice=tool_choice, max_tokens=1024)
    log_response(response.raw_response or {})

    # Check for tool calls
    if response.raw_response:
        choice = response.raw_response.get("choices", [{}])[0]
        msg = choice.get("message", {})

        if "tool_calls" in msg:
            # Normalização: alguns providers rejeitam `content: null` quando há tool_calls.
            if msg.get("content") is None:
                msg["content"] = ""
            messages.append(msg)

            tool_results = []
            for tc in msg["tool_calls"]:
                func = tc["function"]
                name = func["name"]
                args = json.loads(func["arguments"])

                console.print(f"[cyan]🔧 Executando tool: {name}[/cyan]")
                if VERBOSE:
                    console.print(f"[dim]Args: {args}[/dim]")

                # Execute tool
                result = ""
                try:
                    if name == "search_brave":
                        results = search_tool.tool_search_brave(
                            args.get("query", ""),
                            args.get("max_pages", 1),
                            args.get("max_results", 20),
                        )
                        result = json.dumps(results, ensure_ascii=False, indent=2)
                    elif name == "search_brave_with_content":
                        results = search_tool.tool_search_brave_with_content(
                            args.get("query", ""),
                            args.get("max_pages", 1),
                            args.get("max_results", 20),
                            args.get("max_fetch", 3),
                            args.get("timeout", 30),
                        )
                        result = json.dumps(results, ensure_ascii=False, indent=2)
                    elif name == "fetch_url":
                        payload = search_tool.tool_fetch_url(
                            args.get("url", ""),
                            args.get("timeout", 30),
                        )
                        result = json.dumps(payload, ensure_ascii=False, indent=2)
                    elif name == "save_search_report_md":
                        path = search_tool.tool_save_search_report_md(
                            output_path=args.get("output_path", "search_report.md"),
                            queries=args.get("queries", []),
                            results=args.get("results", []),
                            max_preview_chars=args.get("max_preview_chars", 600),
                        )
                        result = json.dumps({"path": path}, ensure_ascii=False, indent=2)
                    elif name == "kb_headings":
                        heads = kb_tools.list_kb_headings(max_items=args.get("max_items", 200))
                        result = json.dumps(heads, ensure_ascii=False, indent=2)
                    elif name == "kb_search":
                        hits = kb_tools.search_kb(
                            args.get("query", ""),
                            max_hits=args.get("max_hits", 20),
                            context_lines=args.get("context_lines", 2),
                        )
                        result = json.dumps(hits, ensure_ascii=False, indent=2)
                    elif name == "kb_section":
                        sec = kb_tools.get_kb_section(
                            args.get("title_contains", ""),
                            max_chars=args.get("max_chars", 4000),
                        )
                        result = json.dumps(sec, ensure_ascii=False, indent=2)
                    elif name == "extract_pdf":
                        result = read_pdf.call_tool_extract_pdf(
                            args.get("pdf_path", "")
                        )
                        result = json.dumps(result, ensure_ascii=False)
                    elif name == "analyze_site":
                        dados_pdf = {
                            "lista_de_caracteristicas_gerais_cts": [],
                            "lista_de_regras_que_devem_seguir": [],
                        }
                        if Path("ct_report.json").exists():
                            dados_pdf = search_tool.ler_json("./ct_report.json")
                        result = (
                            scrap_bot.call_to_scrap_site(
                                {
                                    "link": args.get("url", ""),
                                    "title": args.get("title", ""),
                                },
                                dados_pdf,
                            )
                            or "Erro"
                        )
                    elif name == "analyze_bulk":
                        results = analyzer_run.run_analysis_bulk(int(args.get("n", 1)))
                        output_dir = analyzer_run.save_all_results(results) if results else None
                        from collections import Counter

                        classes = Counter(r.classificacao.value for r in results)
                        result = json.dumps(
                            {
                                "n_requested": int(args.get("n", 1)),
                                "n_analyzed": len(results),
                                "output_dir": str(output_dir) if output_dir else None,
                                "class_counts": dict(classes),
                                "summary_md": f"{output_dir}/summary.md"
                                if output_dir
                                else None,
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                except Exception as e:
                    result = f"Erro: {str(e)}"

                result = _truncate_tool_content(result, max_chars=8000)
                log_tool(name, args, result)

                tool_results.append(
                    {
                        "tool_call_id": tc["id"],
                        "role": "tool",
                        # Alguns providers exigem `name` no role=tool
                        "name": name,
                        "content": result if isinstance(result, str) else str(result),
                    }
                )

            messages.extend(tool_results)

            # Final call
            log_request({"messages": messages})
            # Alguns providers (ex.: OpenRouter) podem rejeitar mensagens com role="tool"
            # se o request final não incluir novamente o schema de tools.
            final_response = llm.chat(messages, tools=tools, max_tokens=1024)
            log_response(final_response.raw_response or {})

            return final_response.content

    return response.content


def chat_mode():
    """Main chat loop."""
    console.print(
        Panel.fit(
            "[bold cyan]Furia TUI[/bold cyan]\n[dim]Chatbot com Tools para CT Catalog[/dim]\n[dim]Digite @ para chat, / para comandos[/dim]",
            border_style="cyan",
        )
    )

    show_status()
    console.print()

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]Furia[/bold cyan]")
        except KeyboardInterrupt:
            console.print("\n[cyan]Até logo![/cyan]")
            break

        if not user_input.strip():
            continue

        if user_input.strip() == "/exit":
            console.print("[cyan]Até logo![/cyan]")
            break

        # Command
        if user_input.startswith("/"):
            parts = user_input.split()
            cmd = parts[0]
            args = parts[1:]

            if cmd in COMMANDS:
                try:
                    result = COMMANDS[cmd](args)
                    if result:
                        console.print(Panel(result, border_style="green"))
                except Exception as e:
                    console.print(f"[red]Erro: {e}[/red]")
            else:
                console.print(f"[red]Comando desconhecido: {cmd}[/red]")
                console.print("[dim]Digite /help para comandos[/dim]")

        # Chat with LLM
        elif user_input.startswith("@"):
            message = user_input[1:].strip()
            console.print("[yellow]Pensando...[/yellow]")

            try:
                response = chat_with_llm(message)
                console.print(Panel(response, border_style="cyan"))
            except Exception as e:
                console.print(f"[red]Erro: {e}[/red]")

        else:
            console.print("[dim]Digite @ para chat, / para comandos[/dim]")


if __name__ == "__main__":
    try:
        chat_mode()
    except KeyboardInterrupt:
        console.print("\n[cyan]Até logo![/cyan]")
