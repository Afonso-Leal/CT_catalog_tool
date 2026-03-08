import requests
import base64
import os
import json

PDF_PATH = "./ct_report.pdf"
API_key = os.environ.get('DEEPSEEK_API_KEY')
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

def limpar_resposta(X):
    X = X.content.decode()
    X = json.loads(X)['choices'][0]['message']['content']
    X = json.dumps(X, ensure_ascii=False)
    X = X.split("```")
    Y = X[1].replace("json", "").replace('\\n', '').replace("\\", '')
    return X[0], json.loads(Y)

def comprimir_pdf_simples(arquivo_pdf, qualidade=50):
    """
    Função mais simples para uso rápido

    Args:
        arquivo_pdf (str): Caminho do arquivo PDF
        qualidade (int): Qualidade (0-100)

    Returns:
        str: Caminho do arquivo comprimido
    """

    try:
        # Importar aqui para não precisar importar no início
        import fitz
        from pathlib import Path

        # Definir nome do arquivo de saída
        nome_original = Path(arquivo_pdf).stem
        saida = f"{nome_original}_comprimido.pdf"

        # Abrir e comprimir
        doc = fitz.open(arquivo_pdf)
        #doc.save(saida, garbage=4, deflate=True, clean=True)
        doc.close()

        # Mostrar resultado
        tamanho_original = os.path.getsize(arquivo_pdf) / 1024 / 1024
        tamanho_novo = os.path.getsize(saida) / 1024 / 1024

        print(f"Original: {tamanho_original:.2f}MB → Comprimido: {tamanho_novo:.2f}MB")
        print(f"Redução: {(1 - tamanho_novo / tamanho_original) * 100:.1f}%")

        return saida

    except ImportError:
        print("Instale o PyMuPDF: pip install pymupdf")
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None


# Uso mais simples ainda:
# pdf_comprimido = comprimir_pdf_simples("meu_arquivo.pdf")

def read_pdf():
    with open(PDF_PATH, 'rb') as arquivo_pdf:
        pdf_bytes = arquivo_pdf.read()

    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    return pdf_base64

def send_request(pdf, pergunta):
    try:

        payload = {
            "model": "arcee-ai/trinity-large-preview:free",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": pergunta
                        },
                        {
                            "type": "text",
                            "text": pdf #{
                                #"content": pdf,
                               # "file_type": "application/pdf"
                            #}
                        }
                    ]
                }
            ],
            "reponse_format": {'type': 'json_object'},
            "max_tokens": 10000
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {API_key}'
        }

        print(f"📤 Enviando PDF para análise...")
        resposta = requests.post(BASE_URL, json=payload, headers=headers)

        if resposta.status_code == 200:
            return limpar_resposta(resposta)
        else:
            return "",f"❌ Erro na API: {resposta.status_code}\n{resposta.text}"

    except Exception as e:
        return "",f"❌ Erro ao processar: {str(e)}"

def calL_tool_extract_pdf():
    try:
        pergunta = '''
        voce e um psicologo responsavem por catalogar centros terapeuticos legais e ilegais presentes em diversos sites na internet

        voce esta recebendo um relatorio sobre centros terapeuticos, voce vai extrait do pdf tres informaçoes;
        lista_de_caracteristicas_gerais_cts, constituise de pontos principais para identificar um centro terapeutico coisas que ajudem
        a identificar se um site e de centro terapeutico ou nao pro exemplo;
        lista_de_regras_que_devem_seguir, as regras que estes centros terapeuticos devem seguir parar que estejam regulares com
        os direitos humanos e a lei;
        ,sinonimos_de_centro_terapeutico_para_pesquisar, sinonimos que podem corresponder a centros terapeuticos para que se possa
        pesquisar e achar mais, forneça pelo menos 10 sinimos;

        cada um dos valores do json devera ser uma lista[] de string()

        {
        'lista_de_caracteristicas_gerais_cts': ['recolhem pessoas para recuperação, pagina 60', 'tratam de dependencia, pagina 30', ...],
        'lista_de_regras_que_devem_seguir':['nao podem internar por mais de 90 dias,pagi 70','devem ser regulamentados com governo, pagina 10',...]
        'sinonimos_de_centro_terapeutico_para_pesquisar'; ['casa de internação','centro de recolhimento',...]
        }
        '''
        before_json, resultado = send_request(comprimir_pdf_simples(PDF_PATH), pergunta)
        return resultado

    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")


def salvar_json_em_arquivo(variavel_json, caminho_arquivo):
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
            # Se já for string JSON, converte para dict primeiro
            if isinstance(variavel_json, str):
                try:
                    dados = json.loads(variavel_json)
                    json.dump(dados, arquivo, indent=2, ensure_ascii=False)
                except:
                    # Se não for JSON válido, salva como string
                    arquivo.write(variavel_json)
            else:
                # Se for dict/list, salva direto
                json.dump(variavel_json, arquivo, indent=2, ensure_ascii=False)

        print(f"✅ JSON salvo com sucesso em: {caminho_arquivo}")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar JSON: {e}")
        return False
# Exemplo de uso com tratamento de erros
if __name__ == "__main__":
    resultado = calL_tool_extract_pdf()
    salvar_json_em_arquivo(resultado, "./ct_report.json")
