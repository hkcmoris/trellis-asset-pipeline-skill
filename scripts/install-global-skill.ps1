[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SkillSource = Join-Path $RepoRoot ".codex\skills\trellis-asset-pipeline"
$GlobalSkillsRoot = Join-Path $HOME ".codex\skills"
$SkillTarget = Join-Path $GlobalSkillsRoot "trellis-asset-pipeline"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $SkillSource -PathType Container)) {
    throw "Repo skill directory was not found: $SkillSource"
}

New-Item -ItemType Directory -Force -Path $GlobalSkillsRoot | Out-Null

if (Test-Path -LiteralPath $SkillTarget) {
    $item = Get-Item -LiteralPath $SkillTarget -Force
    $targetMatches = $false

    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        $existingTarget = $item.Target
        if ($existingTarget) {
            if ($existingTarget -is [array]) {
                $existingTarget = $existingTarget[0]
            }

            try {
                $resolvedExisting = (Resolve-Path -LiteralPath $existingTarget).Path
                $resolvedSource = (Resolve-Path -LiteralPath $SkillSource).Path
                $targetMatches = $resolvedExisting -eq $resolvedSource
            }
            catch {
                $targetMatches = $false
            }
        }
    }

    if (-not $targetMatches) {
        throw "Global skill path already exists and does not point at this repository: $SkillTarget. Remove or rename it manually; nothing was changed."
    }

    Write-Host "OK       Global Codex skill junction already points at this repository."
}
else {
    New-Item -ItemType Junction -Path $SkillTarget -Target $SkillSource | Out-Null
    Write-Host "CREATED  $SkillTarget"
    Write-Host "      -> $SkillSource"
}

[Environment]::SetEnvironmentVariable(
    "TRELLIS_PIPELINE_ROOT",
    $RepoRoot,
    [EnvironmentVariableTarget]::User
)
$env:TRELLIS_PIPELINE_ROOT = $RepoRoot

Write-Host "SET      TRELLIS_PIPELINE_ROOT=$RepoRoot"

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    Write-Warning "The pipeline virtual environment was not found at $VenvPython. Create .venv and install the project editable before using the skill globally."
}
else {
    & $VenvPython -c "import trellis_pipeline; print('OK       Pipeline import works from repo .venv')"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The repo .venv exists but trellis_pipeline could not be imported. Run: .\.venv\Scripts\python.exe -m pip install -e ."
    }
}

Write-Host ""
Write-Host "Global skill setup complete."
Write-Host "Restart Codex (and any already-open terminal used by Codex) so the new user environment variable is inherited."
Write-Host ""
Write-Host "From any workspace, invoke the pipeline with:"
Write-Host '  & "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline doctor'
