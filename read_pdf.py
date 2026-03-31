"""
PDF Handler - Extract information from PDF files using LLM
"""

import base64
import os
import json
from call_llm import LLMWrapper


PDF_PATH = "./ct_report.pdf"


def comprimir_pdf_simples(arquivo_pdf: str, qualidade: int = 50) -> str:
    """Simple compression for PDF files."""
    try:
        import fitz
        from pathlib import Path

        nome_original = Path(arquivo_pdf).stem
        saida = f"{nome_original}_comprimido.pdf"

        doc = fitz.open(arquivo_pdf)
        doc.save(saida, garbage=4, deflate=True, clean=True)
        doc.close()

        tamanho_original = os.path.getsize(arquivo_pdf) / 1024 / 1024
        tamanho_novo = os.path.getsize(saida) / 1024 / 1024

        print(f"Original: {tamanho_original:.2f}MB → Comprimido: {tamanho_novo:.2f}MB")

        return saida

    except ImportError:
        print("Instale o PyMuPDF: pip install pymupdf")
        return arquivo_pdf
    except Exception as e:
        print(f"Erro: {e}")
        return arquivo_pdf


def read_pdf(pdf_path: str = PDF_PATH) -> str:
    """Read PDF and return as base64."""
    with open(pdf_path, "rb") as arquivo_pdf:
        pdf_bytes = arquivo_pdf.read()

    return base64.b64encode(pdf_bytes).decode("utf-8")


def send_request(pdf_base64: str, pergunta: str) -> tuple[str, str]:
    """Send PDF to LLM for extraction."""
    llm = LLMWrapper()

    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": pergunta},
                    {"type": "text", "text": pdf_base64},
                ],
            }
        ]

        print("📤 Enviando PDF para análise...")
        response = llm.chat(messages, max_tokens=10000)

        return "", response.content

    except Exception as e:
        return "", f"❌ Erro ao processar: {str(e)}"


def call_tool_extract_pdf(pdf_path: str = PDF_PATH) -> dict:
    """Extract structured information from PDF about therapeutic centers."""
    pergunta = """
    Voce e um psicologo responsavel por catalogar centros terapeuticos legais e ilegais presentes em diversos sites na internet.

    Voce esta recebendo um relatorio sobre centros terapeuticos, voce vai extrair do pdf tres informacoes:
    - lista_de_caracteristicas_gerais_cts: pontos principais para identificar um centro terapeutico
    - lista_de_regras_que_devem_seguir: regras que estes centros terapeuticos devem seguir para estar regulares
    - sinonimos_de_centro_terapeutico_para_pesquisar: pelo menos 10 sinonimos

    Cada um dos valores do json devera ser uma lista[] de string()

    {
        "lista_de_caracteristicas_gerais_cts": ["recolhem pessoas para recuperacao", ...],
        "lista_de_regras_que_devem_seguir": ["nao podem internar por mais de 90 dias", ...],
        "sinonimos_de_centro_terapeutico_para_pesquisar": ["casa de internacao", ...]
    }
    """

    try:
        pdf_comprimido = comprimir_pdf_simples(pdf_path)
        pdf_base64 = read_pdf(pdf_comprimido)
        _, resultado = send_request(pdf_base64, pergunta)

        try:
            return json.loads(resultado)
        except json.JSONDecodeError:
            return {"raw_response": resultado}

    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
        return {}
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        return {}





if __name__ == "__main__":
    resultado = call_tool_extract_pdf(PDF_PATH)
    salvar_json_em_arquivo(resultado, "./ct_report.json")
