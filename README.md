# TRELLIS Asset Pipeline Skill

A Codex-oriented local pipeline for turning a short asset request into a game-ready 3D asset using image generation, ComfyUI/TRELLIS, and Blender.

> **Status:** early implementation. Repo-scoped Codex skill discovery, local configuration, environment diagnostics, and ComfyUI health-check/auto-start are implemented. Image generation, TRELLIS submission, GLB retrieval, and Blender conversion are the next stages.

## Goal

The intended user experience is deliberately simple:

~~~text
generate supamon game asset bush
~~~

The finished pipeline should:

1. Interpret the requested asset and quality preset.
2. Generate a clean source image suitable for image-to-3D.
3. Ensure the local ComfyUI instance is running.
4. Submit a versioned TRELLIS workflow through the ComfyUI API.
5. Wait locally for completion without repeatedly invoking the LLM.
6. Retrieve the generated GLB.
7. Process and validate the asset in headless Blender.
8. Export a game-ready FBX and report useful asset statistics.

## Intended pipeline

~~~text
Codex / agent
    |
    v
asset-pipeline orchestration
    |
    +--> image generation
    |
    +--> ComfyUI API
    |       |
    |       v
    |    TRELLIS
    |       |
    |       v
    |      GLB
    |
    +--> Blender (headless)
            |
            +--> cleanup / validation
            +--> optional optimization
            |
            v
           FBX
~~~

Long-running ComfyUI work belongs inside the local orchestration layer. The model should receive a compact result when the job finishes rather than being asked to check progress repeatedly.

## Repository layout

~~~text
trellis-asset-pipeline-skill/
├── .codex/
│   └── skills/
│       └── trellis-asset-pipeline/
│           ├── SKILL.md
│           └── references/
│               └── workflows.md
├── src/
│   └── trellis_pipeline/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── comfy.py
│       ├── config.py
│       └── doctor.py
├── workflows/
├── blender/
├── config/
├── benchmarks/
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── AGENTS.md
└── README.md
~~~

## Local setup

Clone the repository and create your local configuration:

~~~powershell
git clone https://github.com/hkcmoris/trellis-asset-pipeline-skill.git
cd trellis-asset-pipeline-skill

Copy-Item .env.example .env
~~~

Edit .env and set the paths for your machine.

Install the local CLI in editable mode:

~~~powershell
py -m pip install -e .
~~~

Run the environment check:

~~~powershell
trellis-pipeline doctor
~~~

Or without installing the console entry point:

~~~powershell
py -m trellis_pipeline doctor
~~~

If ComfyUI is not running and COMFYUI_START_BAT is configured:

~~~powershell
trellis-pipeline comfy ensure
~~~

You can also ask doctor to start it when necessary:

~~~powershell
trellis-pipeline doctor --start-comfyui
~~~

## Local configuration

Copy .env.example to .env. The real .env is ignored by Git.

The main settings are:

~~~env
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_ROOT=C:\AI\ComfyUI
COMFYUI_START_BAT=C:\AI\ComfyUI\Start ComfyUI FlashAttention.bat
COMFYUI_WORKFLOWS_DIR=C:\AI\ComfyUI\user\default\workflows
COMFYUI_INPUT_DIR=C:\AI\ComfyUI\input
COMFYUI_OUTPUT_DIR=C:\AI\ComfyUI\output

BLENDER_EXE=C:\Program Files\Blender Foundation\Blender\blender.exe
ASSET_OUTPUT_DIR=D:\AI\trellis-assets

COMFYUI_STARTUP_TIMEOUT_SECONDS=120
COMFYUI_HEALTH_TIMEOUT_SECONDS=3
~~~

Paths are examples only. Do not commit your machine-specific .env.

## Current CLI

### Doctor

~~~powershell
trellis-pipeline doctor
~~~

Checks:

- .env discovery
- ComfyUI URL and API availability
- ComfyUI root and startup batch file
- local ComfyUI workflow/input/output directories
- Blender executable and version
- NVIDIA GPU visibility through nvidia-smi
- asset output directory configuration

### ComfyUI status

~~~powershell
trellis-pipeline comfy status
~~~

### Ensure ComfyUI is running

~~~powershell
trellis-pipeline comfy ensure
~~~

This first checks the configured ComfyUI API. If the server is offline, it launches COMFYUI_START_BAT and waits locally until the API responds or the configured startup timeout expires.

Startup output is written to logs/comfyui-startup.log.

## Codex skill

The repo-scoped skill lives at:

~~~text
.codex/skills/trellis-asset-pipeline/SKILL.md
~~~

Open this repository as the Codex workspace. You can explicitly invoke it with:

~~~text
Use $trellis-asset-pipeline and run its environment check.
~~~

Its description is also written so asset-generation and TRELLIS workflow-optimization requests can trigger it naturally.

## Workflow policy

Your existing ComfyUI workflow directory is configured using COMFYUI_WORKFLOWS_DIR so Codex and the local tooling can inspect experiments already on your machine.

Known-good pipeline workflows should eventually be copied/exported into the repository under workflows/ and versioned in Git.

The pipeline should submit **API-format** ComfyUI workflows. UI workflow files are useful as source material but are not automatically equivalent to the JSON accepted by the /prompt API.

See .codex/skills/trellis-asset-pipeline/references/workflows.md.

## Planned generation modes

### Draft

Optimized for iteration:

- fast image-to-3D settings
- geometry-first generation
- minimal or no expensive texturing
- fast Blender export

### Balanced

The intended default:

- sensible geometry quality
- moderate texture quality
- basic cleanup and validation
- FBX export

### Quality

For selected keeper assets:

- higher-quality TRELLIS settings
- higher-quality textures where useful
- additional Blender cleanup/validation
- final FBX export and asset report

## Workflow optimization

A major goal is to tune TRELLIS workflows instead of blindly running expensive graphs.

Optimization should:

- establish an unchanged baseline
- record stage/node execution time where possible
- monitor GPU utilization and VRAM
- detect CPU/GPU offloading or stalls
- identify expensive or unnecessary graph stages
- change one important performance variable at a time
- compare output quality against runtime
- preserve known-good presets
- stop bad experiment branches early

The optimizer should eventually produce practical fast, balanced, and quality presets for the current machine.

## Repository policy

Do not commit:

- model weights or checkpoints
- GGUF files
- generated GLB/FBX/Blend assets
- generated textures and renders
- API keys or tokens
- machine-specific .env files
- private input images
- user-specific absolute paths

See .gitignore and AGENTS.md for project rules.

## License

See LICENSE.
