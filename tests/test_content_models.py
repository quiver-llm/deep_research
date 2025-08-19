import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from event_management.event_models import (
    NodeStartEvent,
    NodeFinishEvent,
    IterationFinishEvent,
    WorkflowFinishEvent,
)
from event_management.content_models import (
    NodeStartContent,
    NodeFinishContent,
    WorkflowFinishContent,
    NodeType,
    NodeStatus,
)
from tests.event_data import (
    NODE_START_EVENT_JSON,
    NODE_FINISH_LLM_JSON,
    NODE_FINISH_IF_ELSE_JSON,
    NODE_FINISH_VARIABLE_AGGREGATOR_JSON,
    NODE_FINISH_TEMPLATE_TRANSFORM_JSON,
    ITERATION_FINISH_EVENT_JSON,
    WORKFLOW_FINISH_EVENT_JSON,
)


def _loads(s: str) -> dict:
    return json.loads(s)


def test_node_start_content_fields():
    data = _loads(NODE_START_EVENT_JSON)
    evt = NodeStartEvent.model_validate(data)

    assert isinstance(evt.content, NodeStartContent)
    c = evt.content

    assert c.id
    assert c.node_id
    assert c.node_type == NodeType.ANSWER
    assert c.title == "Answer"

    # created_at must be parsed to aware datetime
    assert isinstance(c.created_at, datetime)
    assert c.created_at.tzinfo == timezone.utc

    # optional fields should exist with defaults
    assert isinstance(c.extras, dict)
    # ensure known optional fields are present (may be None)
    assert hasattr(c, "predecessor_node_id")
    assert hasattr(c, "iteration_id")


def test_node_finish_llm_content_fields():
    data = _loads(NODE_FINISH_LLM_JSON)
    evt = NodeFinishEvent.model_validate(data)

    assert isinstance(evt.content, NodeFinishContent)
    c = evt.content

    assert c.node_type == NodeType.LLM
    # status enum
    assert c.status == NodeStatus.SUCCEEDED
    assert c.elapsed_time and c.elapsed_time > 0

    # timestamps
    assert isinstance(c.created_at, datetime)
    assert c.created_at.tzinfo == timezone.utc
    assert isinstance(c.finished_at, datetime)
    assert c.finished_at.tzinfo == timezone.utc


def test_node_start_optional_fields_missing_are_allowed():
    data = _loads(NODE_START_EVENT_JSON)
    # remove several optional fields
    for key in [
        "predecessor_node_id",
        "extras",
        "parallel_id",
        "parallel_start_node_id",
        "parent_parallel_id",
        "parent_parallel_start_node_id",
        "iteration_id",
        "loop_id",
        "parallel_run_id",
        "agent_strategy",
    ]:
        data["content"].pop(key, None)

    evt = NodeStartEvent.model_validate(data)
    c = evt.content
    # Extras should default to dict per model definition
    assert isinstance(c.extras, dict)
    # Missing fields should be present as attributes (possibly None)
    assert hasattr(c, "iteration_id")


def test_invalid_node_type_raises_validation_error_on_finish_event():
    data = _loads(NODE_FINISH_LLM_JSON)
    data["content"]["node_type"] = "not-a-valid-type"
    with pytest.raises(ValidationError):
        NodeFinishEvent.model_validate(data)


def test_invalid_status_raises_validation_error_on_finish_event():
    data = _loads(NODE_FINISH_LLM_JSON)
    data["content"]["status"] = "definitely-not-valid"
    with pytest.raises(ValidationError):
        NodeFinishEvent.model_validate(data)

@pytest.mark.parametrize(
    "event_json",
    [
        NODE_FINISH_IF_ELSE_JSON,
        NODE_FINISH_VARIABLE_AGGREGATOR_JSON,
        NODE_FINISH_TEMPLATE_TRANSFORM_JSON,
    ],
)
def test_node_finish_outputs_present(event_json):
    data = _loads(event_json)
    evt = NodeFinishEvent.model_validate(data)
    assert isinstance(evt.content, NodeFinishContent)
    c = evt.content
    assert isinstance(c.outputs, dict)


@pytest.mark.parametrize(
    "event_json,expected_node_type",
    [
        (NODE_FINISH_IF_ELSE_JSON, NodeType.IF_ELSE),
        (NODE_FINISH_VARIABLE_AGGREGATOR_JSON, NodeType.VARIABLE_AGGREGATOR),
        (NODE_FINISH_TEMPLATE_TRANSFORM_JSON, NodeType.TEMPLATE_TRANSFORM),
    ],
)
def test_various_node_finish_content_fields(event_json, expected_node_type):
    data = _loads(event_json)
    evt = NodeFinishEvent.model_validate(data)

    assert isinstance(evt.content, NodeFinishContent)
    c = evt.content

    assert c.node_type == expected_node_type
    assert c.status == NodeStatus.SUCCEEDED
    assert c.elapsed_time is not None

    # timestamps
    assert isinstance(c.created_at, datetime)
    assert c.created_at.tzinfo == timezone.utc
    assert isinstance(c.finished_at, datetime)
    assert c.finished_at.tzinfo == timezone.utc


def test_iteration_finish_content_fields():
    data = _loads(ITERATION_FINISH_EVENT_JSON)
    evt = IterationFinishEvent.model_validate(data)

    assert isinstance(evt.content, NodeFinishContent)
    c = evt.content

    assert c.node_type == NodeType.ITERATION
    assert c.status == NodeStatus.SUCCEEDED
    assert isinstance(c.total_tokens, int)
    assert c.total_tokens > 0

    # finished_at parsed
    assert isinstance(c.finished_at, datetime)
    assert c.finished_at.tzinfo == timezone.utc


def test_workflow_finish_content_fields():
    data = _loads(WORKFLOW_FINISH_EVENT_JSON)
    evt = WorkflowFinishEvent.model_validate(data)

    assert isinstance(evt.content, WorkflowFinishContent)
    c = evt.content

    assert c.status == "succeeded"
    assert isinstance(c.total_tokens, int)
    assert c.total_tokens > 0

    # created_at and finished_at parsed
    assert isinstance(c.created_at, datetime)
    assert c.created_at.tzinfo == timezone.utc
    assert isinstance(c.finished_at, datetime)
    assert c.finished_at.tzinfo == timezone.utc
