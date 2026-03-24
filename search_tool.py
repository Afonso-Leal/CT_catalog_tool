
from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher
from lxml import html
from read_pdf import salvar_json_em_arquivo
import  json

def ler_json(caminho_arquivo):
    """
    Lê um arquivo JSON e retorna seu conteúdo como dicionário

    Args:
        caminho_arquivo (str): Caminho para o arquivo JSON

    Returns:
        dict: Conteúdo do arquivo JSON como dicionário
        None: Se ocorrer algum erro
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        return dados
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não é um JSON válido.")
        return None
    except Exception as e:
        print(f"Erro inesperado ao ler o arquivo: {e}")
        return None


def buscar_google_sync(search,max_pg):
    # Aceita cookies se necessário
    # try:
    #     page.click("button:has-text('Aceitar tudo')", timeout=3000)
    #     print("Cookies aceitos")
    # except:
    #     pass

    # Aguarda resultados
    #//div[contains(@class, 'result-content')]//a
    #//div[contains(@class, 'result-content')]//a//div[contains(@class, 'title search-snippet-title')]
    #//div[@id='results']/div[contains(@class,'snippet')]
    resultados = []
    for n_p in range(max_pg):
        page = StealthyFetcher.fetch(f"https://search.brave.com/search?q={search}&offset={n_p}&spellcheck=0", headless=True, network_idle=True)
        # Extrai resultados
        all_html = page.xpath("//div[@id='results']")[0].html_content
        tree = html.fromstring(all_html)

        # Pesquisar com XPath
        elementos = tree.xpath("//div[contains(@class, 'result-content')]/a")
        len_elementos = len(elementos)
        links = [elementos[i].get("href") for i in range(len_elementos)]
        elementos = tree.xpath("//div[contains(@class, 'result-content')]/a/div[contains(@class, 'title search-snippet-title')]")
        titulos = [elementos[i].text for i in range(len_elementos)]
        elementos = tree.xpath("//div[contains(@class,'snippet  ')]")
        iners = [html.tostring(elementos[i]) for i in range(len_elementos)]
        tmp = [{"link": link,"title": title,"html": "inner"} for inner,title,link in zip(iners,titulos,links)]
        resultados += tmp
    return resultados

if __name__ == "__main__":
    # Executa
    print("Iniciando busca invisível...")
    dados = ler_json("./ct_report.json")
    resultados = []
    StealthyFetcher.adaptive = True
    # headless=True = não abre janela (invisível)
    for search in dados['sinonimos_de_centro_terapeutico_para_pesquisar']:
        resultados += buscar_google_sync(search,1)
    salvar_json_em_arquivo(resultados, "./ct_search_report.json")
print()