# TRELLIS Asset Pipeline Skill

A Codex-oriented local pipeline for turning a short asset request into a game-ready 3D asset using image generation, ComfyUI/TRELLIS, and Blender.

> **Status:** early scaffold. The repository currently defines the intended architecture and project layout; the pipeline itself is not implemented yet.

## Goal

The intended user experience is deliberately simple:

```text
generate supamon game asset bush
```

The pipeline should eventually be able to:

1. Interpret the requested asset and generation preset.
2. Generate a clean source image suitable for image-to-3D.
3. Submit a saved workflow to TRELLIS through the ComfyUI API.
4. Wait for the generation locally without repeatedly invoking the LLM.
5. Retrieve the generated GLB.
6. Process and validate the asset in headless Blender.
7. Export a game-ready FBX and report useful asset statistics.

## Intended pipeline

```text
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
```

Long-running ComfyUI work should be monitored by the local orchestration layer (WebSocket or local polling). The model should receive a compact result when the job completes rather than being asked to check progress repeatedly.

## Design goals

- **Short natural-language commands** for common asset-generation tasks.
- **API-first automation** instead of GUI clicking.
- **Reusable ComfyUI workflows** rather than rebuilding graphs for every generation.
- **Draft, balanced, and quality presets** for different speed/quality targets.
- **Benchmark-driven workflow optimization**, especially for limited VRAM.
- **Headless Blender processing** for repeatable conversion and cleanup.
- **Hardware-aware but hardware-agnostic design**: development may target an RTX 3060 12 GB, but assumptions should remain configurable.
- **Local-first execution**: models, generated assets, and large binaries stay on the user's machine.

## Repository layout

```text
trellis-asset-pipeline-skill/
├── AGENTS.md
├── README.md
├── .gitignore
├── skill/          # Codex skill definition and skill resources
├── workflows/      # Versioned ComfyUI/TRELLIS workflow templates
├── src/            # Pipeline orchestration and integrations
├── blender/        # Headless Blender scripts
├── config/         # Example configuration; machine-specific config stays local
├── benchmarks/     # Benchmark definitions/results that are safe to version
└── tests/          # Automated tests
```

## Planned generation modes

### Draft

Optimized for iteration:

- fast image-to-3D settings
- geometry-first generation
- minimal or no expensive texturing
- fast Blender export

### Balanced

The default target for normal asset creation:

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

A major goal of this project is to tune TRELLIS workflows instead of blindly running expensive graphs.

Optimization should:

- record stage/node execution time where possible
- monitor GPU VRAM and utilization
- identify expensive or unnecessary graph stages
- change one important quality/performance variable at a time
- compare output quality against runtime
- preserve known-good presets
- stop bad experiment branches early

The optimizer should be able to produce practical presets such as **fast**, **balanced**, and **quality** for a given machine.

## Local configuration

Machine-specific values must not be committed. Examples include:

```env
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_DIR=C:\AI\ComfyUI
BLENDER_EXE=C:\Program Files\Blender Foundation\Blender\blender.exe
OUTPUT_DIR=D:\AI\generated-assets
```

A committed example configuration can be added once the implementation format is decided.

## Development target

The first implementation is expected to work well on:

- Windows
- NVIDIA GPU
- ComfyUI running locally
- TRELLIS image-to-3D workflow
- Blender with command-line/headless execution
- Codex or another agent capable of invoking the local tools

The architecture should not hard-code a particular username, installation path, GPU, model quantization, or ComfyUI node pack.

## Repository policy

Do not commit:

- model weights or checkpoints
- GGUF files
- generated GLB/FBX/Blend assets
- generated textures and renders
- API keys or tokens
- machine-specific configuration
- absolute user-specific paths

See [`.gitignore`](.gitignore) and [`AGENTS.md`](AGENTS.md) for the project rules.

## License

See [LICENSE](LICENSE).
