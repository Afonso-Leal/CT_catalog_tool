import fitz


def convert_pdf_to_markdown(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    with open(output_path, "w", encoding="utf-8") as f:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            f.write(f"## Página {page_num + 1}\n\n{text}\n\n")


if __name__ == "__main__":
    convert_pdf_to_markdown(
        "diretrizes_assit_integral_final.pdf",
        "analyzer/knowledge_base/directives/diretrizes_assist_integral.md",
    )
