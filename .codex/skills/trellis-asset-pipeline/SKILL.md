---
name: trellis-asset-pipeline
description: Generate, prepare, inspect, benchmark, or optimize 3D game assets with a local image-generation -> ComfyUI/TRELLIS -> GLB -> Blender -> FBX pipeline. Use for requests such as "generate supamon game asset bush", image-to-3D asset creation, TRELLIS workflow inspection/tuning, ComfyUI pipeline troubleshooting, or game-asset conversion.
---

# TRELLIS Asset Pipeline

Use this skill for this repository's local 3D asset pipeline.

## First rule

Prefer the local pipeline and APIs over GUI automation.

Do not repeatedly invoke the model to watch a long TRELLIS render. Long waits must happen inside local tooling using WebSocket events or local polling, and the tool should return a compact completion result.

## Long-running job policy — mandatory

A long TRELLIS, ComfyUI, Blender, baking, or conversion job must **not** become an agent-side progress loop.

After starting a long job:

- do not poll ComfyUI from separate agent turns
- do not repeatedly call queue/history/status endpoints to estimate completion
- do not read or tail the job log while it is still running
- do not narrate quarter/half/step percentages to the user
- do not emit "still working" updates based on sampler steps
- do not turn WebSocket progress events into model/tool responses

WebSocket or polling progress belongs entirely inside a local worker process. Intermediate events may be written to a local file for debugging, but they are not agent context.

Until the native pipeline generation worker exists, wrap any improvised long-running command with:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline quiet-run --log "$env:TRELLIS_PIPELINE_ROOT\logs\asset-job.log" -- <command> <args...>
~~~

`quiet-run` blocks until the child exits and redirects all child stdout/stderr to the local log. It prints only a final exit code, duration, and log path. On failure it may print the final log tail **after** the child has exited.

Once a long-running command has been launched through `quiet-run`, wait for that single tool invocation to return. Do not launch side-channel progress checks.

When the native `trellis-pipeline generate` command is implemented, it must follow the same final-only output contract.

## Pipeline location and invocation

This skill may be loaded globally while Codex is working in another repository.

Resolve the pipeline in this order:

1. If TRELLIS_PIPELINE_ROOT is set, use that repository.
2. Otherwise, if the current workspace is the TRELLIS asset pipeline repository, use the current repository.
3. Otherwise, tell the user to run scripts/install-global-skill.ps1 from the pipeline repository. Do not guess its location.

When TRELLIS_PIPELINE_ROOT is available, invoke every pipeline command through its own virtual environment:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline <args>
~~~

Do not depend on the current workspace Python, active virtual environment, .env, or PATH entry.

## Environment bootstrap

Before pipeline work, run:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline doctor
~~~

If ComfyUI is offline:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline comfy ensure
~~~

If configuration is incomplete, inspect .env.example and tell the user exactly which local .env values are missing or invalid.

Never commit .env.

## Machine-specific configuration

Important settings:

- COMFYUI_URL
- COMFYUI_ROOT
- COMFYUI_START_BAT
- TRELLIS_EXAMPLE_WORKFLOWS_DIR
- COMFYUI_WORKFLOWS_DIR
- COMFYUI_INPUT_DIR
- COMFYUI_OUTPUT_DIR
- BLENDER_EXE
- ASSET_OUTPUT_DIR

Never replace these with guessed user-specific paths.

## Workflow discovery

Before guessing about a local TRELLIS graph, inspect what is actually present:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline workflows list
~~~

Sources:

- examples: TRELLIS_EXAMPLE_WORKFLOWS_DIR, reference only
- user: COMFYUI_WORKFLOWS_DIR, user-owned experiments
- repo: workflows/, version-controlled known-good workflows

Inspect without modifying:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline workflows inspect <name>
~~~

Use --source examples|user|repo when needed. Use --all-nodes when the full graph summary is useful.

UI workflow widget values are positional. Do not guess names for widget positions. API workflows expose named scalar inputs and are preferred for programmatic mutation/execution.

## Asset-generation intent

For:

~~~text
generate supamon game asset bush
~~~

the intended final pipeline is:

1. Interpret bush as the requested asset and supamon as project/style context.
2. Generate one clean image-to-3D reference: isolated, fully visible, centered, strong silhouette, clean background, no text/clutter, game-art / Unreal-style presentation when requested.
3. Ensure ComfyUI is available.
4. Select the requested TRELLIS preset; default balanced.
5. Submit the versioned API workflow.
6. Wait locally for completion.
7. Retrieve GLB.
8. Process with headless Blender.
9. Export FBX.
10. Report concise asset statistics and output paths.

## Current implementation boundary

Implemented now:

- environment diagnostics
- ComfyUI health/startup
- workflow discovery
- read-only workflow inspection

Not implemented yet:

- image generation
- TRELLIS workflow submission
- job completion monitoring
- GLB retrieval
- Blender export
- automatic benchmark optimization

Do not pretend unimplemented stages already work.

## Optimization requests

When optimizing a TRELLIS graph:

1. Inspect the actual workflow first.
2. Preserve the original.
3. Establish a measured baseline.
4. Keep input and seed stable where appropriate.
5. Measure overall runtime and expensive stages/nodes.
6. Monitor NVIDIA utilization and VRAM.
7. Change one meaningful variable at a time.
8. Stop OOM/regressive branches.
9. Preserve known-good variants.
10. Produce practical draft/balanced/quality recommendations.

Pay particular attention to cascade, reconstruction/remesh/quad operations, high resolutions, sampling steps, decode choices, simplification, repeated texturing, memory pressure, and CPU/GPU offloading.

## Blender policy

Use Blender headlessly through Python/CLI. Do not manually click through Blender unless no supported automation path exists.

## Output behavior

Generated assets and logs are local artifacts and should remain in ignored directories. Keep agent-facing results compact.
