You are generating World Scholar's Cup-style multiple-choice questions for a single topic.

## Inputs
- Topic file: `topics/<TOPIC_SLUG>/topic.json`
- Question rules: `question-structure-guideliens.md`
- Schema: `wsc-question-schema.json`

## Task
Generate `<QUESTION_COUNT>` questions for this one topic and write them as JSONL to:
- `<OUTPUT_FILE>`

Allowed categories:
- `<CATEGORY_LIST_OR_ALL>`
- Default for single-topic mode: `single_topic_understanding,context_clues`
- If `all` is requested, treat it as `single_topic_understanding,context_clues` for single-topic mode.
- Do NOT use `comparative_consequences` or `thematic_synthesis` in single-topic mode (they require two topics).

## Hard requirements
- Output must be valid JSONL: one JSON object per line.
- Each object must conform to `wsc-question-schema.json`.
- `question` is one sentence, max 22 words.
- Exactly 5 choices.
- `correct` is one of `A`-`E` and must match the best choice.
- `topics` must contain exactly one item: the topic title from `topic.json`.
- Correct answer must not be longer than any distractor by more than one word.
- Distractors must be plausible and source-faithful to topic material.
- Do not include explanations.

## Quality targets
- ~30% negatively phrased questions (e.g., NOT / EXCEPT / least likely).
- At least 20% of questions should involve artworks from the topic.
- At least 20% should involve named people from the topic.
- Keep answer options distinct (not synonymous).
- Generate roughly equal counts across the allowed categories.
- Randomize `correct` placement (A-E) so distribution is not heavily skewed.

## Source fidelity
- Use only knowledge present in:
  - `topic_text`
  - `learning_guidelines`
  - `linked_text_entries`
  - `artworks`
  - `concepts`
  - `persons`
- If uncertain, skip the candidate question.

## Output format example (single line)
{"category":"single_topic_understanding","question":"Which term best describes ...?","choices":["...","...","...","...","..."],"correct":"C","topics":["The End is Nearish"]}

## Final step
- Run a verification loop before finalizing:
  1. Write candidate file.
  2. Run validator:
     - `python validate-question-pool.py --input <OUTPUT_FILE> --topics-dir topics --allowed-categories "<CATEGORY_LIST_OR_ALL>" --check-category-balance`
  3. If validation fails, repair and rewrite until it passes.
- At end, print:
  - output file path
  - question count
  - estimated negative/artwork/person percentages
