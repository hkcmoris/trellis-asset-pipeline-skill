from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from trellis_pipeline.config import Settings
from trellis_pipeline.workflows import WorkflowError, clone_workflow_to_user


def _settings(root: Path, examples: Path, user: Path) -> Settings:
    return Settings(
        repo_root=root,
        env_file=root / ".env",
        comfyui_url="http://127.0.0.1:8188",
        comfyui_root=None,
        comfyui_start_bat=None,
        trellis_example_workflows_dir=examples,
        comfyui_workflows_dir=user,
        comfyui_input_dir=None,
        comfyui_output_dir=None,
        blender_exe=None,
        asset_output_dir=None,
        comfyui_startup_timeout_seconds=120.0,
        comfyui_health_timeout_seconds=3.0,
        nvidia_smi_exe="nvidia-smi",
    )


class WorkflowCloneTests(unittest.TestCase):
    def test_clones_example_to_user_without_touching_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            examples = root / "examples"
            user = root / "user"
            examples.mkdir()

            source = examples / "LowPoly.json"
            original = json.dumps({"nodes": [{"id": 1, "type": "TrellisNode"}]}, indent=2)
            source.write_text(original, encoding="utf-8")

            result = clone_workflow_to_user(
                _settings(root, examples, user),
                "LowPoly",
                source="examples",
                name="supamon-tree-balanced-v001",
            )

            self.assertEqual(result.destination, user / "supamon-tree-balanced-v001.json")
            self.assertEqual(result.format, "ui")
            self.assertFalse(result.overwritten)
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(result.destination.read_text(encoding="utf-8"), original)

    def test_refuses_existing_destination_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            examples = root / "examples"
            user = root / "user"
            examples.mkdir()
            user.mkdir()

            (examples / "Simple.json").write_text('{"nodes": []}', encoding="utf-8")
            destination = user / "tree.json"
            destination.write_text('{"keep": true}', encoding="utf-8")

            with self.assertRaises(WorkflowError):
                clone_workflow_to_user(
                    _settings(root, examples, user),
                    "Simple",
                    source="examples",
                    name="tree",
                )

            self.assertEqual(destination.read_text(encoding="utf-8"), '{"keep": true}')

    def test_explicit_overwrite_replaces_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            examples = root / "examples"
            user = root / "user"
            examples.mkdir()
            user.mkdir()

            (examples / "Simple.json").write_text('{"nodes": []}', encoding="utf-8")
            destination = user / "tree.json"
            destination.write_text('{"old": true}', encoding="utf-8")

            result = clone_workflow_to_user(
                _settings(root, examples, user),
                "Simple",
                source="examples",
                name="tree",
                overwrite=True,
            )

            self.assertTrue(result.overwritten)
            self.assertEqual(destination.read_text(encoding="utf-8"), '{"nodes": []}')

    def test_rejects_path_traversal_destination_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            examples = root / "examples"
            user = root / "user"
            examples.mkdir()

            (examples / "Simple.json").write_text('{"nodes": []}', encoding="utf-8")

            with self.assertRaises(WorkflowError):
                clone_workflow_to_user(
                    _settings(root, examples, user),
                    "Simple",
                    source="examples",
                    name="..\\escape",
                )

    def test_user_to_user_requires_new_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            examples = root / "examples"
            user = root / "user"
            examples.mkdir()
            user.mkdir()

            source = user / "tree-v001.json"
            source.write_text('{"nodes": []}', encoding="utf-8")

            with self.assertRaises(WorkflowError):
                clone_workflow_to_user(
                    _settings(root, examples, user),
                    "tree-v001",
                    source="user",
                    name="tree-v001",
                    overwrite=True,
                )

            result = clone_workflow_to_user(
                _settings(root, examples, user),
                "tree-v001",
                source="user",
                name="tree-v002",
            )
            self.assertEqual(result.destination, user / "tree-v002.json")


if __name__ == "__main__":
    unittest.main()
