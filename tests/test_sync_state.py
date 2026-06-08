import os
import json
import tempfile
import unittest

from src.sync_state import SyncState


class SyncStateTests(unittest.TestCase):
    def test_changed_files_are_uploaded_once_then_skipped_until_content_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "state.json")
            md_path = os.path.join(tmpdir, "note.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# First\n")

            file_info = {"path": md_path, "relative_path": "note.md"}
            state = SyncState(state_path)

            self.assertTrue(state.has_changed(file_info))

            state.mark_uploaded(file_info)
            state.save()

            reloaded = SyncState(state_path)
            self.assertFalse(reloaded.has_changed(file_info))

            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# Changed\n")

            self.assertTrue(reloaded.has_changed(file_info))

    def test_mark_uploaded_stores_doc_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "state.json")
            md_path = os.path.join(tmpdir, "note.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("content")

            file_info = {"path": md_path, "relative_path": "note.md"}
            state = SyncState(state_path)
            state.mark_uploaded(file_info, doc_token="doc_123")
            state.save()

            reloaded = SyncState(state_path)
            self.assertEqual("doc_123", reloaded.get_doc_token(file_info))

    def test_load_old_state_without_doc_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "state.json")
            old_state = {
                "files": {
                    "note.md": {
                        "sha256": "hash",
                        "size": 6,
                    }
                }
            }
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(old_state, f, ensure_ascii=False)

            with open(os.path.join(tmpdir, "note.md"), "w", encoding="utf-8") as f:
                f.write("abc\n")

            state = SyncState(state_path)
            file_info = {"path": os.path.join(tmpdir, "note.md"), "relative_path": "note.md"}
            self.assertIsNone(state.get_doc_token(file_info))

    def test_mark_and_get_folder_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "state.json")
            state = SyncState(state_path)
            state.mark_folder("folder/a", "token-abc")
            state.save()

            reloaded = SyncState(state_path)
            self.assertEqual("token-abc", reloaded.get_folder_token("folder/a"))

    def test_mark_folder_path_normalization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = SyncState(os.path.join(tmpdir, "state.json"))
            state.mark_folder("", "root-token")
            state.mark_folder("./a/b", "nested-token")
            state.save()

            reloaded = SyncState(os.path.join(tmpdir, "state.json"))
            self.assertEqual("root-token", reloaded.get_folder_token("."))
            self.assertEqual("nested-token", reloaded.get_folder_token("a/b"))

    def test_load_old_state_with_no_folders_keeps_empty_map(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                f.write('{"files": {"a.md": {"sha256": "x", "size": 1}}}')

            state = SyncState(state_path)
            self.assertEqual({}, state.folders)


if __name__ == "__main__":
    unittest.main()
