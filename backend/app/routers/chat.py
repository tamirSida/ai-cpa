from fastapi import APIRouter, Depends, Query
from app.core.auth import get_owned_business, require_active
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.user import User
from app.schemas.chat import (ChatHistoryResponse, ChatMessage, ChatMessageRequest,
                              ChatTurnResult, ExecutionResult)
from app.services import chat_service
from app.services.openai_service import CommandParser, get_command_parser

router = APIRouter(prefix="/businesses/{businessId}/chat", tags=["chat"])

@router.post("/message", response_model=ChatTurnResult)
def post_message(body: ChatMessageRequest, business: Business = Depends(get_owned_business),
                 user: User = Depends(require_active),  # cached per-request: reuses get_owned_business's user
                 db=Depends(get_db), parser: CommandParser = Depends(get_command_parser)):
    text = body.text.strip()
    if not text:
        api_error(422, "empty_message", "הודעה ריקה")
    return chat_service.handle_message(db, parser, business, user, body.thread_id, text)

@router.post("/actions/{action_id}/confirm", response_model=ExecutionResult)
def confirm(action_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return chat_service.confirm_action(db, None, business, action_id)

@router.post("/actions/{action_id}/cancel")
def cancel(action_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    # cancel_action validates (404/409) and returns the action's threadId — single read, no race.
    thread_id = chat_service.cancel_action(db, business.id, action_id)
    chat_service.save_message(db, business.id, thread_id, "assistant", "הפעולה בוטלה.", action_id=action_id)
    return {"status": "cancelled"}

@router.get("/messages", response_model=ChatHistoryResponse)
def list_messages(business: Business = Depends(get_owned_business), db=Depends(get_db),
                  thread_id: str = Query("main", alias="threadId"), limit: int = Query(50, ge=1, le=200)):
    # NOTE: _load_active_action below self-heals (expires stale / cancels duplicate actions),
    # so this GET can mutate Firestore — intentional, keeps thread state consistent on read.
    docs = db.collection("businesses").document(business.id).collection("chatThreads") \
             .document(thread_id).collection("messages") \
             .order_by("createdAt", direction="DESCENDING").limit(limit).stream()
    messages = [ChatMessage.model_validate({**d.to_dict(), "id": d.id}) for d in docs][::-1]
    active = chat_service._load_active_action(db, business.id, thread_id)
    return ChatHistoryResponse(messages=messages,
                               active_action=chat_service._action_view(*active) if active else None)
