You are extracting one World Scholar's Cup 2026 Guiding Questions topic into structured files.

## Task
Extract the topic named: `<TOPIC_NAME>`

Primary source file (local snapshot):
`wsc-topics.html`

Reference source page:
`https://themes.scholarscup.org/#/themes/2026/guidingquestions`

Output folder root:
`topics/`

Create exactly these files:
1. `topics/<slug>/topic.json`
2. `topics/<slug>/sources.json`
3. `topics/<slug>/notes.md`

Use `<slug>` as a lowercase hyphenated slug of the actual matched topic title.

## Matching and overwrite behavior
- Match topic title case-insensitively.
- If no topic matches: print a warning and stop without creating files.
- If `topics/<slug>/` already exists: ask for explicit overwrite confirmation before replacing it.

## Source usage policy
- Use `wsc-topics.html` as the authoritative source for WSC topic-section text and links.
- Do not scrape the live WSC page for topic text if the local file is present and readable.
- You may fetch external linked pages to enrich `artworks`, `concepts`, and `linked_text_entries`.
- If `wsc-topics.html` is missing or unreadable, stop and report the issue (do not silently switch sources).

## Core extraction rules

### 1) Topic text separation
- `topic_text` must include only text from the WSC topic section itself.
- Do not place linked-source content inside `topic_text`.

### 2) Learning guidelines
- Identify learner-directed instructional excerpts in the WSC topic text (for example: "Learn more...", "Explore...", "Discuss with your team...").
- Store them in `learning_guidelines` as clean standalone strings.

### 3) Link routing logic
For each link discovered in the topic:
- If it points to an artwork/work source:
  - Do NOT add a generic linked-text entry.
  - Add or update an item in `artworks`.
- If it points to a concept/term/event source:
  - Do NOT add a generic linked-text entry.
  - Add or update an item in `concepts`.
- Otherwise:
  - Add a summary entry in `linked_text_entries`.

### 4) Unlinked concepts/artworks
- If concepts or artworks appear in topic lists without links, still create entries.
- Research them from reputable sources and fill descriptions.
- Record provenance in `sources.json` with `discovered_by: "unlinked_topic_item"`.

## Data requirements

### topic.json
Write valid JSON with at least:
- `title`
- `year` = `"2026"`
- `source_page`
- `source_file` = `"wsc-topics.html"`
- `extracted_at` (ISO-8601 UTC)
- `topic_text`
- `learning_guidelines` (array of strings)
- `linked_text_entries` (array)
- `artworks` (array)
- `concepts` (array)
- `persons` (array of human individuals only)

`linked_text_entries` item shape:
- `url`
- `anchor_texts` (array)
- `summary`

`artworks` item shape:
- `creator`
- `title`
- `year` (if known)
- `source_links` (array)
- `description` with:
  - physical/content description summary
  - key facts about work and artist
  - brief interpretation

`concepts` item shape:
- `name`
- `year` (if applicable)
- `source_links` (array)
- `description` with:
  - definition/what it is
  - key facts/context
  - relevance to this topic

### sources.json
Include provenance and source tracking:
- `title`
- `year`
- `source_page`
- `source_file`
- `extracted_at`
- `bundle_or_page_sources` (what WSC sources were used)
- `links` array with per-link:
  - `url`
  - `anchor_texts`
  - `classification` (`artwork` | `concept` | `general`)
  - `status` (`ok` | `error` | `skipped_non_html`)
  - `title` (if available)
  - `summary_or_excerpt`
  - `fetched_at`
- `derived_items` for unlinked concepts/artworks with supporting references.

### notes.md
Human-readable summary derived from JSON:
- Title and metadata
- Topic text
- Learning guidelines
- Linked text entries
- Artworks
- Concepts
- Persons
- Source/provenance notes

## Quality constraints
- Do not invent facts.
- Use concise, factual summaries.
- Normalize names/titles consistently.
- `persons` must contain only human individuals (no artworks, concepts, groups, or institutions).
- Keep section boundaries strict:
  - topic prose in `topic_text`
  - instructional prompts in `learning_guidelines`
  - general link summaries in `linked_text_entries`
  - artwork/concept knowledge in their dedicated arrays

## Final report
At the end, print:
- matched topic title
- output folder path
- count of links processed
- count of artworks/concepts/persons
- count of inaccessible links
