# TRELLIS Asset Pipeline Skill

A Codex-oriented local pipeline for turning a short asset request into a game-ready 3D asset using image generation, ComfyUI/TRELLIS, and Blender.

> **Status:** early implementation. Repo-scoped Codex skill discovery, local configuration, environment diagnostics, ComfyUI health-check/auto-start, read-only workflow discovery/inspection, and guarded workflow cloning into the user workflow folder are implemented. Image generation, TRELLIS submission, GLB retrieval, and Blender conversion are the next stages.

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

## Local setup

~~~powershell
git clone https://github.com/hkcmoris/trellis-asset-pipeline-skill.git
cd trellis-asset-pipeline-skill

Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools
python -m pip install -e .
~~~

Edit .env and set the paths for your machine.

Run diagnostics:

~~~powershell
trellis-pipeline doctor
~~~

Ensure ComfyUI is running:

~~~powershell
trellis-pipeline comfy ensure
~~~

## Use the skill from any Codex workspace

The pipeline repository can stay separate from the game project. To make the skill available while Codex is opened on Supamon or any other workspace, run this once from the pipeline repository:

~~~powershell
.\scripts\install-global-skill.ps1
~~~

The installer:

- creates a junction at ~/.codex/skills/trellis-asset-pipeline pointing to this repo skill
- sets the user environment variable TRELLIS_PIPELINE_ROOT to this repository
- checks whether .venv\Scripts\python.exe can import trellis_pipeline
- refuses to replace an unrelated existing global skill directory

Restart Codex after running the installer so the new user environment variable is inherited.

From any workspace, the reliable pipeline invocation is:

~~~powershell
& "$env:TRELLIS_PIPELINE_ROOT\.venv\Scripts\python.exe" -m trellis_pipeline doctor
~~~

The skill uses the same pattern for all pipeline commands, so the active workspace does not need its own Python environment or .env. The machine-specific .env remains in the TRELLIS pipeline repository.

## Local configuration

The important workflow-related settings are:

~~~env
TRELLIS_EXAMPLE_WORKFLOWS_DIR=C:\AI\ComfyUI\custom_nodes\ComfyUI-Trellis2-GGUF\example_workflows
COMFYUI_WORKFLOWS_DIR=C:\AI\ComfyUI\user\default\workflows
~~~

These have intentionally different roles:

- **TRELLIS examples** are read-only reference workflows shipped with the custom node.
- **ComfyUI workflows** are your own saved/experimental graphs.
- **repo workflows/** are known-good pipeline workflows that are safe to version and optimize.

The real .env is ignored by Git.

## Current CLI

### Environment and ComfyUI

~~~powershell
trellis-pipeline doctor
trellis-pipeline doctor --start-comfyui
trellis-pipeline comfy status
trellis-pipeline comfy ensure
trellis-pipeline comfy start
~~~

### Quiet execution for long jobs

Until the native `trellis-pipeline generate` worker is implemented, run any long TRELLIS/ComfyUI/Blender command through:

~~~powershell
trellis-pipeline quiet-run --log logs\asset-job.log -- <command> <args...>
~~~

The child process may produce thousands of progress lines; they are written only to the local log. The CLI blocks and prints a compact result only after the process exits. This prevents Codex from waking up to narrate sampler steps such as "quarter complete" or repeatedly polling ComfyUI.

On failure, the final log tail is shown after the child has stopped.

### Workflow discovery

List all three workflow sources:

~~~powershell
trellis-pipeline workflows list
~~~

Limit to one source:

~~~powershell
trellis-pipeline workflows list --source examples
trellis-pipeline workflows list --source user
trellis-pipeline workflows list --source repo
~~~

Inspect by filename, stem, or relative path:

~~~powershell
trellis-pipeline workflows inspect my-tree-workflow
~~~

If the name exists in more than one source, make it explicit:

~~~powershell
trellis-pipeline workflows inspect my-tree-workflow --source user
~~~

To print every node:

~~~powershell
trellis-pipeline workflows inspect my-tree-workflow --source user --all-nodes
~~~

Inspection is read-only. It currently:

- detects standard ComfyUI UI vs API workflow JSON
- counts node classes
- surfaces TRELLIS/performance-relevant nodes by name
- prints scalar API inputs
- prints positional widget values for UI workflows without guessing their parameter names

UI workflow widget values are positional. For reliable parameter-name mutation and API execution, export or convert the graph to API format first.

## Codex skill

The repo-scoped skill lives at:

~~~text
.codex/skills/trellis-asset-pipeline/SKILL.md
~~~

Open this repository as the Codex workspace. You can explicitly invoke it with:

~~~text
Use $trellis-asset-pipeline and inspect my TRELLIS workflows.
~~~

## Workflow policy

Known-good pipeline workflows should eventually be copied/exported into workflows/ and versioned in Git.

The pipeline should submit **API-format** ComfyUI workflows. UI workflow files are useful as source material but are not automatically equivalent to JSON accepted by the /prompt API.

See .codex/skills/trellis-asset-pipeline/references/workflows.md.

## Planned generation modes

- **draft**: fastest useful geometry iteration; avoid expensive final-only work
- **balanced**: default game-asset generation
- **quality**: higher-cost keeper/final asset generation

## Workflow optimization

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

Do not commit model weights, GGUF/checkpoints, generated assets, API keys, machine-specific .env files, private input images, or user-specific absolute paths.

See .gitignore and AGENTS.md for project rules.

## License

See LICENSE.
