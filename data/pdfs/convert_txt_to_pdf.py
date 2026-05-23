from __future__ import annotations

import os
from pathlib import Path
import textwrap

import fitz


BASE_DIR = Path(__file__).resolve().parent

PAGE_MARGIN = 72
FONT_SIZE = 11
LINE_HEIGHT = 14
LINE_WIDTH = 95


def _write_text_to_pdf(text: str, output_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = PAGE_MARGIN
    max_y = page.rect.height - PAGE_MARGIN

    for paragraph in text.splitlines():
        if not paragraph.strip():
            y += LINE_HEIGHT
            if y > max_y:
                page = doc.new_page()
                y = PAGE_MARGIN
            continue

        wrapped = textwrap.wrap(paragraph, width=LINE_WIDTH)
        for line in wrapped:
            if y > max_y:
                page = doc.new_page()
                y = PAGE_MARGIN
            page.insert_text(
                (PAGE_MARGIN, y),
                line,
                fontsize=FONT_SIZE,
                fontname="helv",
            )
            y += LINE_HEIGHT

    doc.save(output_path)
    doc.close()


def convert_all() -> None:
    txt_files = sorted(BASE_DIR.glob("*.txt"))
    converted = 0
    skipped = 0
    deleted = 0

    for txt_path in txt_files:
        pdf_path = txt_path.with_suffix(".pdf")
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            skipped += 1
            txt_path.unlink()
            deleted += 1
            continue

        content = txt_path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            continue

        _write_text_to_pdf(content, pdf_path)
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            converted += 1
            txt_path.unlink()
            deleted += 1

    print(
        f"Converted: {converted}, skipped(existing pdf): {skipped}, deleted txt: {deleted}"
    )


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    convert_all()
