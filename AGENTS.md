# AGENTS.md

## Mission

Build a reliable, local-first asset-generation pipeline that lets an agent turn a short request such as:

~~~text
generate supamon game asset bush
~~~

into a usable 3D game asset through:

~~~text
image generation -> ComfyUI/TRELLIS -> GLB -> Blender -> FBX
~~~

Optimize for repeatability, debuggability, sensible GPU usage, and minimal unnecessary LLM interaction.

## Current implementation state

Implemented:

- repo-scoped Codex skill under .codex/skills/trellis-asset-pipeline
- .env-based local configuration
- environment diagnostics
- ComfyUI API health check
- automatic ComfyUI startup using COMFYUI_START_BAT
- local waiting for ComfyUI startup
- separate TRELLIS example/user/repo workflow discovery
- read-only ComfyUI workflow format/node inspection

Not implemented yet:

- image-generation provider integration
- ComfyUI workflow submission
- WebSocket job completion
- GLB discovery/retrieval
- Blender GLB-to-FBX processing
- workflow benchmarking/optimization engine

Do not claim an unimplemented stage works.

## Core principles

### 1. Prefer APIs over UI automation

Use the ComfyUI API and Blender command-line/Python interfaces whenever possible.

Computer-control/UI automation is a last resort.

### 2. Do not make the LLM babysit long jobs

TRELLIS generation can take minutes or longer.

The local orchestration layer should submit, wait locally, collect the result, and return one compact completion result. Do not repeatedly invoke Codex merely to ask whether generation has finished.

### 2a. Long jobs are final-only at the agent boundary

All intermediate ComfyUI/TRELLIS progress must stay inside the local process.

Do not expose sampler steps, percentages, WebSocket progress events, queue polling, or periodic "still running" checks to Codex. Do not read a live log from agent turns.

For any improvised long-running command before the native generation worker exists, use:

~~~powershell
python -m trellis_pipeline quiet-run --log <local-log> -- <command> <args...>
~~~

The wrapper must block, capture stdout/stderr to disk, and return only after completion. A failed process may expose its log tail after exit.

### 3. Keep machine configuration local

Local values belong in .env, which is ignored by Git. .env.example documents supported settings.

### 4. Treat workflow sources differently

- TRELLIS_EXAMPLE_WORKFLOWS_DIR: reference workflows shipped with the custom node; read-only.
- COMFYUI_WORKFLOWS_DIR: user-owned saved/experimental workflows; inspect/import but do not overwrite without explicit instruction.
- workflows/: repository-owned known-good API workflows; version and optimize here.

### 5. Keep workflows versioned and reusable

Known-good ComfyUI API workflow JSON belongs under workflows/.

Do not dynamically rebuild an entire TRELLIS graph unless there is a strong reason. Prefer loading a known workflow and changing explicit inputs or parameters.

### 6. Optimize scientifically

When tuning a workflow:

- establish a baseline first
- record runtime
- record relevant GPU/VRAM information when available
- change one meaningful variable at a time
- preserve input and seed when a fair visual comparison requires it
- record failures and OOM conditions
- stop obviously bad experiment branches early
- keep known-good configurations reproducible

The target is the best useful game asset for the requested time/quality budget, not maximum theoretical fidelity.

### 7. Separate generation quality levels

Design around draft, balanced, and quality.

Draft mode should avoid expensive final-only work. Geometry exploration should not require full-resolution final texturing on every attempt.

### 8. Keep the public repository clean

Never commit credentials, private paths/URLs, private source images, generated assets unless deliberately public test fixtures, or model weights/checkpoints.

## Cross-workspace execution

The pipeline may be invoked while Codex is working in another repository such as a game project.

When TRELLIS_PIPELINE_ROOT is set, use the pipeline repository own virtual environment:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline <args>
~~~

Do not assume the current workspace contains trellis_pipeline, .env, or the pipeline .venv.

The root-level scripts/install-global-skill.ps1 installs the repo skill globally via a junction and sets TRELLIS_PIPELINE_ROOT as a user environment variable.

If TRELLIS_PIPELINE_ROOT is absent and the current workspace is this pipeline repository, local invocation is fine. Otherwise report that global setup is required rather than guessing a path.

## Local commands

Use the project virtual environment.

~~~powershell
.\.venv\Scripts\Activate.ps1
trellis-pipeline doctor
trellis-pipeline comfy ensure
trellis-pipeline quiet-run --log logs\\job.log -- <long-command> <args...>
trellis-pipeline workflows list
trellis-pipeline workflows inspect <workflow>
~~~

Equivalent module invocation should remain supported:

~~~powershell
python -m trellis_pipeline ...
~~~

## Configuration

Supported environment variables currently include:

- COMFYUI_URL
- COMFYUI_ROOT
- COMFYUI_START_BAT
- TRELLIS_EXAMPLE_WORKFLOWS_DIR
- COMFYUI_WORKFLOWS_DIR
- COMFYUI_INPUT_DIR
- COMFYUI_OUTPUT_DIR
- BLENDER_EXE
- ASSET_OUTPUT_DIR
- COMFYUI_STARTUP_TIMEOUT_SECONDS
- COMFYUI_HEALTH_TIMEOUT_SECONDS
- NVIDIA_SMI_EXE

Default ComfyUI development URL is http://127.0.0.1:8188 but must remain overridable.

## Workflow discovery and inspection

Workflow inspection must remain read-only.

For UI-format workflow JSON:

- report node type/title
- report positional widgets as widget[index]
- do not invent parameter names from positions

For API-format workflow JSON:

- report class_type
- report scalar named inputs
- preserve linked inputs without pretending they are scalar parameters

When a workflow name is ambiguous, require --source or a more specific relative path.

## ComfyUI integration

Keep the integration layer narrow: availability/startup, workflow submission, input upload/reference, local completion waiting, failure detection, output metadata/files, concise final status.

Avoid leaking raw high-volume ComfyUI event streams into agent context.

## TRELLIS workflows

Treat workflow JSON as source code.

Keep diffs understandable, avoid unrelated node churn, document performance-sensitive changes, preserve known-good baselines, and distinguish parameter changes from topology changes.

The pipeline should eventually submit API-format workflow JSON to ComfyUI.

## Blender

Blender processing should be deterministic, scriptable, and headless.

Do not apply destructive cleanup/decimation merely because it is available.

## Performance and benchmarking

The initial reference machine may be an RTX 3060 12 GB, but implementation decisions must remain configurable.

Prioritize detecting VRAM pressure, CPU/GPU offloading, low utilization, expensive remesh/reconstruction, excessive sampling, high intermediate resolutions, and repeated final-quality texturing during geometry iteration.

Benchmark data must distinguish measured values from assumptions.

## Coding expectations

- Python 3.11+.
- Prefer the standard library unless a dependency materially improves the project.
- Keep modules small with narrow responsibilities.
- Use type hints and actionable errors.
- Keep Windows compatibility in mind.
- Keep orchestration testable without a live GPU where practical.

## Documentation

Do not document a feature as implemented until the repository actually provides it.

## Change discipline

Before a substantial change:

1. inspect relevant existing files
2. preserve known-good workflows/configuration
3. make the smallest coherent change
4. test what can be tested
5. summarize behavior changes and known limitations
