"""Unit tests for code_pipeline.models."""

import pytest

from code_pipeline.models import (
    BackwardCompatibility,
    CrewTemplate,
    DynamicPipeline,
    MigrationHelper,
    PipelineConfig,
    SimpleAuth,
    User,
)


def test_user_empty_id_raises():
    """User with empty id raises ValueError."""
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        User(id="")
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        User(id="   ")


def test_user_valid_creates():
    """User with valid id and api_keys creates successfully."""
    u = User(id="alice", api_keys={"github": "gh123"})
    assert u.id == "alice"
    assert u.api_keys == {"github": "gh123"}
    assert u.created_at is not None


def test_user_strips_id():
    """User id is stripped of whitespace."""
    u = User(id="  bob  ")
    assert u.id == "bob"


def test_user_default_api_keys():
    """User api_keys defaults to empty dict."""
    u = User(id="charlie")
    assert u.api_keys == {}


def test_pipeline_config_empty_name_raises():
    """PipelineConfig with empty name raises ValueError."""
    with pytest.raises(ValueError, match="Pipeline name cannot be empty"):
        PipelineConfig(name="")


def test_pipeline_config_valid_creates():
    """PipelineConfig with valid data creates successfully."""
    cfg = PipelineConfig(
        name="test-pipeline",
        description="A test",
        pipeline_settings={"branch": "main"},
    )
    assert cfg.name == "test-pipeline"
    assert cfg.description == "A test"
    assert cfg.pipeline_settings == {"branch": "main"}
    assert cfg.models == {}
    assert cfg.tools == {}


def test_crew_template_empty_id_raises():
    """CrewTemplate with empty id raises ValueError."""
    with pytest.raises(ValueError, match="Crew ID cannot be empty"):
        CrewTemplate(id="", name="X", agents_yaml="a: 1", tasks_yaml="b: 1")


def test_crew_template_empty_yaml_raises():
    """CrewTemplate with empty agents_yaml or tasks_yaml raises ValueError."""
    with pytest.raises(ValueError, match="YAML content cannot be empty"):
        CrewTemplate(
            id="crew1",
            name="Crew",
            agents_yaml="",
            tasks_yaml="x: 1",
        )
    with pytest.raises(ValueError, match="YAML content cannot be empty"):
        CrewTemplate(
            id="crew1",
            name="Crew",
            agents_yaml="a: 1",
            tasks_yaml="   ",
        )


def test_crew_template_normalizes_id():
    """CrewTemplate validates id to lowercase and replaces spaces."""
    t = CrewTemplate(
        id="My Crew Name",
        name="Crew",
        agents_yaml="a: 1",
        tasks_yaml="b: 1",
    )
    assert t.id == "my_crew_name"


def test_dynamic_pipeline_invalid_status_raises():
    """DynamicPipeline with invalid status raises ValueError."""
    with pytest.raises(ValueError, match="Status must be one of"):
        DynamicPipeline(
            id="p1",
            user_id="u1",
            status="invalid_status",
        )


def test_dynamic_pipeline_valid_statuses():
    """DynamicPipeline accepts valid statuses."""
    for status in ("pending", "running", "completed", "failed"):
        p = DynamicPipeline(id="p1", user_id="u1", status=status)
        assert p.status == status


def test_dynamic_pipeline_empty_id_raises():
    """DynamicPipeline with empty id raises ValueError."""
    with pytest.raises(ValueError, match="Pipeline ID cannot be empty"):
        DynamicPipeline(id="  ", user_id="u1")


def test_migration_helper_crew_template_from_yaml(tmp_path):
    """crew_template_from_yaml_files creates CrewTemplate from valid files."""
    agents = tmp_path / "agents.yaml"
    tasks = tmp_path / "tasks.yaml"
    agents.write_text("agents: []")
    tasks.write_text("tasks: []")

    t = MigrationHelper.crew_template_from_yaml_files(
        crew_id="explorer",
        name="Explorer",
        agents_yaml_path=str(agents),
        tasks_yaml_path=str(tasks),
    )
    assert t.id == "explorer"
    assert t.name == "Explorer"
    assert "agents: []" in t.agents_yaml
    assert "tasks: []" in t.tasks_yaml


def test_migration_helper_crew_template_invalid_yaml_raises(tmp_path):
    """crew_template_from_yaml_files with invalid YAML raises ValueError."""
    agents = tmp_path / "agents.yaml"
    tasks = tmp_path / "tasks.yaml"
    agents.write_text("invalid: [")
    tasks.write_text("tasks: []")

    with pytest.raises(ValueError, match="Invalid YAML"):
        MigrationHelper.crew_template_from_yaml_files(
            crew_id="x",
            name="X",
            agents_yaml_path=str(agents),
            tasks_yaml_path=str(tasks),
        )


def test_migration_helper_pipeline_config_from_yaml(tmp_path):
    """pipeline_config_from_yaml_file creates PipelineConfig."""
    config = tmp_path / "config.yaml"
    config.write_text("""
pipeline:
  branch: main
models: {}
tools: {}
""")
    cfg = MigrationHelper.pipeline_config_from_yaml_file(
        config_id="c1",
        name="Test",
        config_yaml_path=str(config),
    )
    assert cfg.name == "Test"
    assert cfg.pipeline_settings == {"branch": "main"}


def test_backward_compatibility_load_config_exists(tmp_path):
    """BackwardCompatibility.load_config returns parsed YAML when file exists."""
    config = tmp_path / "config.yaml"
    config.write_text("pipeline:\n  branch: dev\n")
    bc = BackwardCompatibility(default_config_path=str(config))
    data = bc.load_config()
    assert data["pipeline"]["branch"] == "dev"


def test_backward_compatibility_load_config_missing():
    """BackwardCompatibility.load_config returns empty dict when file missing."""
    bc = BackwardCompatibility(default_config_path="/nonexistent/config.yaml")
    assert bc.load_config() == {}


def test_backward_compatibility_get_crew_yaml_missing_raises(tmp_path):
    """get_crew_yaml raises FileNotFoundError when agents/tasks missing."""
    crew_dir = tmp_path / "crew"
    crew_dir.mkdir()
    (crew_dir / "config").mkdir()
    # No agents.yaml or tasks.yaml

    bc = BackwardCompatibility()
    with pytest.raises(FileNotFoundError, match="Missing YAML files"):
        bc.get_crew_yaml(str(crew_dir))


def test_backward_compatibility_get_crew_yaml_success(tmp_path):
    """get_crew_yaml returns agents and tasks content."""
    crew_dir = tmp_path / "crew"
    crew_dir.mkdir()
    config_dir = crew_dir / "config"
    config_dir.mkdir()
    (config_dir / "agents.yaml").write_text("a: 1")
    (config_dir / "tasks.yaml").write_text("t: 2")

    bc = BackwardCompatibility()
    agents, tasks = bc.get_crew_yaml(str(crew_dir))
    assert agents == "a: 1"
    assert tasks == "t: 2"


def test_simple_auth_create_user():
    """create_user returns User with api_keys."""
    u = SimpleAuth.create_user("user1", {"github": "token"})
    assert u.id == "user1"
    assert u.api_keys == {"github": "token"}


def test_simple_auth_authenticate_user_returns_none():
    """authenticate_user returns None (no DB implementation)."""
    assert SimpleAuth.authenticate_user("any_key") is None
