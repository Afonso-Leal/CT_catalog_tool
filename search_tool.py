from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError as time_out_exception
from lxml import html
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


def buscar_google_sync(search,max_pg,page):
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
        page.goto(f"https://search.brave.com/search?q={search}&offset={n_p}&spellcheck=0")
        try:
            page.wait_for_selector("//div[@id='results']",timeout=1000)
        except time_out_exception as e:
            page.wait_for_selector("//div[@id='pow-captcha']//button")
            print("captch found")
            page.query_selector("//div[@id='pow-captcha']//button").click()
            page.wait_for_selector("//div[@id='results']", timeout=120000)
        # Extrai resultados
        all_html = page.query_selector_all("//div[@id='results']")[0].inner_html()
        tree = html.fromstring(all_html)

        # Pesquisar com XPath
        elementos = tree.xpath("//div[contains(@class, 'result-content')]/a")
        len_elementos = len(elementos)
        links = [elementos[i].get("href") for i in range(len_elementos)]
        elementos = tree.xpath("//div[contains(@class, 'result-content')]/a/div[contains(@class, 'title search-snippet-title')]")
        titulos = [elementos[i].text for i in range(len_elementos)]
        elementos = tree.xpath("//div[contains(@class,'snippet  ')]")
        iners = [html.tostring(elementos[i]) for i in range(len_elementos)]
        tmp = [{"link": link,"title": title,"html": inner} for inner,title,link in zip(iners,titulos,links)]
        resultados += tmp
    return resultados

if __name__ == "__main__":
    # Executa
    print("Iniciando busca invisível...")
    dados = ler_json("./ct_report.json")
    resultados = []
    with sync_playwright() as p:
        # headless=True = não abre janela (invisível)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Define um user-agent comum para não ser detectado como bot
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        for search in dados['sinonimos_de_centro_terapeutico_para_pesquisar']:
            resultados += buscar_google_sync(search,1,page)
        browser.close()
    print()