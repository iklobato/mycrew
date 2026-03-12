"""Flow checkpoint persistence in .code_pipeline/checkpoint.json."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _task_hash(task: str) -> str:
    """Stable hash for checkpoint key."""
    if task is not None:
        task_bytes = task.encode()
    else:
        task_bytes = "".encode()
    return hashlib.sha256(task_bytes).hexdigest()[:16]


class CheckpointStore:
    """Manages flow checkpoint persistence in .code_pipeline/checkpoint.json."""

    def __init__(self, repo_path: str) -> None:
        """Initialize with absolute repo path."""
        self._repo_path = os.path.abspath(repo_path)

    def _path(self) -> Path:
        """Path to checkpoint registry in repo."""
        return Path(self._repo_path) / ".code_pipeline" / "checkpoint.json"

    def _key(self, task: str) -> str:
        """Storage key for (repo_path, task)."""
        return f"{self._repo_path}|{_task_hash(task)}"

    def load(self, task: str) -> str | None:
        """Load flow_id for task. Returns None if not found."""
        path = self._path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            entry = data.get(self._key(task))
            if entry and isinstance(entry, dict):
                return entry.get("flow_id")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Checkpoint load failed: %s", e)
        return None

    def save(self, task: str, flow_id: str) -> None:
        """Save flow_id for task."""
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        data[self._key(task)] = {
            "flow_id": flow_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(data, indent=2))
