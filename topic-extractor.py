#!/usr/bin/env python3
"""
Extract WSC guiding-question topics into structured JSON + derived markdown.

Usage:
  python topic-extractor.py --list
  python topic-extractor.py --topics "The End is Nearish,Progress, Not Regress"
  python topic-extractor.py --topics all
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://themes.scholarscup.org/"
DEFAULT_YEAR = "2026"
TOPICS_DIR = Path("topics")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def http_get_text(url: str, timeout: int = 30) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "")
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
        return body, content_type


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def strip_tags(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value, flags=re.DOTALL)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def unique_preserve(seq):
    seen = set()
    out = []
    for item in seq:
        if isinstance(item, dict):
            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        else:
            key = item
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def extract_balanced_array(source: str, open_bracket_pos: int) -> str:
    depth = 0
    in_single = False
    in_double = False
    in_backtick = False
    escaped = False
    start = open_bracket_pos

    for i in range(open_bracket_pos, len(source)):
        ch = source[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue

        if in_single:
            if ch == "'":
                in_single = False
            continue
        if in_double:
            if ch == '"':
                in_double = False
            continue
        if in_backtick:
            if ch == "`":
                in_backtick = False
            continue

        if ch == "'":
            in_single = True
            continue
        if ch == '"':
            in_double = True
            continue
        if ch == "`":
            in_backtick = True
            continue

        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise ValueError("Could not parse balanced array from JS bundle.")


def discover_bundle_url() -> str:
    home_html, _ = http_get_text(BASE_URL)
    match = re.search(r'<script type="module"[^>]+src="([^"]+)"', home_html)
    if not match:
        raise RuntimeError("Could not find JS bundle script URL on WSC themes page.")
    src = match.group(1)
    return urllib.parse.urljoin(BASE_URL, src)


def extract_theme_data_variable(bundle_text: str, year: str) -> str:
    idx = bundle_text.find("_I=[")
    if idx == -1:
        raise RuntimeError("Could not locate theme index (_I) in WSC JS bundle.")
    open_pos = bundle_text.find("[", idx)
    arr_text = extract_balanced_array(bundle_text, open_pos)

    for match in re.finditer(r'\{year:"(?P<year>\d{4})".*?data:(?P<data_var>[A-Za-z0-9_$]+)', arr_text):
        if match.group("year") == year:
            return match.group("data_var")
    raise RuntimeError(f"Could not find guiding questions material for year {year}.")


def extract_topics_from_data_var(bundle_text: str, data_var: str):
    marker = f"{data_var}=["
    idx = bundle_text.find(marker)
    if idx == -1:
        raise RuntimeError(f"Could not locate data variable '{data_var}' in JS bundle.")
    open_pos = bundle_text.find("[", idx)
    arr_text = extract_balanced_array(bundle_text, open_pos)

    topics = []
    pattern = re.compile(r'\{title:"(.*?)",body:`(.*?)`\}', re.DOTALL)
    for m in pattern.finditer(arr_text):
        title = html.unescape(m.group(1)).strip()
        body_html = m.group(2).strip()
        topics.append({"title": title, "body_html": body_html})
    if not topics:
        raise RuntimeError("No topics were parsed from the bundle data.")
    return topics


class LiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._li_stack = []
        self._in_anchor = False
        self._anchor_href = ""
        self._anchor_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "li":
            self._li_stack.append(
                {
                    "text_parts": [],
                    "links": [],
                    "has_italic": False,
                }
            )
        if not self._li_stack:
            return
        if tag in {"i", "em"}:
            self._li_stack[-1]["has_italic"] = True
        if tag == "a":
            self._in_anchor = True
            self._anchor_href = attrs_dict.get("href", "")
            self._anchor_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_anchor and self._li_stack:
            anchor_text = "".join(self._anchor_text).strip()
            self._li_stack[-1]["links"].append({"href": self._anchor_href, "text": anchor_text})
            self._in_anchor = False
            self._anchor_href = ""
            self._anchor_text = []
        if tag == "li" and self._li_stack:
            li = self._li_stack.pop()
            text = re.sub(r"\s+", " ", "".join(li["text_parts"])).strip()
            self.items.append(
                {
                    "text": html.unescape(text),
                    "links": li["links"],
                    "has_italic": li["has_italic"],
                }
            )

    def handle_data(self, data):
        if self._li_stack:
            self._li_stack[-1]["text_parts"].append(data)
        if self._in_anchor:
            self._anchor_text.append(data)


def parse_bullets(topic_body_html: str):
    parser = LiParser()
    parser.feed(topic_body_html)
    return [item for item in parser.items if item["text"]]


PERSON_STOPWORDS = {
    "index",
    "effect",
    "government",
    "clock",
    "bug",
    "panic",
    "prints",
    "season",
    "art",
    "questions",
    "overview",
}


def looks_like_person_name(value: str) -> bool:
    cleaned = re.sub(r"\([^)]*\)", "", value).strip()
    cleaned = re.sub(r"[“”\"'`.,:;!?]", "", cleaned)
    cleaned = cleaned.replace("’s", "").replace("'s", "")
    if any(ch.isdigit() for ch in cleaned):
        return False
    words = [w for w in cleaned.split() if w]
    if len(words) < 1 or len(words) > 5:
        return False
    if words[0].lower() == "the":
        return False
    if any(w.lower() in PERSON_STOPWORDS for w in words):
        return False
    if len(words) == 1:
        w = words[0]
        if len(w) < 6:
            return False
        return w[0].isupper() and not w.isupper()

    caps = 0
    for w in words:
        core = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ.-]", "", w)
        if not core:
            continue
        if core[0].isupper():
            caps += 1
    return caps >= 2


def clean_concept_token(token: str) -> str:
    token = re.sub(r"\([^)]*\)", "", token)
    token = token.strip()
    token = token.strip("“”\"'`")
    return re.sub(r"\s+", " ", token)


def clean_work_title(token: str) -> str:
    token = clean_concept_token(token)
    token = token.strip("“”\"")
    return token


def classify_topic_entities(bullets):
    artworks = []
    persons = []
    concepts = []

    for li in bullets:
        text = li["text"]
        parts = [clean_concept_token(p) for p in text.split("|")]
        parts = [p for p in parts if p]

        if len(parts) >= 2 and (li["has_italic"] or "“" in li["text"] or '"' in li["text"]):
            # Treat as potential artwork/media entry when it appears in a title-like formatting context.
            if len(parts) == 2:
                creator = parts[0]
                work = clean_work_title(parts[1])
                artworks.append({"creator": creator, "work": work})
                creator_parts = re.split(r"\s*&\s*|\s+and\s+", creator)
                for piece in creator_parts:
                    if looks_like_person_name(piece):
                        persons.append(piece)
            elif len(parts) > 2:
                # Fallback: keep tokens as concepts if structure is not clearly creator|work.
                concepts.extend(parts)
        elif len(parts) > 1:
            concepts.extend(parts)

    concepts = [c for c in concepts if c and not looks_like_person_name(c)]
    persons = [p for p in persons if p]

    return {
        "artworks": unique_preserve(artworks),
        "persons": unique_preserve(persons),
        "concepts": unique_preserve(concepts),
    }


def fetch_source_excerpt(url: str) -> dict:
    fetched_at = dt.datetime.utcnow().isoformat() + "Z"
    try:
        body, content_type = http_get_text(url, timeout=25)
    except urllib.error.URLError as exc:
        return {
            "url": url,
            "status": "error",
            "error": str(exc),
            "fetched_at": fetched_at,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "url": url,
            "status": "error",
            "error": str(exc),
            "fetched_at": fetched_at,
        }

    if "html" not in content_type.lower():
        return {
            "url": url,
            "status": "skipped_non_html",
            "content_type": content_type,
            "fetched_at": fetched_at,
        }

    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
    title = strip_tags(title_match.group(1)) if title_match else ""

    body_clean = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body_clean = re.sub(r"<style[^>]*>.*?</style>", " ", body_clean, flags=re.IGNORECASE | re.DOTALL)
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", body_clean, flags=re.IGNORECASE | re.DOTALL)
    para_text = [strip_tags(p) for p in paragraphs]
    para_text = [p for p in para_text if len(p) > 40]
    excerpt = " ".join(para_text[:3]).strip()
    if len(excerpt) > 1800:
        excerpt = excerpt[:1800].rsplit(" ", 1)[0] + "..."

    return {
        "url": url,
        "status": "ok",
        "content_type": content_type,
        "title": title,
        "excerpt": excerpt,
        "fetched_at": fetched_at,
    }


def build_topic_payload(topic: dict, year: str):
    bullets = parse_bullets(topic["body_html"])
    links = []
    for li in bullets:
        for link in li["links"]:
            href = link.get("href", "").strip()
            if href:
                links.append({"url": href, "anchor_text": link.get("text", "").strip()})
    unique_link_urls = unique_preserve([l["url"] for l in links])

    sources = []
    for url in unique_link_urls:
        src = fetch_source_excerpt(url)
        anchor_texts = [l["anchor_text"] for l in links if l["url"] == url and l["anchor_text"]]
        if anchor_texts:
            src["anchor_texts"] = unique_preserve(anchor_texts)
        sources.append(src)

    entities = classify_topic_entities(bullets)
    topic_text = "\n".join(f"- {li['text']}" for li in bullets)
    linked_text_parts = []
    for src in sources:
        if src.get("status") == "ok" and src.get("excerpt"):
            title = src.get("title", "").strip()
            prefix = f"[{title}] " if title else ""
            linked_text_parts.append(prefix + src["excerpt"])
    linked_text = "\n\n".join(linked_text_parts).strip()
    combined_text = (topic_text + "\n\n" + linked_text).strip() if linked_text else topic_text

    topic_payload = {
        "title": topic["title"],
        "year": year,
        "source_page": f"{BASE_URL}#/themes/{year}/guidingquestions",
        "extracted_at": dt.datetime.utcnow().isoformat() + "Z",
        "topic_text": topic_text,
        "linked_text": linked_text,
        "combined_text": combined_text,
        "artworks": entities["artworks"],
        "persons": entities["persons"],
        "concepts": entities["concepts"],
    }

    sources_payload = {
        "title": topic["title"],
        "year": year,
        "source_page": f"{BASE_URL}#/themes/{year}/guidingquestions",
        "bundle_source": discover_bundle_url(),
        "topic_links": sources,
    }
    return topic_payload, sources_payload


def render_notes_md(topic_payload: dict, sources_payload: dict) -> str:
    lines = []
    lines.append(f"# {topic_payload['title']}")
    lines.append("")
    lines.append(f"- Year: {topic_payload['year']}")
    lines.append(f"- Source page: {topic_payload['source_page']}")
    lines.append(f"- Extracted at: {topic_payload['extracted_at']}")
    lines.append("")
    lines.append("## Topic Material")
    lines.append("")
    lines.append(topic_payload["topic_text"] or "(none)")
    lines.append("")
    lines.append("## Linked Source Text")
    lines.append("")
    lines.append(topic_payload["linked_text"] or "(none)")
    lines.append("")
    lines.append("## Artworks")
    lines.append("")
    if topic_payload["artworks"]:
        for item in topic_payload["artworks"]:
            lines.append(f"- {item['creator']} | {item['work']}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Persons")
    lines.append("")
    if topic_payload["persons"]:
        for person in topic_payload["persons"]:
            lines.append(f"- {person}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Concepts")
    lines.append("")
    if topic_payload["concepts"]:
        for concept in topic_payload["concepts"]:
            lines.append(f"- {concept}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Source Links")
    lines.append("")
    for src in sources_payload["topic_links"]:
        status = src.get("status", "unknown")
        title = src.get("title", "").strip()
        label = f"{title} ({status})" if title else status
        lines.append(f"- {src['url']} - {label}")
    return "\n".join(lines).strip() + "\n"


def ensure_topic_folder(topic_title: str) -> Path | None:
    slug = slugify(topic_title)
    out_dir = TOPICS_DIR / slug
    if out_dir.exists():
        answer = input(f"Overwrite existing topic folder for '{topic_title}'? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print(f"Skipping '{topic_title}' (overwrite not confirmed).")
            return None
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_topic_files(topic_payload: dict, sources_payload: dict):
    out_dir = ensure_topic_folder(topic_payload["title"])
    if out_dir is None:
        return False
    (out_dir / "topic.json").write_text(
        json.dumps(topic_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "sources.json").write_text(
        json.dumps(sources_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "notes.md").write_text(
        render_notes_md(topic_payload, sources_payload),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir}")
    return True


def load_topics(year: str):
    bundle_url = discover_bundle_url()
    bundle_text, _ = http_get_text(bundle_url)
    data_var = extract_theme_data_variable(bundle_text, year)
    return extract_topics_from_data_var(bundle_text, data_var)


def normalize_lookup_map(topics):
    mapping = {}
    for topic in topics:
        title = topic["title"]
        mapping[title.lower()] = topic
    return mapping


def parse_args():
    parser = argparse.ArgumentParser(description="Extract WSC topics into JSON + markdown.")
    parser.add_argument("--list", action="store_true", help="List available topic titles.")
    parser.add_argument(
        "--topics",
        type=str,
        default="",
        help='Comma-separated topic titles to extract (or "all").',
    )
    parser.add_argument(
        "--year",
        type=str,
        default=DEFAULT_YEAR,
        help=f"Theme year to extract (default: {DEFAULT_YEAR}).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.list and not args.topics:
        print("Provide either --list or --topics.")
        return 1

    try:
        topics = load_topics(args.year)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load WSC topics: {exc}")
        return 1

    if args.list:
        for topic in topics:
            print(topic["title"])
        return 0

    selected_raw = [s.strip() for s in args.topics.split(",") if s.strip()]
    if not selected_raw:
        print("No topics supplied.")
        return 1

    if len(selected_raw) == 1 and selected_raw[0].lower() == "all":
        selected_topics = topics
    else:
        lookup = normalize_lookup_map(topics)
        selected_topics = []
        for name in selected_raw:
            topic = lookup.get(name.lower())
            if not topic:
                print(f"Warning: topic not found, skipping: {name}")
                continue
            selected_topics.append(topic)
        if not selected_topics:
            print("No valid topics selected.")
            return 1

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    wrote_any = False
    for topic in selected_topics:
        print(f"Extracting: {topic['title']}")
        try:
            topic_payload, sources_payload = build_topic_payload(topic, args.year)
            wrote = write_topic_files(topic_payload, sources_payload)
            wrote_any = wrote_any or wrote
        except Exception as exc:  # noqa: BLE001
            print(f"Failed extracting '{topic['title']}': {exc}")
    return 0 if wrote_any else 1


if __name__ == "__main__":
    sys.exit(main())
