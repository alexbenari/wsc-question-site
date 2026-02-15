You are generating a full World Scholar's Cup-style question pool across extracted topics.

## Inputs
- Topic directory: `topics/` (all `topics/*/topic.json`)
- Question rules: `question-structure-guideliens.md`
- Schema: `wsc-question-schema.json`

## Task
Generate `<QUESTION_COUNT>` questions across all available topics and write JSONL to:
- `<OUTPUT_FILE>`

Allowed categories:
- `<CATEGORY_LIST_OR_ALL>`
- If set to `all`, use all 4 categories.
- If set to a comma-separated subset, generate only from those categories.

## Category requirements
- Allowed categories:
  - `single_topic_understanding`
  - `context_clues`
  - `comparative_consequences`
  - `thematic_synthesis`
- For `comparative_consequences` and `thematic_synthesis`, `topics` must include exactly 2 topic titles.
- For `single_topic_understanding` and `context_clues`, prefer exactly 1 topic title.

## Hard requirements
- Output must be valid JSONL: one JSON object per line.
- Every line must conform to `wsc-question-schema.json`.
- Each question is one sentence, max 22 words.
- Exactly 5 choices.
- `correct` is one of `A`-`E`.
- Correct answer length rule: correct choice must not exceed any distractor by more than one word.
- No answer explanations or answer-revealing wording.
- Distractors must stay plausible and non-trivial.

## Pool-level targets (must satisfy)
- ~30% negatively phrased questions.
- At least 20% artwork-based questions.
- At least 20% named-person-based questions.
- Broad coverage of topic set (avoid over-concentrating on 1-2 topics).
- Generate roughly equal counts across the allowed categories (target near-even split).
- Randomize `correct` placement (A-E) so distribution is not heavily skewed.

## Source fidelity
- Use only extracted topic data from `topic.json` files.
- Do not invent entities outside extracted material.
- If evidence is weak, discard the candidate question.

## Generation process
1. Load all topic JSON files.
2. Build candidate question sets by category.
3. Balance pool to meet quotas and category/topic diversity.
4. Write JSONL.
5. Run validator:
   - `python validate-question-pool.py --input <OUTPUT_FILE> --topics-dir topics --allowed-categories "<CATEGORY_LIST_OR_ALL>" --check-category-balance`
6. If validator fails, repair and rewrite until valid.

## Output format example (single line)
{"category":"comparative_consequences","question":"If A mirrors B, what consequence is most likely shared?","choices":["...","...","...","...","..."],"correct":"D","topics":["The End is Nearish","Progress, Not Regress"]}

## Final report
- question count
- category counts
- negative/artwork/person percentages
- topics coverage summary
- validator result
