from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag

INPUT_PATH = Path("data/knowledge/config/rag_destinations.csv")
OUTPUT_PATH = Path("data/knowledge/rag_documents.csv")
RAW_PAGES_DIR = Path("data/knowledge/raw_pages")

WIKIVOYAGE_PAGE_URL = "https://en.wikivoyage.org/wiki/{page}"

SECTION_ORDER = ["Understand", "See", "Do", "Get around", "Eat", "Sleep"]
MIN_PARAGRAPH_CHARS = 60
MIN_SECTION_CHARS = 140
MIN_DOC_CHARS = 180
FALLBACK_BLOCK_MIN_CHARS = 120
FALLBACK_DOC_MIN_CHARS = 500
FALLBACK_DOC_MAX_CHARS = 1500
MAX_DOCS_PER_DESTINATION = 3
FALLBACK_TITLES = ["Overview", "Things to know", "Travel highlights"]

NOISY_TAGS = ["script", "style", "nav", "footer", "table", "aside", "noscript", "form", "header"]
NOISE_EXACT_TEXTS = {
    "create account",
    "log in",
    "main page",
    "travel destinations",
    "travel forum",
    "arrivals lounge",
    "random page",
    "recent changes",
    "community portal",
    "maintenance panel",
    "policies",
    "help",
    "interlingual lounge",
    "read",
    "edit",
    "view history",
    "what links here",
    "related changes",
    "upload file",
    "permanent link",
    "page information",
    "cite this page",
    "get shortened url",
    "switch to legacy parser",
    "create a book",
    "download as pdf",
    "printable version",
    "privacy policy",
    "about wikivoyage",
    "disclaimer",
    "code of conduct",
    "developers",
    "statistics",
    "cookie statement",
    "mobile view",
}
NOISE_CONTAINS = {
    "wikimedia foundation",
    "powered by mediawiki",
    "terms of use",
}


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = re.sub(r"\[\s*edit\s*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).strip().lower()


def normalize_doc_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "destination"


def derive_local_filename(page_title: str) -> str:
    slug = page_title.strip().lower().replace(" ", "_").replace("/", "_")
    slug = re.sub(r"[^a-z0-9._-]+", "_", slug)
    if not slug.endswith(".html"):
        slug = f"{slug}.html"
    return slug


def build_source_url(page_title: str) -> str:
    page = page_title.strip().replace(" ", "_")
    return WIKIVOYAGE_PAGE_URL.format(page=quote(page, safe="_()"))


def remove_noisy_tags(soup: BeautifulSoup) -> None:
    for tag_name in NOISY_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def get_heading_title(heading: Tag) -> str:
    headline = heading.find(class_="mw-headline")
    text = headline.get_text(" ", strip=True) if isinstance(headline, Tag) else heading.get_text(" ", strip=True)
    return clean_text(text)


def map_section_title(raw_title: str) -> str | None:
    key = normalize_key(raw_title)

    if key.startswith("understand"):
        return "Understand"
    if key == "see" or key.startswith("see "):
        return "See"
    if key == "do" or key.startswith("do "):
        return "Do"
    if key.startswith("get around"):
        return "Get around"
    if key.startswith("eat"):
        return "Eat"
    if key.startswith("sleep"):
        return "Sleep"

    return None


def get_content_root(soup: BeautifulSoup) -> tuple[Tag | BeautifulSoup, bool, str]:
    content_container = soup.find(id="mw-content-text")
    if isinstance(content_container, Tag):
        parser_output_in_content = content_container.find("div", class_="mw-parser-output")
        if isinstance(parser_output_in_content, Tag):
            return parser_output_in_content, True, "div.mw-parser-output"

    parser_output = soup.find("div", class_="mw-parser-output")
    if isinstance(parser_output, Tag):
        return parser_output, True, "div.mw-parser-output"

    main = soup.find("main")
    if isinstance(main, Tag):
        return main, False, "main"

    if isinstance(soup.body, Tag):
        return soup.body, False, "body"

    return soup, False, "soup"


def is_noise_text(text: str) -> bool:
    normalized = normalize_key(text)
    if not normalized:
        return True
    if normalized in NOISE_EXACT_TEXTS:
        return True
    return any(phrase in normalized for phrase in NOISE_CONTAINS)


def get_clean_text_from_tag(tag: Tag, min_chars: int = MIN_PARAGRAPH_CHARS) -> str:
    text = clean_text(tag.get_text(" ", strip=True))
    if len(text) < min_chars:
        return ""
    if is_noise_text(text):
        return ""
    return text


def add_block_text(parts: list[str], tag: Tag) -> None:
    text = get_clean_text_from_tag(tag)
    if text:
        parts.append(text)


def extract_intro_text(content_root: Tag | BeautifulSoup) -> str:
    parts: list[str] = []

    for element in content_root.descendants:
        if not isinstance(element, Tag):
            continue
        if element.name in {"h1", "h2", "h3", "h4"}:
            break
        if element.name in {"p", "li"}:
            add_block_text(parts, element)
        if len(" ".join(parts)) >= 1200:
            break

    return clean_text(" ".join(parts))


def collect_section_text(heading: Tag) -> str:
    parts: list[str] = []
    heading_level = int(heading.name[1]) if re.fullmatch(r"h[1-6]", heading.name or "") else 6

    for element in heading.next_elements:
        if element is heading or not isinstance(element, Tag):
            continue

        if element.name in {"h1", "h2", "h3", "h4"}:
            level = int(element.name[1]) if re.fullmatch(r"h[1-6]", element.name or "") else 6
            if level <= heading_level:
                break
            continue

        if element.name in {"p", "li"}:
            add_block_text(parts, element)

        if len(" ".join(parts)) >= 1800:
            break

    return clean_text(" ".join(parts))


def extract_sections(content_root: Tag | BeautifulSoup) -> dict[str, str]:
    section_texts: dict[str, str] = {}

    for heading in content_root.find_all(["h1", "h2", "h3", "h4"]):
        if not isinstance(heading, Tag):
            continue

        raw_title = get_heading_title(heading)
        mapped_title = map_section_title(raw_title)

        if mapped_title is None or mapped_title in section_texts:
            continue

        text = collect_section_text(heading)
        if len(text) >= MIN_SECTION_CHARS:
            section_texts[mapped_title] = text

    return section_texts


def join_non_empty(parts: Iterable[str]) -> str:
    text = clean_text(" ".join(part for part in parts if part))
    return text


def dedupe_preserve_order(texts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for text in texts:
        key = normalize_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped


def collect_text_blocks(content_root: Tag | BeautifulSoup) -> list[str]:
    blocks: list[str] = []
    for tag in content_root.find_all(["p", "li"], recursive=True):
        if not isinstance(tag, Tag):
            continue
        text = get_clean_text_from_tag(tag)
        if text:
            blocks.append(text)
    return blocks


def extract_raw_html_blocks(html: str) -> list[str]:
    pattern = re.compile(r"<(p|li)\b[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)
    blocks: list[str] = []

    for match in pattern.finditer(html):
        raw_block = match.group(0)
        text = clean_text(BeautifulSoup(raw_block, "html.parser").get_text(" ", strip=True))
        if len(text) < FALLBACK_BLOCK_MIN_CHARS:
            continue
        if is_noise_text(text):
            continue
        blocks.append(text)

    return dedupe_preserve_order(blocks)


def build_fallback_documents(text_blocks: list[str]) -> list[tuple[str, str]]:
    long_blocks = [text for text in dedupe_preserve_order(text_blocks) if len(text) >= FALLBACK_BLOCK_MIN_CHARS]
    if not long_blocks:
        return []

    documents: list[tuple[str, str]] = []
    block_index = 0

    while block_index < len(long_blocks) and len(documents) < MAX_DOCS_PER_DESTINATION:
        grouped_blocks: list[str] = []
        grouped_length = 0

        while block_index < len(long_blocks):
            block = long_blocks[block_index]
            projected_length = grouped_length + len(block) + (1 if grouped_blocks else 0)

            if grouped_blocks and projected_length > FALLBACK_DOC_MAX_CHARS and grouped_length >= FALLBACK_DOC_MIN_CHARS:
                break

            grouped_blocks.append(block)
            grouped_length = projected_length
            block_index += 1

            if grouped_length >= FALLBACK_DOC_MIN_CHARS and grouped_length >= 900:
                break

        if not grouped_blocks:
            break

        fallback_text = clean_text(" ".join(grouped_blocks))
        if len(fallback_text) >= MIN_DOC_CHARS:
            title = FALLBACK_TITLES[min(len(documents), len(FALLBACK_TITLES) - 1)]
            documents.append((title, fallback_text))

    return documents[:MAX_DOCS_PER_DESTINATION]


def choose_documents(
    intro_text: str,
    sections: dict[str, str],
    fallback_documents: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    documents: list[tuple[str, str]] = []
    seen_texts: set[str] = set()

    def add_document(title: str, text: str) -> None:
        cleaned = clean_text(text)
        if len(cleaned) < MIN_DOC_CHARS:
            return
        key = normalize_key(cleaned)
        if not key or key in seen_texts:
            return
        seen_texts.add(key)
        documents.append((title, cleaned))

    overview_text = join_non_empty([intro_text, sections.get("Understand", "")])
    if len(overview_text) >= MIN_DOC_CHARS:
        add_document("Overview & Understand", overview_text)
    elif len(intro_text) >= MIN_DOC_CHARS:
        add_document("Overview", intro_text)
    elif len(sections.get("Understand", "")) >= MIN_DOC_CHARS:
        add_document("Understand", sections["Understand"])

    activities_text = join_non_empty(
        [sections.get("See", ""), sections.get("Do", ""), sections.get("Get around", "")]
    )
    if len(activities_text) >= MIN_DOC_CHARS:
        add_document("See, Do & Get around", activities_text)

    stay_text = join_non_empty([sections.get("Eat", ""), sections.get("Sleep", "")])
    if len(stay_text) >= MIN_DOC_CHARS:
        add_document("Eat & Sleep", stay_text)

    if len(documents) < 2:
        for section_name in SECTION_ORDER:
            section_text = sections.get(section_name, "")
            add_document(section_name, section_text)
            if len(documents) >= MAX_DOCS_PER_DESTINATION:
                break

    if len(documents) < MAX_DOCS_PER_DESTINATION:
        for title, text in fallback_documents:
            add_document(title, text)
            if len(documents) >= MAX_DOCS_PER_DESTINATION:
                break

    return documents[:MAX_DOCS_PER_DESTINATION]


def load_destinations() -> list[dict[str, str]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Destination config not found: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"No columns found in {INPUT_PATH}")

        required_columns = {
            "destination_name",
            "country",
            "travel_style",
            "wikivoyage_page",
        }
        missing = required_columns - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing columns in {INPUT_PATH}: {sorted(missing)}")

        return [dict(row) for row in reader]


def resolve_local_html_path(destination: dict[str, str]) -> Path:
    local_html_file = destination.get("local_html_file", "").strip()

    if local_html_file:
        local_path = Path(local_html_file)
        if local_path.suffix.lower() != ".html":
            local_path = local_path.with_suffix(".html")
        if not local_path.is_absolute():
            return RAW_PAGES_DIR / local_path
        return local_path

    page_title = destination["wikivoyage_page"].strip()
    return RAW_PAGES_DIR / derive_local_filename(page_title)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)

    destinations = load_destinations()

    rows: list[dict[str, str]] = []

    for destination in destinations:
        destination_name = destination["destination_name"].strip()
        country = destination["country"].strip()
        travel_style = destination["travel_style"].strip()
        page = destination["wikivoyage_page"].strip()

        local_html_path = resolve_local_html_path(destination)

        print(f"\nProcessing destination: {destination_name}")
        print(f"Using local file: {local_html_path}")

        if not local_html_path.exists():
            print(f"WARNING: Missing local HTML file for {destination_name}. Skipping.")
            continue

        html = local_html_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        remove_noisy_tags(soup)

        content_root, has_mw_parser_output, selected_container = get_content_root(soup)
        selected_container_blocks = collect_text_blocks(content_root)

        body_fallback_blocks: list[str] = []
        whole_soup_fallback_blocks: list[str] = []
        raw_regex_fallback_blocks: list[str] = []

        extraction_root: Tag | BeautifulSoup = content_root
        text_blocks = selected_container_blocks

        if not text_blocks:
            if isinstance(soup.body, Tag):
                body_fallback_blocks = collect_text_blocks(soup.body)
            if body_fallback_blocks:
                extraction_root = soup.body
                text_blocks = body_fallback_blocks
            else:
                whole_soup_fallback_blocks = collect_text_blocks(soup)
                if whole_soup_fallback_blocks:
                    extraction_root = soup
                    text_blocks = whole_soup_fallback_blocks

        if not text_blocks:
            raw_regex_fallback_blocks = extract_raw_html_blocks(html)
            text_blocks = raw_regex_fallback_blocks

        intro_text = extract_intro_text(extraction_root)
        sections = extract_sections(extraction_root)
        fallback_documents = build_fallback_documents(text_blocks)
        documents = choose_documents(intro_text, sections, fallback_documents)

        print(f"Debug: mw-parser-output found: {has_mw_parser_output}")
        print(f"Debug: selected container: {selected_container}")
        print(f"Debug: selected container block count: {len(selected_container_blocks)}")
        print(f"Debug: body fallback block count: {len(body_fallback_blocks)}")
        print(f"Debug: whole soup fallback block count: {len(whole_soup_fallback_blocks)}")
        print(f"Debug: raw regex fallback block count: {len(raw_regex_fallback_blocks)}")

        extracted_for_destination = 0
        for index, (title, text) in enumerate(documents, start=1):
            text = clean_text(text)
            if len(text) < MIN_DOC_CHARS:
                continue

            extracted_for_destination += 1
            doc_id = f"{normalize_doc_slug(destination_name)}_{index:03d}"

            rows.append(
                {
                    "doc_id": doc_id,
                    "destination_name": destination_name,
                    "country": country,
                    "source_name": "Wikivoyage",
                    "source_url": build_source_url(page),
                    "title": title,
                    "text": text,
                    "travel_style": travel_style,
                }
            )

        print(
            "Extracted "
            f"{extracted_for_destination} document(s) for {destination_name}."
        )
        print(f"Debug: docs created: {extracted_for_destination}")

    if not rows:
        raise RuntimeError(
            "No RAG documents were collected from local HTML files. "
            "Refusing to overwrite data/knowledge/rag_documents.csv."
        )

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "doc_id",
                "destination_name",
                "country",
                "source_name",
                "source_url",
                "title",
                "text",
                "travel_style",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} total documents to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
