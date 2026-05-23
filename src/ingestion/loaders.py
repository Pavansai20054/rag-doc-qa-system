import os
import time
from pathlib import Path
from typing import Iterable

import pdfplumber
import fitz
from bs4 import BeautifulSoup
from docx import Document
import markdown as md

from src.utils.metadata import DocumentChunk
from src.utils.text import normalize_whitespace


def _file_metadata(path: Path, doc_type: str) -> dict:
    stat = path.stat()
    return {
        "filename": path.name,
        "document_type": doc_type,
        "source_path": str(path),
        "created_date": time.strftime("%Y-%m-%d", time.localtime(stat.st_ctime)),
        "category": path.parent.name,
        "department": "unknown",
    }


def load_pdfs(root_dir: str) -> Iterable[DocumentChunk]:
    for path in Path(root_dir).rglob("*.pdf"):
        base_meta = _file_metadata(path, "pdf")
        try:
            with fitz.open(path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text = normalize_whitespace(page.get_text())
                    if not text:
                        continue
                    yield {
                        "text": text,
                        "metadata": {
                            **base_meta,
                            "page_number": page_num,
                            "section_heading": None,
                        },
                    }
        except Exception:
            with pdfplumber.open(path) as doc:
                for page_num, page in enumerate(doc.pages, start=1):
                    text = normalize_whitespace(page.extract_text() or "")
                    if not text:
                        continue
                    yield {
                        "text": text,
                        "metadata": {
                            **base_meta,
                            "page_number": page_num,
                            "section_heading": None,
                        },
                    }


def load_docx(root_dir: str) -> Iterable[DocumentChunk]:
    for path in Path(root_dir).rglob("*.docx"):
        base_meta = _file_metadata(path, "docx")
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            continue
        text = normalize_whitespace("\n".join(paragraphs))
        yield {
            "text": text,
            "metadata": {
                **base_meta,
                "page_number": None,
                "section_heading": None,
            },
        }


def load_wiki(root_dir: str) -> Iterable[DocumentChunk]:
    patterns = ("*.html", "*.htm", "*.md")
    for pattern in patterns:
        for path in Path(root_dir).rglob(pattern):
            base_meta = _file_metadata(path, "confluence")
            raw = Path(path).read_text(encoding="utf-8", errors="ignore")
            if path.suffix.lower() == ".md":
                raw = md.markdown(raw)
            soup = BeautifulSoup(raw, "html.parser")
            text = normalize_whitespace(soup.get_text(" "))
            if not text:
                continue
            yield {
                "text": text,
                "metadata": {
                    **base_meta,
                    "page_number": None,
                    "section_heading": None,
                },
            }


def load_txt(root_dir: str) -> Iterable[DocumentChunk]:
    for path in Path(root_dir).rglob("*.txt"):
        base_meta = _file_metadata(path, "txt")
        text = normalize_whitespace(
            Path(path).read_text(encoding="utf-8", errors="ignore")
        )
        if not text:
            continue
        yield {
            "text": text,
            "metadata": {
                **base_meta,
                "page_number": None,
                "section_heading": None,
            },
        }


def load_all(root_dir: str) -> Iterable[DocumentChunk]:
    for loader in (load_pdfs, load_docx, load_wiki, load_txt):
        yield from loader(root_dir)
