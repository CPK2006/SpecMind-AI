from app.utils.document_parser import extract_text

# Replace this with one of the uploaded PDF/DOCX files
file_path = "uploads/pdf/f33ab59b-6f70-4660-9f90-a5be282f7be6.pdf"

text = extract_text(file_path)

print("=" * 80)
print(text)
print("=" * 80)