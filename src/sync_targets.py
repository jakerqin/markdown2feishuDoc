import json
import os
from dataclasses import dataclass

from src.path_utils import normalize_config_path


DEFAULT_SYNC_TARGETS_CONFIG = "sync_targets.json"
DEFAULT_TARGET_ID = "default"


@dataclass(frozen=True)
class SyncTarget:
    id: str
    local_dir: str
    feishu_folder_token: str


def load_sync_targets(config_path=None, explicit=False):
    env_config_path = os.getenv("SYNC_TARGETS_CONFIG")
    if config_path is None:
        config_path = env_config_path or DEFAULT_SYNC_TARGETS_CONFIG
        explicit = env_config_path is not None

    if config_path and os.path.exists(config_path):
        return _load_targets_file(config_path)

    if explicit:
        raise FileNotFoundError(config_path)

    return [_legacy_target_from_env()]


def _load_targets_file(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_targets = data.get("targets") if isinstance(data, dict) else None
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("sync_targets.json 必须包含非空 targets 列表")

    targets = []
    seen_ids = set()
    for raw_target in raw_targets:
        target = _target_from_dict(raw_target)
        if target.id in seen_ids:
            raise ValueError(f"重复的同步目标 id: {target.id}")
        seen_ids.add(target.id)
        targets.append(target)

    return targets


def _target_from_dict(raw_target):
    if not isinstance(raw_target, dict):
        raise ValueError("每个同步目标必须是对象")

    target_id = str(raw_target.get("id", "")).strip()
    local_dir = normalize_config_path(str(raw_target.get("local_dir", "")).strip())
    feishu_folder_token = str(raw_target.get("feishu_folder_token", "")).strip()

    if not target_id:
        raise ValueError("同步目标缺少 id")
    if not local_dir:
        raise ValueError(f"同步目标 {target_id} 缺少 local_dir")
    if not feishu_folder_token:
        raise ValueError(f"同步目标 {target_id} 缺少 feishu_folder_token")

    return SyncTarget(
        id=target_id,
        local_dir=local_dir,
        feishu_folder_token=feishu_folder_token,
    )


def _legacy_target_from_env():
    local_dir = normalize_config_path(os.getenv("LOCAL_MARKDOWN_DIR", ""))
    feishu_folder_token = os.getenv("DEFAULT_PARENT_FOLDER_TOKEN", "")

    if not local_dir or not feishu_folder_token:
        raise ValueError("请配置 sync_targets.json，或在 .env 中设置 LOCAL_MARKDOWN_DIR 和 DEFAULT_PARENT_FOLDER_TOKEN")

    return SyncTarget(
        id=DEFAULT_TARGET_ID,
        local_dir=local_dir,
        feishu_folder_token=feishu_folder_token,
    )
