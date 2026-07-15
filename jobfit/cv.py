from pypdf import PdfReader


def read_cv(path: str, max_chars: int = 12000) -> tuple[str, list[str]]:
    reader = PdfReader(path)
    text = ""
    logs = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        logs.append(f"Read CV page {page_number}: {len(page_text)} characters")
        text += page_text + "\n"
    return text[:max_chars], logs
