"""
Event models for Dify events.

This module contains Pydantic models for Dify events. These models are used to
validate and process events from the Dify workflow engine.
"""

from typing import Dict, Any, Union, Literal
from pydantic import BaseModel

# Import content models
from .content_models import (
    NodeStartContent,
    NodeFinishContent,
    WorkflowFinishContent,
)

class BaseEvent(BaseModel):
    """Base class for all event types."""
    type: str
    content: Dict[str, Any]

class NodeStartEvent(BaseEvent):
    """Event triggered when a node starts processing."""
    type: Literal["node_start"] = "node_start"
    content: NodeStartContent

class NodeFinishEvent(BaseEvent):
    """Event triggered when a regular node finishes processing."""
    type: Literal["node_finish"] = "node_finish"
    content: NodeFinishContent

class IterationFinishEvent(BaseEvent):
    """Event triggered when an iteration node finishes processing."""
    type: Literal["iteration_finish"] = "iteration_finish"
    content: NodeFinishContent

class WorkflowFinishEvent(BaseEvent):
    """Event triggered when a workflow finishes."""
    type: Literal["workflow_finish"] = "workflow_finish"
    content: WorkflowFinishContent

# Union type for all Dify events
DifyEvent = Union[NodeStartEvent, NodeFinishEvent, IterationFinishEvent, WorkflowFinishEvent]
