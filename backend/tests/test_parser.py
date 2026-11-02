from app.utils.document_parser import extract_text


def test_extract_text_rejects_unsupported_extensions(tmp_path):
    source = tmp_path / "requirements.txt"
    source.write_text("Not a supported SRS file", encoding="utf-8")

    try:
        extract_text(str(source))
    except ValueError as error:
        assert "Unsupported file type" in str(error)
    else:
        raise AssertionError("Unsupported file extensions must be rejected")
