"""Unit tests for code_pipeline.models."""

import pytest

from code_pipeline.models import (
    CrewTemplate,
    DynamicPipeline,
    PipelineConfig,
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
