# AGENTS.md

## Mission

Build a reliable, local-first asset-generation pipeline that lets an agent turn a short request such as:

```text
generate supamon game asset bush
```

into a usable 3D game asset through:

```text
image generation -> ComfyUI/TRELLIS -> GLB -> Blender -> FBX
```

The project should optimize for repeatability, debuggability, sensible GPU usage, and minimal unnecessary LLM interaction.

## Core principles

### 1. Prefer APIs over UI automation

Use the ComfyUI API and Blender command-line/Python interfaces whenever possible.

Computer-control/UI automation is a last resort, not the primary architecture.

### 2. Do not make the LLM babysit long jobs

TRELLIS generation can take minutes or longer.

The local orchestration layer should:

1. submit the job
2. wait using a WebSocket or local polling
3. collect the result
4. return one compact completion result to the agent

Do not implement a loop that repeatedly invokes Codex merely to ask whether a generation has finished.

### 3. Keep workflows versioned and reusable

Store known-good ComfyUI API workflow JSON under `workflows/`.

Do not dynamically rebuild an entire TRELLIS graph unless there is a strong reason. Prefer loading a known workflow and changing explicit inputs or parameters.

### 4. Optimize scientifically

When tuning a workflow:

- establish a baseline first
- record runtime
- record relevant GPU/VRAM information when available
- change one meaningful variable at a time
- preserve the input/seed when a fair visual comparison requires it
- record failures and OOM conditions
- stop obviously bad experiment branches early
- keep known-good configurations reproducible

The goal is not maximum theoretical quality. The goal is the best useful asset for the requested time/quality budget.

### 5. Separate generation quality levels

Design around at least these conceptual modes:

- `draft`
- `balanced`
- `quality`

Draft mode should avoid expensive final-only work when possible. For example, geometry exploration should not require full-resolution final texturing on every attempt.

### 6. Keep the public repository clean

This is a public repository.

Never commit:

- credentials, API keys, auth tokens, cookies, or secrets
- private URLs or network details
- user-specific absolute paths
- generated assets unless intentionally added as small public test fixtures
- model weights
- `.gguf`, `.safetensors`, checkpoints, or similar large model files
- private source images
- machine-specific configuration

Use environment variables or ignored local configuration files for machine-specific values.

## Repository map

```text
skill/       Codex skill definition and supporting skill resources
workflows/   Versioned ComfyUI/TRELLIS workflow templates
src/         Pipeline orchestration, ComfyUI integration, image generation, optimization
blender/     Headless Blender scripts for import, cleanup, inspection, and export
config/      Public/example configuration only
benchmarks/  Reproducible benchmark definitions and small textual results
tests/       Automated tests
```

## Implementation guidance

### Configuration

Do not hard-code installation paths.

Values such as these must be configurable:

- ComfyUI base URL
- ComfyUI installation/output paths
- Blender executable path
- output directory
- workflow selection
- image-generation provider/model
- GPU-specific performance presets

Default ComfyUI development URL may be `http://127.0.0.1:8188`, but code should allow it to be overridden.

### ComfyUI

Prefer a thin integration layer with responsibilities such as:

- validate server availability
- submit workflow
- upload/reference inputs
- wait for completion locally
- detect failures
- retrieve output metadata/files
- expose concise progress or final status to callers

Avoid leaking large raw ComfyUI event streams into agent context.

### TRELLIS workflows

Treat workflow JSON as source code.

When changing a workflow:

- keep diffs understandable
- avoid unrelated node reordering/churn when possible
- document performance-sensitive changes
- preserve a known-good workflow before major experimentation
- distinguish input parameters from topology changes

### Blender

Blender processing should be scriptable and headless.

Prefer deterministic scripts that can:

- import GLB
- inspect mesh/material/texture data
- perform explicitly requested cleanup
- validate transforms/normals
- optionally simplify/optimize
- export FBX
- return machine-readable statistics

Do not apply destructive mesh operations merely because they are available.

### Outputs

Generated user assets belong in ignored local output directories.

A successful pipeline result should eventually report useful facts such as:

- output GLB path
- output FBX path
- total generation time
- Blender processing time
- vertex/triangle count
- material count
- texture dimensions
- warnings/failures

Keep agent-facing results concise; detailed logs should remain available locally for debugging.

## Performance and benchmarking

The reference development machine may be an RTX 3060 12 GB, but implementation decisions should stay configurable for other GPUs.

When adding optimization logic, prioritize detecting:

- VRAM pressure
- CPU/GPU offloading
- unexpectedly low GPU utilization
- expensive remesh/reconstruction stages
- excessive sampling steps
- unnecessarily high intermediate resolutions
- repeated texture generation during geometry iteration

Benchmark data must clearly distinguish measured values from assumptions.

## Coding expectations

Until the implementation stack is finalized:

- prefer small modules with narrow responsibilities
- isolate external integrations behind clear interfaces
- keep orchestration logic testable without a live GPU where practical
- add type hints/types appropriate to the chosen language
- provide actionable error messages
- avoid swallowing exceptions
- avoid unnecessary dependencies
- keep Windows compatibility in mind

Do not introduce a framework solely for architecture aesthetics.

## Testing

Where practical, tests should cover:

- config parsing/validation
- workflow parameter mutation
- job-state handling
- output discovery
- timeout/failure handling
- Blender command construction
- benchmark result handling

GPU-heavy integration tests should be optional and clearly separated from fast unit tests.

## Documentation

Update `README.md` when:

- installation steps become real
- supported workflows change
- command syntax changes
- required dependencies change
- generated output behavior changes

Do not document a feature as implemented until the repository actually provides it.

## Change discipline

Before making a substantial change:

1. inspect the relevant existing files
2. preserve known-good workflows/configuration
3. make the smallest coherent change
4. test what can be tested
5. summarize behavior changes and known limitations

Favor working incremental automation over an oversized all-at-once pipeline.
