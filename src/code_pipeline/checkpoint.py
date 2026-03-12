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
        """Save flow_id for task with memory management."""
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())

                # Clean up old entries to prevent file from growing too large
                max_entries = 20  # Keep only last 20 tasks
                if len(data) > max_entries:
                    # Sort by timestamp and keep only most recent
                    entries_with_times = []
                    for key, entry in data.items():
                        if isinstance(entry, dict) and "updated_at" in entry:
                            entries_with_times.append((key, entry["updated_at"]))

                    if entries_with_times:
                        # Sort by timestamp (newest first)
                        entries_with_times.sort(key=lambda x: x[1], reverse=True)
                        # Keep only most recent entries
                        keys_to_keep = {
                            key for key, _ in entries_with_times[:max_entries]
                        }
                        data = {k: v for k, v in data.items() if k in keys_to_keep}
                        logger.info(
                            "Checkpoint cleanup: kept %d most recent entries", len(data)
                        )

            except (json.JSONDecodeError, OSError):
                pass

        data[self._key(task)] = {
            "flow_id": flow_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Write with minimal indentation to save space
        path.write_text(json.dumps(data, separators=(",", ":")))
