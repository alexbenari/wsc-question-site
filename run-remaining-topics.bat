@echo off
setlocal
cd /d "%~dp0"

if not exist "codex-topic-extraction-single-topic-prompt.md" (
  echo Missing file: codex-topic-extraction-single-topic-prompt.md
  exit /b 1
)

if not exist "wsc-topics.html" (
  echo Missing file: wsc-topics.html
  exit /b 1
)

echo Running extraction for remaining topics...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$template = Get-Content -Raw 'codex-topic-extraction-single-topic-prompt.md';" ^
  "$topics = @(" ^
    "'Introductory Questions'," ^
    "'Progress, Not Regress'," ^
    "'More To Do Than Can Ever Be Listed'," ^
    "'There’s a Draft in Here'," ^
    "'We’re All in This to Get There'," ^
    "'Where the Sidewalk Starts'," ^
    "'Monkey See, Monkey Prototype'," ^
    "'The Lovely and the Liminal'," ^
    "'Going Pains'," ^
    "'Home and Wandering'," ^
    "'Where We’re Going, We’ll Still Need Them'," ^
    "'Call of Duty-Free'," ^
    "'Next Year in Futurism'," ^
    "'Concluding Questions'" ^
  ");" ^
  "function Get-Slug([string]$s) { $slug = $s.ToLowerInvariant(); $slug = $slug -replace '[’'']',''; $slug = $slug -replace '[^a-z0-9]+','-'; $slug = $slug.Trim('-'); return $slug }" ^
  "foreach($topic in $topics) {" ^
    "$slug = Get-Slug $topic;" ^
    "$outDir = Join-Path 'topics' $slug;" ^
    "if (Test-Path $outDir) { Write-Host ('SKIP (exists): ' + $topic + ' -> ' + $outDir); continue }" ^
    "Write-Host ('START: ' + $topic);" ^
    "$prompt = $template.Replace('<TOPIC_NAME>', $topic);" ^
    "$prompt | codex --search exec --full-auto --cd . -;" ^
    "if ($LASTEXITCODE -ne 0) { Write-Host ('FAILED: ' + $topic); exit $LASTEXITCODE }" ^
    "Write-Host ('DONE: ' + $topic);" ^
    "Write-Host '';" ^
  "}" ^
  "Write-Host 'All remaining topics processed.';"

if errorlevel 1 (
  echo.
  echo Batch failed.
  exit /b 1
)

echo.
echo Batch completed successfully.
exit /b 0

