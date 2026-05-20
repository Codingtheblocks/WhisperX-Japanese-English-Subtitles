$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Config = Join-Path $Root "config.yaml"

& $Python (Join-Path $Root "caption_pipeline.py") --config $Config @args
