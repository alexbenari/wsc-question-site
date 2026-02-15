# Question Generation Workflow

## 0) Unified CLI (recommended)
Use:
- `question-generator.py`

Single-topic example (50 questions, default single-topic categories):
```powershell
python .\question-generator.py single --topic the-end-is-nearish --count 50
```

Single-topic with custom output filename:
```powershell
python .\question-generator.py single --topic the-end-is-nearish --count 50 --output .\nearish-50.jsonl
```

Single-topic without validation (opt out):
```powershell
python .\question-generator.py single --topic the-end-is-nearish --count 50 --no-validate
```

Batch example (300 questions, all categories):
```powershell
python .\question-generator.py batch --count 300
```

Batch with custom output filename:
```powershell
python .\question-generator.py batch --count 300 --output .\question-pool-v1.jsonl
```

Batch with selected categories and validation:
```powershell
python .\question-generator.py batch --count 300 --categories "single_topic_understanding,context_clues,thematic_synthesis"
```

Batch without validation (opt out):
```powershell
python .\question-generator.py batch --count 300 --no-validate
```

## 1) Single-topic generation
Use prompt template:
- `codex-question-generation-single-topic-prompt.md`

PowerShell example (`the-end-is-nearish`, 40 questions):
```powershell
$prompt = Get-Content -Raw .\codex-question-generation-single-topic-prompt.md
$prompt = $prompt.Replace('<TOPIC_SLUG>', 'the-end-is-nearish').Replace('<QUESTION_COUNT>', '40').Replace('<CATEGORY_LIST_OR_ALL>', 'single_topic_understanding,context_clues')
$prompt | codex --search exec --full-auto --cd . -
```

## 2) Full batch generation
Use prompt template:
- `codex-question-generation-batch-prompt.md`

PowerShell example (300 questions):
```powershell
$prompt = Get-Content -Raw .\codex-question-generation-batch-prompt.md
$prompt = $prompt.Replace('<QUESTION_COUNT>', '300').Replace('<CATEGORY_LIST_OR_ALL>', 'all')
$prompt | codex --search exec --full-auto --cd . -
```

## 3) Validate question pool
Validate JSONL shape + key guideline constraints:
```powershell
python .\validate-question-pool.py --input .\question-pool.jsonl --topics-dir .\topics --allowed-categories all --check-category-balance
```

Optional strict mode (warnings fail build):
```powershell
python .\validate-question-pool.py --input .\question-pool.jsonl --topics-dir .\topics --allowed-categories all --check-category-balance --strict-warnings
```
