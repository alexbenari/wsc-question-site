# Question Generation Workflow

## 0) Unified CLI (recommended)
Use:
- `question-generator.py`

Staged delivery:
- Staging is handled by Codex according to prompt instructions (not by this wrapper).
- The wrapper sends one generation request with your requested count/output.
- After generation, the wrapper runs one final validator pass (non-fatal by default).
- If final validation fails, output file is still kept and run exits successfully.

Single-topic example (50 questions, default single-topic categories):
```powershell
python .\question-generator.py single --topic the-end-is-nearish --count 50
```

Single-topic with custom output filename:
```powershell
python .\question-generator.py single --topic the-end-is-nearish --count 50 --output .\nearish-50.jsonl
```

Batch example (300 questions, all categories):
```powershell
python .\question-generator.py batch --count 300
```

Batch with custom output filename:
```powershell
python .\question-generator.py batch --count 300 --output .\question-pool-v1.jsonl
```

Batch with selected categories:
```powershell
python .\question-generator.py batch --count 300 --categories "single_topic_understanding,context_clues,thematic_synthesis"
```

Artwork-only flow (all questions about artworks; paintings include additional palette questions):
```powershell
python .\question-generator.py batch --count 200 --flow artworks
```

Artwork flow rules are loaded from:
- `flows/flow-artworks.md`

Artwork-only flow with custom output:
```powershell
python .\question-generator.py batch --count 200 --flow artworks --output .\question-pool-artworks-v1.jsonl
```

Skip wrapper final validation:
```powershell
python .\question-generator.py batch --count 300 --no-final-validate
```

## 1) Manual prompt run (optional)
Use unified prompt template:
- `codex-question-generation-batch-prompt.md`

PowerShell example (300 questions):
```powershell
$prompt = Get-Content -Raw .\codex-question-generation-batch-prompt.md
$prompt = $prompt.Replace('<QUESTION_COUNT>', '300').Replace('<CATEGORY_LIST_OR_ALL>', 'all').Replace('<OUTPUT_FILE>', 'question-pool.jsonl').Replace('<SCOPE_SOURCE>', 'topics/ (all topics/*/topic.json)').Replace('<SCOPE_PROFILE>', '- Multi-topic scope: use all topic files under topics/.').Replace('<FLOW_RULES>', '- No additional flow-specific rules.')
$prompt | codex --search exec --full-auto --cd . -
```

## 2) Validate question pool
Validate JSONL shape + key guideline constraints:
```powershell
python .\validate-question-pool.py --input .\question-pool.jsonl --topics-dir .\topics --allowed-categories all
```
