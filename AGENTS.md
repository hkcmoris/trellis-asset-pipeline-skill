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

The local orchestration layer should:

1. submit the job
2. wait using a WebSocket or local polling
3. collect the result
4. return one compact completion result to the agent

Do not implement a loop that repeatedly invokes Codex to ask whether generation has finished.

### 3. Keep machine configuration local

The public repository must never contain machine-specific paths or secrets.

Local values belong in .env, which is ignored by Git.

.env.example documents supported settings.

### 4. Keep workflows versioned and reusable

Known-good ComfyUI API workflow JSON belongs under workflows/.

COMFYUI_WORKFLOWS_DIR can point to the user's existing ComfyUI workflow directory for discovery and migration, but do not modify those workflows unless explicitly asked.

Do not dynamically rebuild an entire TRELLIS graph unless there is a strong reason. Prefer loading a known workflow and changing explicit inputs or parameters.

### 5. Optimize scientifically

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

### 6. Separate generation quality levels

Design around:

- draft
- balanced
- quality

Draft mode should avoid expensive final-only work. Geometry exploration should not require full-resolution final texturing on every attempt.

### 7. Keep the public repository clean

Never commit:

- credentials, API keys, auth tokens, cookies, or secrets
- private URLs or network details
- user-specific absolute paths
- generated assets unless intentionally added as small public test fixtures
- model weights
- GGUF, Safetensors, checkpoints, or similar model files
- private source images
- machine-specific configuration

## Repository map

~~~text
.codex/skills/trellis-asset-pipeline/
    Repo-scoped Codex skill and references

workflows/
    Versioned ComfyUI/TRELLIS API workflow templates

src/trellis_pipeline/
    Pipeline CLI, configuration, ComfyUI integration, and future orchestration

blender/
    Future headless Blender scripts

config/
    Public/example configuration only

benchmarks/
    Reproducible benchmark definitions and small textual results

tests/
    Automated tests
~~~

## Local commands

Install editable:

~~~powershell
py -m pip install -e .
~~~

Run diagnostics:

~~~powershell
trellis-pipeline doctor
~~~

Check ComfyUI:

~~~powershell
trellis-pipeline comfy status
~~~

Ensure ComfyUI is running:

~~~powershell
trellis-pipeline comfy ensure
~~~

When developing commands, preserve equivalent support for:

~~~powershell
py -m trellis_pipeline ...
~~~

## Configuration

Do not hard-code installation paths.

Supported environment variables currently include:

- COMFYUI_URL
- COMFYUI_ROOT
- COMFYUI_START_BAT
- COMFYUI_WORKFLOWS_DIR
- COMFYUI_INPUT_DIR
- COMFYUI_OUTPUT_DIR
- BLENDER_EXE
- ASSET_OUTPUT_DIR
- COMFYUI_STARTUP_TIMEOUT_SECONDS
- COMFYUI_HEALTH_TIMEOUT_SECONDS
- NVIDIA_SMI_EXE

Default ComfyUI development URL is http://127.0.0.1:8188 but must remain overridable.

## ComfyUI integration

Keep the integration layer narrow.

Responsibilities should include:

- validate server availability
- start the configured local instance when requested
- submit workflow
- upload/reference inputs
- wait for completion locally
- detect failures
- retrieve output metadata/files
- expose concise final status to callers

Avoid leaking raw high-volume ComfyUI event streams into agent context.

The current health check uses /system_stats.

Startup must first check whether the API is already available. Do not launch duplicate ComfyUI instances from ensure behavior.

## TRELLIS workflows

Treat workflow JSON as source code.

When changing a workflow:

- keep diffs understandable
- avoid unrelated node reordering/churn
- document performance-sensitive changes
- preserve a known-good workflow before major experiments
- distinguish parameter changes from graph-topology changes

The pipeline should eventually submit API-format workflow JSON to ComfyUI.

## Blender

Blender processing should be deterministic, scriptable, and headless.

Future scripts should be able to:

- import GLB
- inspect mesh/material/texture data
- perform explicitly requested cleanup
- validate transforms and normals
- optionally simplify/optimize
- export FBX
- return machine-readable statistics

Do not apply destructive mesh operations merely because they are available.

## Outputs

Generated user assets belong in ignored local output directories.

A successful full pipeline should eventually report:

- source image path
- output GLB path
- output FBX path
- total generation time
- Blender processing time
- vertex/triangle count
- material count
- texture dimensions
- warnings/failures

Keep agent-facing results concise. Detailed logs remain local.

## Performance and benchmarking

The initial reference machine may be an RTX 3060 12 GB, but implementation decisions must remain configurable for other hardware.

Optimization should prioritize detecting:

- VRAM pressure
- CPU/GPU offloading
- unexpectedly low GPU utilization
- expensive remesh/reconstruction stages
- excessive sampling steps
- unnecessarily high intermediate resolutions
- repeated texture generation during geometry iteration

Benchmark data must distinguish measured values from assumptions.

## Coding expectations

- Python 3.11+.
- Prefer the standard library unless a dependency materially improves the project.
- Keep modules small with narrow responsibilities.
- Isolate external integrations behind clear interfaces.
- Keep orchestration testable without a live GPU where practical.
- Use type hints.
- Provide actionable errors.
- Do not swallow exceptions.
- Keep Windows compatibility in mind.
- Do not introduce frameworks merely for architecture aesthetics.

## Testing

Where practical, tests should cover:

- config parsing/validation
- workflow parameter mutation
- job-state handling
- output discovery
- timeout/failure handling
- Blender command construction
- benchmark result handling

GPU-heavy integration tests should be optional and separated from fast unit tests.

## Documentation

Update README.md when:

- installation steps change
- supported workflows change
- command syntax changes
- required dependencies change
- generated output behavior changes

Do not document a feature as implemented until the repository actually provides it.

## Change discipline

Before a substantial change:

1. inspect relevant existing files
2. preserve known-good workflows/configuration
3. make the smallest coherent change
4. test what can be tested
5. summarize behavior changes and known limitations

Favor working incremental automation over an oversized all-at-once pipeline.
