import re
import unicodedata


def transform_to_markdown(raw_text: str) -> str:
    """
    Converte uma string extraída de um site para o formato Markdown,
    aplicando estruturação, remoção de espaços desnecessários e limpeza de caracteres inválidos.

    Args:
        raw_text (str): Texto bruto extraído do site.

    Returns:
        str: Texto formatado em Markdown.
    """
    if not raw_text:
        return ""

    # 1. Normalizar caracteres (remover ou substituir não-UTF8)
    #    Mantém acentos, mas tenta corrigir caracteres problemáticos
    text = unicodedata.normalize('NFKD', raw_text).encode('ascii', 'ignore').decode('ascii')
    # Se preferir manter acentos, comente a linha acima e use:
    # text = raw_text.encode('utf-8', 'ignore').decode('utf-8')

    # 2. Remover tags HTML (caso existam)
    text = re.sub(r'<[^>]+>', '', text)

    # 3. Dividir em linhas e limpar espaços internos
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = re.sub(r'\s+', ' ', line).strip()
        if line:  # mantém linhas não vazias
            cleaned_lines.append(line)

    # 4. Heurísticas para classificação de linhas
    def is_heading1(line: str) -> bool:
        # Título com barras verticais (ex: "A | B | C")
        return '|' in line and len(line) < 200

    def is_heading2(line: str) -> bool:
        # Linha curta em maiúsculas e sem pontuação final (ou título curto)
        return (line.isupper() and len(line) < 50) or (len(line) < 30 and line[0].isupper() and line[-1] not in '.!?')

    def is_phone(line: str) -> bool:
        # Padrão brasileiro: (11) 9 5555-1234 ou 11 9 5555-1234
        pattern = r'^\D*(\d{2})\s*(\d{4,5})-?(\d{4})\s*(\D*)$'
        return bool(re.match(pattern, line.replace('(', '').replace(')', '').strip()))

    def is_address(line: str) -> bool:
        # Linha que parece endereço (contém "Av.", "Rua", "CEP", etc.)
        addr_keywords = ['av.', 'rua', 'alameda', 'praça', 'cep', 'jardim', 'jd.']
        return any(kw in line.lower() for kw in addr_keywords) and len(line) > 20

    def is_email(line: str) -> bool:
        return bool(re.match(r'[^@]+@[^@]+\.[^@]+', line))

    def is_url(line: str) -> bool:
        return bool(re.match(r'https?://\S+', line))

    def is_footer(line: str) -> bool:
        # Linha de rodapé com copyright ou símbolo ©
        return '©' in line or 'webmaster' in line.lower() or 'tecnologia' in line.lower()

    def is_list_item(line: str) -> bool:
        # Critérios para item de lista: linha curta, não se encaixa em outras categorias,
        # não termina com pontuação de frase, e não é heading
        if is_heading1(line) or is_heading2(line) or is_phone(line) or is_address(line) or is_email(line) or is_url(
                line) or is_footer(line):
            return False
        # Linha curta (menos de 40 caracteres) e não termina com ponto final
        return len(line) < 40 and line[-1] not in '.!?'

    # 5. Processar as linhas sequencialmente, agrupando listas e parágrafos
    output_lines = []
    i = 0
    n = len(cleaned_lines)

    while i < n:
        line = cleaned_lines[i]

        # --- Título principal (heading 1) ---
        if is_heading1(line):
            output_lines.append(f"# {line}")
            i += 1
            continue

        # --- Heading 2 (seção) ---
        if is_heading2(line):
            output_lines.append(f"## {line}")
            i += 1
            continue

        # --- Lista de itens (agrupa consecutivos) ---
        if is_list_item(line):
            list_items = []
            while i < n and is_list_item(cleaned_lines[i]):
                list_items.append(cleaned_lines[i])
                i += 1
            # Cada item vira bullet point
            for item in list_items:
                output_lines.append(f"* {item}")
            continue

        # --- Telefone ---
        if is_phone(line):
            output_lines.append(f" {line}")
            i += 1
            continue

        # --- Endereço ---
        if is_address(line):
            output_lines.append(f" {line}")
            i += 1
            continue

        # --- E-mail ou URL ---
        if is_email(line) or is_url(line):
            output_lines.append(f" {line}")
            i += 1
            continue

        # --- Rodapé ---
        if is_footer(line):
            output_lines.append(f"---\n{line}")
            i += 1
            continue

        # --- Parágrafo (agrupa linhas consecutivas que não são nenhum dos acima) ---
        paragraph_lines = []
        while i < n:
            cur = cleaned_lines[i]
            # Para não engolir headings e listas, verificamos novamente
            if (is_heading1(cur) or is_heading2(cur) or is_list_item(cur) or
                    is_phone(cur) or is_address(cur) or is_email(cur) or is_url(cur) or is_footer(cur)):
                break
            paragraph_lines.append(cur)
            i += 1

        if paragraph_lines:
            # Junta as linhas com espaço, e separa parágrafos com linha em branco
            paragraph_text = ' '.join(paragraph_lines)
            output_lines.append(paragraph_text)
            # Adiciona linha em branco para separação
            output_lines.append('')

        # Se não entrou em nenhum bloco, avança (não deve ocorrer)
        if not (is_heading1(line) or is_heading2(line) or is_list_item(line) or
                is_phone(line) or is_address(line) or is_email(line) or is_url(line) or
                is_footer(line) or paragraph_lines):
            i += 1

    # 6. Remover duplicatas de linhas em branco e juntar
    final_output = []
    prev_empty = False
    for line in output_lines:
        if line == '':
            if not prev_empty:
                final_output.append(line)
                prev_empty = True
        else:
            final_output.append(line)
            prev_empty = False

    return '\n'.join(final_output).strip()