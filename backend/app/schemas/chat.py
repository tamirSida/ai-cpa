from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class PendingAction(CamelModel):  # doc §5.6
    id: str; business_id: str; thread_id: str; type: str; status: str
    payload: dict[str, Any]; missing_fields: list[str]
    created_at: datetime; updated_at: datetime

class ChatMessage(CamelModel):    # doc §5.7
    id: str; business_id: str; thread_id: str; role: str; text: str
    parsed_intent: Optional[dict[str, Any]] = None
    action_id: Optional[str] = None; created_at: datetime

class ChatMessageRequest(CamelModel):
    text: str; thread_id: str = "main"

class ActionView(CamelModel):
    id: str; type: str; status: str
    payload: dict[str, Any]; missing_fields: list[str]

class ChatTurnResult(CamelModel):
    assistant_text: str; action: Optional[ActionView] = None; result: Optional[dict[str, Any]] = None

class ExecutionResult(CamelModel):
    assistant_text: str; action: Optional[ActionView] = None; result: Optional[dict[str, Any]] = None

class ChatHistoryResponse(CamelModel):
    messages: list[ChatMessage]; active_action: Optional[ActionView] = None
