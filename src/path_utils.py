import os
import shlex


def normalize_config_path(path):
    if not path:
        return path

    normalized = path.strip().strip('"').strip("'")
    if "\\" in normalized:
        try:
            parts = shlex.split(normalized)
            if len(parts) == 1:
                normalized = parts[0]
        except ValueError:
            normalized = normalized.replace("\\ ", " ").replace("\\~", "~")

    return os.path.expandvars(os.path.expanduser(normalized))
