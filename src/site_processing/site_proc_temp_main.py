import json
import re
from datetime import datetime, timezone
from pathlib import Path
from scrapling.fetchers import StealthyFetcher
from BaseSite import BaseSpider
from lxml import html as lxml_html
from tools_templates import fetch_url_content

CT_SEARCH_REPORT = "../../output/reports/ct_search_report.json"
CT_CANDIDATES = [
    "https://www.institutonovavida.org/casas-de-recuperacao-de-dependentes-quimicos-evangelicas",
    "https://casadiasp.com.br/",
    "https://crenvi.org.br/",
    "https://www.clinicasviverbem.com/clinica-de-recuperacao-em-curitiba-pr/",
    "https://clinicavivavida.com/clinicas/550/boqueirao-curitiba-pr",
    "https://www.gruporecanto.com.br/",
    "https://www.gruponovavida.com.br/clinicas-de-recuperacao/curitiba-pr",
    "https://gruporecomeco.com.br/",
    "https://crejer.org.br/",
    "https://www.institutogratidao.org/",
]

def load_json(caminho_arquivo: str = CT_SEARCH_REPORT) -> dict:
    """Lê um arquivo JSON e retorna seu conteúdo como dicionário."""
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)

def extract_domain(url):
    # Pattern: optional scheme, then capture everything until : / ? #
    match = re.search(r'^(?:https?://)?([^/:?#]+)', url)
    if match:
        return match.group(1).replace("www.","")
    return None

def salvar_json_em_arquivo(variavel_json, caminho_arquivo: str) -> bool:
    """Save JSON to file."""
    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            if isinstance(variavel_json, str):
                try:
                    dados = json.loads(variavel_json)
                    json.dump(dados, arquivo, indent=2, ensure_ascii=False)
                except Exception:
                    arquivo.write(variavel_json)
            else:
                json.dump(variavel_json, arquivo, indent=2, ensure_ascii=False)

        print(f"✅ JSON salvo com sucesso em: {caminho_arquivo}")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar JSON: {e}")
        return False

if __name__ == "__main__":
    search_report = load_json()
    domains = []
    for report in search_report:
        domains.append(extract_domain(report["link"]))

    # page = StealthyFetcher.fetch("https://www.institutogratidao.org/", headless=True, network_idle=False)
    # test = page.xpath("//a[contains(@href, 'institutogratidao.org')]")[0].attrib["href"]


    test_spider = BaseSpider()
    for site in [CT_CANDIDATES[0]]:
        site_ = extract_domain(site)
        test_spider.set_urls(f"https://{site_}/")
        test_result = test_spider.start()
        salvar_json_em_arquivo(test_result.items, caminho_arquivo=f"../../output/reports/{site_.replace(".","")}_page_report.json")
    # print(test_result.items)

