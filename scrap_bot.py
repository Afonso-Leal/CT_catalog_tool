import requests
import os
import json
import asyncio
from read_pdf import salvar_json_em_arquivo, limpar_resposta
from search_tool import ler_json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

API_key = os.environ.get('DEEPSEEK_API_KEY')
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MCP_SERVER_URL = "http://127.0.0.1:8000/sse"

# ========== Funções assíncronas do MCP ==========
async def _get_mcp_tools(server_url: str):
    async with streamable_http_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            openai_tools = []
            for t in tools.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })
            return openai_tools

async def _call_mcp_tool(server_url: str, tool_name: str, arguments: dict):
    async with streamable_http_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            if result.content:
                return result.content[0].text
            return None

# ========== Wrappers síncronos ==========
def get_mcp_tools_sync(server_url: str):
    """Versão síncrona de _get_mcp_tools."""
    return asyncio.run(_get_mcp_tools(server_url))

def call_mcp_tool_sync(server_url: str, tool_name: str, arguments: dict):
    """Versão síncrona de _call_mcp_tool."""
    return asyncio.run(_call_mcp_tool(server_url, tool_name, arguments))

# ========== Função de chamada ao modelo (síncrona) ==========
def call_model(messages, tools=None):
    """Envia mensagens para a API e retorna o JSON da resposta."""
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": messages,
        "max_tokens": 10000,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_key}"
    }
    response = requests.post(BASE_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()   # <-- retorna o dicionário da resposta

# ========== Função principal de scraping ==========

def call_to_scrap_site(site_info, dados_pdf):
        pergunta = f"""
        Você é um psicólogo responsável por catalogar centros terapêuticos legais e ilegais presentes em diversos sites na internet.
        Tem a tarefa de visitar o link: {site_info['link']} de título {site_info['title']} e seguir os seguintes passos:

        Baseado nesta lista de características gerais de centros terapêuticos:
        {dados_pdf['lista_de_caracteristicas_gerais_cts']}

        Você deve identificar, após uma investigação minuciosa no site, se ele atende às características para ser considerado um centro terapêutico.
        Salve quais características o site possui em uma variável `caracteristicas_CTS_tem`.

        Você também deve utilizar a seguinte lista de regras que centros terapêuticos devem seguir:
        {dados_pdf['lista_de_regras_que_devem_seguir']}

        E deve elencar em quais regras não seguem, salvando em uma lista `regras_CTS_n_seguem`.

        Cada um dos valores do JSON deverá ser uma lista de strings. Exemplo:
        {{
            "caracteristicas_CTS_tem": ["recolhem pessoas para recuperação, pagina 60", "tratam de dependencia, pagina 30"],
            "regras_CTS_n_seguem": ["nao podem internar por mais de 90 dias, pagina 70", "devem ser regulamentados com governo, pagina 10"]
        }}
        """

        # 1. Obter ferramentas do MCP (síncrono)
        tools = get_mcp_tools_sync(MCP_SERVER_URL)

        # 2. Criar histórico inicial
        messages = [{"role": "user", "content": pergunta}]

        # 3. Primeira chamada ao modelo
        response = call_model(messages, tools)
        message = response["choices"][0]["message"]

        # 4. Se houver tool_calls, executá‑las
        if "tool_calls" in message:
            # Adiciona a mensagem do assistente com as tool_calls
            messages.append(message)

            tool_results = []
            for tc in message["tool_calls"]:
                func = tc["function"]
                tool_name = func["name"]
                args = json.loads(func["arguments"])
                print(f"🔧 Chamando ferramenta '{tool_name}' com argumentos: {args}")
                # Executa a tool via MCP (síncrono)
                result_text = call_mcp_tool_sync(MCP_SERVER_URL, tool_name, args)
                tool_results.append({
                    "tool_call_id": tc["id"],
                    "role": "tool",
                    "content": result_text
                })
                print(f"📝 Resultado: {result_text[:200]}...")

            # Adiciona os resultados das tools ao histórico
            messages.extend(tool_results)

            # 5. Segunda chamada ao modelo, agora com o resultado das tools
            final_response = call_model(messages)   # sem tools
            final_answer = final_response["choices"][0]["message"]["content"]
        else:
            # Resposta direta (sem tool_calls)
            final_answer = message["content"]

        return final_answer

if __name__ == "__main__":
    dados_search = ler_json("./ct_search_report.json")
    dados_pdf = ler_json("./ct_report.json")
    resultados = []
    for search in dados_search:
        print()
        resultado = call_to_scrap_site(search, dados_pdf)
        if resultado:
            resultados.append(resultado)
        print(resultados)
        break   # teste apenas com o primeiro
    # salvar_json_em_arquivo(resultados, "./ct_scrap_report.json")