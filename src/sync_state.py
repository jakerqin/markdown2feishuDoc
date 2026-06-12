import hashlib
import json
import os
import tempfile


DEFAULT_SYNC_STATE_PATH = ".sync_state.json"
DEFAULT_TARGET_ID = "default"


class SyncState:
    def __init__(self, path=DEFAULT_SYNC_STATE_PATH):
        self.path = path
        self.targets = {}
        self.files = {}
        self.folders = {}
        self._load()
        self._sync_legacy_attrs()

    def _load(self):
        if not os.path.exists(self.path):
            self._ensure_target(DEFAULT_TARGET_ID)
            return

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        targets = data.get("targets")
        if isinstance(targets, dict):
            for target_id, target_data in targets.items():
                if not isinstance(target_data, dict):
                    continue
                self.targets[target_id] = {
                    "files": target_data.get("files", {}),
                    "folders": target_data.get("folders", {}),
                }
            self._ensure_target(DEFAULT_TARGET_ID)
            return

        self.targets[DEFAULT_TARGET_ID] = {
            "files": data.get("files", {}),
            "folders": data.get("folders", {}),
        }

    def _ensure_target(self, target_id):
        if not target_id:
            target_id = DEFAULT_TARGET_ID
        if target_id not in self.targets:
            self.targets[target_id] = {
                "files": {},
                "folders": {},
            }
        return self.targets[target_id]

    def _target_data(self, target_id=None):
        return self._ensure_target(target_id or DEFAULT_TARGET_ID)

    def _sync_legacy_attrs(self):
        default_target = self._target_data(DEFAULT_TARGET_ID)
        self.files = default_target["files"]
        self.folders = default_target["folders"]

    def get_entry(self, file_info, target_id=None):
        key = file_info["relative_path"]
        entry = self._target_data(target_id)["files"].get(key)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry
        return None

    def has_changed(self, file_info, target_id=None):
        entry = self.get_fingerprint(file_info, target_id=target_id)
        return entry != self._fingerprint(file_info["path"])

    def get_fingerprint(self, file_info, target_id=None):
        entry = self.get_entry(file_info, target_id=target_id)
        if not isinstance(entry, dict):
            return None
        return {
            "sha256": entry.get("sha256"),
            "size": entry.get("size"),
        }

    def get_doc_token(self, file_info, target_id=None):
        entry = self.get_entry(file_info, target_id=target_id)
        if not isinstance(entry, dict):
            return None
        return entry.get("doc_token")

    def get_folders(self, target_id=None):
        return self._target_data(target_id)["folders"]

    def get_folder_token(self, folder_path, target_id=None):
        key = self._normalize_folder_path(folder_path)
        return self._target_data(target_id)["folders"].get(key)

    def mark_folder(self, folder_path, folder_token, target_id=None):
        key = self._normalize_folder_path(folder_path)
        self._target_data(target_id)["folders"][key] = folder_token
        self._sync_legacy_attrs()

    @staticmethod
    def _normalize_folder_path(path):
        if not path or path == ".":
            return ""
        return os.path.normpath(path)

    def mark_uploaded(self, file_info, doc_token=None, target_id=None):
        key = file_info["relative_path"]
        entry = self._fingerprint(file_info["path"])
        if doc_token is not None:
            entry["doc_token"] = doc_token
        self._target_data(target_id)["files"][key] = entry
        self._sync_legacy_attrs()

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".sync_state.", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"version": 2, "targets": self.targets}, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _fingerprint(file_path):
        stat = os.stat(file_path)
        digest = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)

        return {
            "sha256": digest.hexdigest(),
            "size": stat.st_size,
        }
