import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.sync_targets import load_sync_targets


class SyncTargetsTests(unittest.TestCase):
    def test_load_targets_from_json_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "sync_targets.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "targets": [
                            {
                                "id": "research",
                                "local_dir": "/Users/molly/Library/Mobile\\ Documents/research",
                                "feishu_folder_token": "fld_research",
                            },
                            {
                                "id": "work",
                                "local_dir": "/Users/molly/Library/Mobile Documents/work",
                                "feishu_folder_token": "fld_work",
                            },
                        ]
                    },
                    f,
                )

            targets = load_sync_targets(config_path=config_path)

            self.assertEqual(["research", "work"], [target.id for target in targets])
            self.assertEqual(
                "/Users/molly/Library/Mobile Documents/research",
                targets[0].local_dir,
            )
            self.assertEqual("fld_work", targets[1].feishu_folder_token)

    def test_duplicate_target_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "sync_targets.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "targets": [
                            {
                                "id": "notes",
                                "local_dir": "/tmp/a",
                                "feishu_folder_token": "fld_a",
                            },
                            {
                                "id": "notes",
                                "local_dir": "/tmp/b",
                                "feishu_folder_token": "fld_b",
                            },
                        ]
                    },
                    f,
                )

            with self.assertRaisesRegex(ValueError, "重复"):
                load_sync_targets(config_path=config_path)

    def test_missing_default_config_falls_back_to_legacy_env(self):
        env = {
            "LOCAL_MARKDOWN_DIR": "/tmp/legacy",
            "DEFAULT_PARENT_FOLDER_TOKEN": "fld_legacy",
        }
        with patch.dict(os.environ, env, clear=True):
            targets = load_sync_targets(config_path="missing-sync-targets.json")

        self.assertEqual(1, len(targets))
        self.assertEqual("default", targets[0].id)
        self.assertEqual("/tmp/legacy", targets[0].local_dir)
        self.assertEqual("fld_legacy", targets[0].feishu_folder_token)

    def test_explicit_missing_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "missing.json")

            with self.assertRaises(FileNotFoundError):
                load_sync_targets(config_path=config_path, explicit=True)


if __name__ == "__main__":
    unittest.main()
