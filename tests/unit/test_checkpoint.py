"""Unit tests for code_pipeline.checkpoint."""

import json

from code_pipeline.checkpoint import CheckpointStore


def test_checkpoint_store_load_empty_path_returns_none(tmp_path):
    """load returns None when checkpoint file does not exist."""
    store = CheckpointStore(str(tmp_path))
    assert store.load("some task") is None


def test_checkpoint_store_load_missing_task_returns_none(tmp_path):
    """load returns None when task is not in checkpoint file."""
    checkpoint_dir = tmp_path / ".code_pipeline"
    checkpoint_dir.mkdir(parents=True)
    (tmp_path / ".code_pipeline" / "checkpoint.json").write_text("{}")
    store = CheckpointStore(str(tmp_path))
    assert store.load("other task") is None


def test_checkpoint_store_save_creates_file_and_dir(tmp_path):
    """save creates .code_pipeline/checkpoint.json and parent dirs."""
    store = CheckpointStore(str(tmp_path))
    store.save("Fix bug", "flow-123")
    path = tmp_path / ".code_pipeline" / "checkpoint.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert isinstance(data, dict)
    # Key format: abs_path|hash
    keys = list(data.keys())
    assert len(keys) == 1
    assert "|" in keys[0]
    entry = data[keys[0]]
    assert entry["flow_id"] == "flow-123"
    assert "updated_at" in entry


def test_checkpoint_store_save_and_load_roundtrip(tmp_path):
    """save then load returns same flow_id."""
    store = CheckpointStore(str(tmp_path))
    store.save("Fix login", "flow-abc")
    assert store.load("Fix login") == "flow-abc"


def test_checkpoint_store_load_preserves_other_entries(tmp_path):
    """Saving one task does not overwrite other task entries."""
    store = CheckpointStore(str(tmp_path))
    store.save("Task A", "flow-a")
    store.save("Task B", "flow-b")
    assert store.load("Task A") == "flow-a"
    assert store.load("Task B") == "flow-b"


def test_checkpoint_store_save_overwrites_same_task(tmp_path):
    """Saving same task twice overwrites with new flow_id."""
    store = CheckpointStore(str(tmp_path))
    store.save("Task X", "flow-1")
    store.save("Task X", "flow-2")
    assert store.load("Task X") == "flow-2"


def test_checkpoint_store_load_invalid_json_returns_none(tmp_path):
    """load returns None when checkpoint file has invalid JSON."""
    checkpoint_dir = tmp_path / ".code_pipeline"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "checkpoint.json").write_text("not valid json {")
    store = CheckpointStore(str(tmp_path))
    assert store.load("any task") is None


def test_checkpoint_store_load_malformed_entry_returns_none(tmp_path):
    """load returns None when entry exists but has no flow_id."""
    store = CheckpointStore(str(tmp_path))
    store.save("task", "flow-1")
    path = tmp_path / ".code_pipeline" / "checkpoint.json"
    data = json.loads(path.read_text())
    keys = list(data.keys())
    data[keys[0]] = {"updated_at": "2020-01-01"}  # no flow_id
    path.write_text(json.dumps(data, indent=2))
    assert store.load("task") is None


def test_checkpoint_store_save_overwrites_invalid_existing_json(tmp_path):
    """save overwrites existing invalid JSON file with valid data."""
    checkpoint_dir = tmp_path / ".code_pipeline"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "checkpoint.json").write_text("not valid json {{{")
    store = CheckpointStore(str(tmp_path))
    store.save("task", "flow-new")
    assert store.load("task") == "flow-new"


def test_checkpoint_store_different_tasks_different_keys(tmp_path):
    """Different tasks produce different storage keys."""
    store = CheckpointStore(str(tmp_path))
    store.save("Task A", "flow-a")
    store.save("Task B", "flow-b")
    path = tmp_path / ".code_pipeline" / "checkpoint.json"
    data = json.loads(path.read_text())
    keys = list(data.keys())
    assert len(keys) == 2
    assert all("|" in k for k in keys)
