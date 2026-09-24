---
name: trellis-asset-pipeline
description: Generate, prepare, benchmark, or optimize 3D game assets with a local image-generation -> ComfyUI/TRELLIS -> GLB -> Blender -> FBX pipeline. Use for requests such as "generate supamon game asset bush", image-to-3D asset creation, TRELLIS workflow tuning, ComfyUI pipeline troubleshooting, or game-asset conversion.
---

# TRELLIS Asset Pipeline

Use this skill for this repository's local 3D asset pipeline.

## First rule

Prefer the local pipeline and APIs over GUI automation.

Do not repeatedly invoke the model to watch a long TRELLIS render. Long waits must happen inside local tooling using WebSocket events or local polling, and the tool should return a compact completion result.

## Environment bootstrap

Before running pipeline work:

1. Run:

   ~~~powershell
   py -m trellis_pipeline doctor
   ~~~

2. If ComfyUI is offline, run:

   ~~~powershell
   py -m trellis_pipeline comfy ensure
   ~~~

3. If configuration is incomplete, inspect .env.example and tell the user exactly which local .env values are missing or invalid.

Do not commit .env.

## Machine-specific configuration

Read configuration from the repository's local .env.

Important settings:

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

Never replace these with guessed user-specific paths.

## Asset-generation intent

For a request shaped like:

~~~text
generate supamon game asset bush
~~~

the intended final pipeline is:

1. Interpret "bush" as the requested asset and "supamon" as project/style context.
2. Use the configured image-generation integration to create one clean image-to-3D reference:
   - isolated asset
   - full object visible
   - centered
   - strong silhouette
   - clean or neutral background
   - no text
   - no unnecessary scene clutter
   - game-art / Unreal-style presentation when requested
3. Ensure ComfyUI is available.
4. Select the requested TRELLIS preset. Default to balanced.
5. Submit the versioned API workflow to ComfyUI.
6. Wait locally for completion.
7. retrieve the resulting GLB.
8. Process the GLB with headless Blender.
9. Export FBX.
10. Inspect and report concise asset statistics and output paths.

## Current implementation boundary

At present, only environment diagnostics and ComfyUI health/startup are implemented.

Do not pretend image generation, TRELLIS submission, GLB retrieval, or Blender export already exist. When implementing them, update README.md and this section.

## Presets

Use these conceptual modes:

- draft: fastest useful geometry iteration; avoid expensive final-only work
- balanced: default game-asset generation
- quality: higher-cost keeper/final asset generation

If no mode is provided, use balanced.

## TRELLIS workflow policy

Read references/workflows.md before importing or modifying workflows.

Known-good pipeline workflows belong under the repository's workflows/ directory.

COMFYUI_WORKFLOWS_DIR points to the user's existing local ComfyUI workflows for discovery/migration. Do not overwrite them unless the user explicitly asks.

Use API-format workflow JSON for programmatic submission.

## Optimization requests

When the user asks to optimize a TRELLIS graph:

1. Preserve the original workflow.
2. Establish a measured baseline.
3. Use the same input and seed where a fair visual comparison requires it.
4. Measure overall runtime and, where possible, expensive stages/nodes.
5. Monitor NVIDIA utilization and VRAM.
6. Change one meaningful performance/quality variable at a time.
7. Record the result.
8. Stop branches that OOM, regress badly, or take disproportionately longer.
9. Preserve known-good variants.
10. Produce practical draft/balanced/quality recommendations rather than blindly maximizing every parameter.

Pay particular attention to:

- high intermediate geometry resolutions
- sampling step counts
- decoder/tiled-decoder choices
- remesh/reconstruction stages
- simplification stages
- repeated final-quality texture generation during geometry experiments
- GPU memory pressure and CPU/GPU offloading

## Blender policy

Use Blender headlessly through its Python/CLI interfaces.

Do not manually click through Blender unless no supported automation path exists.

Only apply destructive cleanup/decimation when it is explicitly part of the selected pipeline or justified by measured asset requirements.

## Output behavior

Generated assets and logs are local artifacts and should remain in ignored directories.

A finished full generation should eventually report:

- source image
- GLB path
- FBX path
- generation time
- Blender processing time
- triangle/vertex count
- material count
- texture information
- relevant warnings

Keep the agent-facing result compact.
