# ComfyUI workflow handling

## Two kinds of workflow JSON

ComfyUI commonly exposes workflow data in two forms:

1. **UI workflow JSON**
   - designed to reconstruct the graph in the ComfyUI editor
   - contains editor/layout information
   - useful for human editing and as a migration source

2. **API-format workflow JSON**
   - node-id keyed prompt structure used for programmatic execution
   - suitable for submission to ComfyUI's /prompt API

The pipeline should version and execute API-format workflows.

Do not assume a UI workflow file can be posted directly to /prompt unchanged.

## Existing local workflows

COMFYUI_WORKFLOWS_DIR points at the user's existing ComfyUI workflow directory.

Use it to:

- discover workflows the user has already tested
- identify TRELLIS node choices and parameters
- compare experiments
- migrate a known-good workflow into this repository

Do not modify or delete local ComfyUI workflows unless the user explicitly asks.

## Repository workflows

Known-good reusable workflows belong under:

~~~text
workflows/
~~~

Suggested future naming:

~~~text
workflows/
├── trellis-draft.json
├── trellis-balanced.json
└── trellis-quality.json
~~~

Keep machine-specific paths out of workflow JSON whenever possible.

## Importing an experimental workflow

When moving a workflow from the user's ComfyUI setup into the repository:

1. preserve the original local file
2. identify whether it is UI or API format
3. export/convert to API format if necessary
4. remove machine-specific transient values where practical
5. place the reusable workflow under workflows/
6. commit it before major optimization experiments
7. record why it is considered known-good

## Optimization discipline

Treat workflow JSON as source code.

Avoid unrelated graph churn.

For controlled benchmarks:

- preserve the source image
- preserve the random seed where appropriate
- change one important parameter or graph choice at a time
- record runtime and VRAM behavior
- record output-quality observations
- retain the baseline for comparison
