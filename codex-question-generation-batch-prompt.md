You are generating a full World Scholar's Cup-style question pool across extracted topics.

## Quality charter (primary objective)
- Primary objective: produce genuinely strong, WSC-style questions; passing validation is secondary.
- Do not optimize for minimum-effort compliance.
- Favor depth, nuance, and plausible reasoning over formulaic templates.
- Each question should feel like it was written by a careful human quiz writer, not a pattern filler.
- If a candidate question is shallow, repetitive, list-matching, or obvious, discard it and write a better one.
- Maintain diversity in:
  - stem style
  - reasoning mode (recall, inference, comparison, synthesis)
  - difficulty and distractor strategy
- Before finalizing each batch, run a self-audit on a random sample of at least 10 questions:
  - rewrite any question with generic phrasing, weak distractors, or boilerplate explanation.

## Inputs
- Scope source: `<SCOPE_SOURCE>`
- Question rules: `question-structure-guideliens.md`
- Schema: `wsc-question-schema.json`

## Task
Generate `<QUESTION_COUNT>` questions across all available topics and write JSONL to:
- `<OUTPUT_FILE>`

## Scope profile
<SCOPE_PROFILE>

## Flow-specific rules
<FLOW_RULES>

## Generation mode constraint
- Do NOT generate questions by writing/running code or scripts.
- Do NOT create helper generators in Python/JS/etc.
- Use model reasoning directly to author the question, correct answer and distractors.
- Only write/update the target JSONL output file
- Allow multi-turn staged delivery : you can choose to split the total requested count into smaller batches and generate each separately
- Treat validation as a black box:
  - Run the validator command only.
  - Do NOT read `validate-question-pool.py` or tailor output to validator implementation details.
  - Follow this prompt and source material, not validator internals.
- Non-interactive execution:
  - Do not ask the user follow-up questions during processing.
  - Choose reasonable defaults from this prompt when needed.
  - If a requirement is truly impossible to satisfy without user input, print:
    1) exact blocking requirement,
    2) why no valid default exists,
    3) what specific input is required,
    then terminate.

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
- For `comparative_consequences` and `thematic_synthesis`, `topics` must include exactly 2 topic titles (unless scope profile overrides).
- For `single_topic_understanding` and `context_clues`, prefer exactly 1 topic title.

## Hard requirements
- Output must be valid JSONL: one JSON object per line.
- Every line must conform to `wsc-question-schema.json`.
- Include a compact unique question `id` per item:
  - format: `q_<alphanumeric>`
  - length target: 10-14 chars total
  - example: `q_A7k29Zp1`
- Each question is one sentence, max 22 words.
- Exactly 5 choices.
- `correct` is one of `A`-`E`.
- Include `explanation` with 2-5 sentences:
  - must explain why the correct answer is correct
  - may briefly explain why one or more distractors are wrong
  - may add concise extra context relevant to the topic(s)
- For single-topic scope, each question's `topics` must contain exactly one topic title from that scope.
- Correct answer length rule: correct choice must not exceed any distractor by more than one word.
- Do not embed explanation clues in the question wording itself.
- Choices must not include explanations/justifications (e.g., "because", "since", "therefore"). Put reasoning only in `explanation`.
- Distractors must stay plausible and non-trivial.
- Do NOT use low-effort list-membership templates such as:
  - "Which listed concept/artwork belongs to this topic?"
  - "Which listed item best fits this topic?"
  - Any question whose main task is matching an option to a topic list without reasoning.
- Each explanation must be question-specific:
  - reference concrete content (terms, people, artworks, events)
  - avoid generic boilerplate like "it matches extracted material" or "others do not belong here"
  - A question should never reference the topic as part of the question. Avoid asking about the topic itself, ask only about the contents of the topic. Here are some exampels of BAD questions of this sort:
    - Which navigation method in this topic relies on stars, swells, and winds rather than magnetic instruments? [because "in thos topic" is sued. Witout it the question is OK]
    - "Which is NOT a project-management concept listed in this topic?" [becuase of "in this topic".]
    - "Which practice is NOT a list framework named in More To Do Than Can Ever Be Listed?"] [becaosue of "nameded in More To Do Than Can Ever Be Listed?" since More To Do Than Can Ever Be Listed is a topic name ]
  - A question should never be about whether something is included im the topic. I.e. avoid questions like the following and similar structures:
    -  "Which artwork in There's a Draft in Here is NOT associated with Edvard Munch?" where "There's a Draft in Here" is the name of a topic. 
    -  "Which term describes adolescent preference for novelty emphasized in Going Pains?" -> because "Going Pains" is a topic name. 
    -  "A teammate studies this topic; which listed concept best fits?"
    -  "Which listed concept belongs to this topic?"

## Pool-level targets (must satisfy)
- ~30% negatively phrased questions.
- At least 20% artwork-based questions.
- At least 20% named-person-based questions.
- Generate roughly equal questions counts across topics
- Generate roughly equal counts across the allowed categories (target near-even split).
- Randomize `correct` placement (A-E) so distribution is not heavily skewed.

## Source fidelity
- Use only extracted topic data from `topic.json` files.
- Do not invent entities outside extracted material.
- If evidence is weak, discard the candidate question.

## Generation process
1. If `<QUESTION_COUNT>` is large you can choose to generate in batches (for example 5x150 for 750)
2. Load all topic JSON files.
3. Plan in advance how many questions you well generate per question category, so that the distribution is about equal (overall or per batch if you are wqorkign in batches)
4. Generate questions according to the amount planned. 
5. Write output JSONL.
6. Run validator: the validator only checks very simple technical requirements like number of answers, jsonl format and such.
   - `python validate-question-pool.py --input <OUTPUT_FILE> --topics-dir topics --allowed-categories "<CATEGORY_LIST_OR_ALL>" 
7. If validator fails:
  7.1 for errors that involve a single question - repair the failed questions
  7.2 For correct-letter distribution skew -> change the placement of correct answers in questions so as to be tabdomly distributed
  7.3 For repeated-answer run length -> break the repeated run by changing the location of the correct answer in at least half of the questions in the run 
  7.4 After fixing rerun the validator. Repeat until all questions pass validation.

## Output format example (single line)
{"id":"q_A7k29Zp1","category":"comparative_consequences","question":"If A mirrors B, what consequence is most likely shared?","choices":["...","...","...","...","..."],"correct":"D","topics":["The End is Nearish","Progress, Not Regress"],"explanation":"Option D best fits both topics because ... . Option A overstates ... . This comparison reflects ... in both materials."}

## Final report
- question count
- category counts
- negative/artwork/person percentages
- topics coverage summary
- validator result
