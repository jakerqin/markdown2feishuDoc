import hashlib
import json
import os
import tempfile


DEFAULT_SYNC_STATE_PATH = ".sync_state.json"


class SyncState:
    def __init__(self, path=DEFAULT_SYNC_STATE_PATH):
        self.path = path
        self.files = {}
        self.folders = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.files = data.get("files", {})
        self.folders = data.get("folders", {})

    def get_entry(self, file_info):
        key = file_info["relative_path"]
        entry = self.files.get(key)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry
        return None

    def has_changed(self, file_info):
        entry = self.get_fingerprint(file_info)
        return entry != self._fingerprint(file_info["path"])

    def get_fingerprint(self, file_info):
        entry = self.get_entry(file_info)
        if not isinstance(entry, dict):
            return None
        return {
            "sha256": entry.get("sha256"),
            "size": entry.get("size"),
        }

    def get_doc_token(self, file_info):
        entry = self.get_entry(file_info)
        if not isinstance(entry, dict):
            return None
        return entry.get("doc_token")

    def get_folder_token(self, folder_path):
        key = self._normalize_folder_path(folder_path)
        return self.folders.get(key)

    def mark_folder(self, folder_path, folder_token):
        key = self._normalize_folder_path(folder_path)
        self.folders[key] = folder_token

    @staticmethod
    def _normalize_folder_path(path):
        if not path or path == ".":
            return ""
        return os.path.normpath(path)

    def mark_uploaded(self, file_info, doc_token=None):
        key = file_info["relative_path"]
        entry = self._fingerprint(file_info["path"])
        if doc_token is not None:
            entry["doc_token"] = doc_token
        self.files[key] = entry

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".sync_state.", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"files": self.files, "folders": self.folders}, f, ensure_ascii=False, indent=2, sort_keys=True)
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
