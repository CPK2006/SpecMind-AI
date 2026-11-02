from docx import Document

from app.utils.document_parser import extract_docx_text


def test_docx_extraction_includes_paragraphs_tables_headers_and_footers(tmp_path):
    path = tmp_path / "requirements.docx"
    document = Document()
    document.add_paragraph("Software requirements")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "FR-001"
    table.cell(0, 1).text = "The system shall export reports"
    document.sections[0].header.paragraphs[0].text = "Confidential SRS"
    document.sections[0].footer.paragraphs[0].text = "Version 1.0"
    document.save(path)

    text = extract_docx_text(str(path))

    assert "Software requirements" in text
    assert "FR-001 | The system shall export reports" in text
    assert "Header: Confidential SRS" in text
    assert "Footer: Version 1.0" in text
