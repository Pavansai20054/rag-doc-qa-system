import re


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def simple_token_count(text: str) -> int:
    return len(text.split())


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]
