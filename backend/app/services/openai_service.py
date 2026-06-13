import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol, Union
import openai
from openai import OpenAI
from pydantic import ValidationError
from app.core.config import get_settings
from app.schemas.ai_commands import ExpenseExtraction, ParsedUserCommand, ParserFailure

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

class CommandParser(Protocol):
    def parse_user_command(self, context: dict, message: str) -> Union[ParsedUserCommand, ParserFailure]: ...
    def extract_expense(self, image_url: str) -> Union[ExpenseExtraction, ParserFailure]: ...

def _normalize(cmd: ParsedUserCommand) -> ParsedUserCommand:
    # server-side scalar defaults (strict schema forced Optional on the wire)
    cmd.missing_fields = cmd.missing_fields or []
    cmd.confidence = 0.0 if cmd.confidence is None else cmd.confidence
    cmd.language = cmd.language or "unknown"
    cmd.requires_confirmation = True if cmd.requires_confirmation is None else cmd.requires_confirmation
    cmd.resolved_from_context = bool(cmd.resolved_from_context)
    return cmd

class OpenAICommandParser:
    def __init__(self):
        self._client = None  # NEVER construct OpenAI() at import/instantiation time
        self._command_prompt = (_PROMPTS / "command_parser.txt").read_text(encoding="utf-8")
        self._expense_prompt = (_PROMPTS / "expense_extractor.txt").read_text(encoding="utf-8")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            s = get_settings()
            self._client = OpenAI(api_key=s.openai_api_key, timeout=20.0, max_retries=2)
        return self._client

    def _call(self, model: str, input_items: list, text_format):
        try:
            response = self.client.responses.parse(model=model, input=input_items, text_format=text_format)
        except openai.LengthFinishReasonError as e: return ParserFailure(reason="length", detail=str(e))
        except openai.APITimeoutError as e: return ParserFailure(reason="timeout", detail=str(e))
        except openai.RateLimitError as e: return ParserFailure(reason="rate_limit", detail=str(e))
        except openai.APIStatusError as e: return ParserFailure(reason="api_error", detail=f"status={e.status_code}")
        except openai.APIConnectionError as e: return ParserFailure(reason="api_error", detail=str(e))  # non-timeout network failure (timeouts caught above)
        except ValidationError as e: return ParserFailure(reason="validation_error", detail=str(e)[:500])
        if response.output_parsed is None:
            return ParserFailure(reason="refusal", detail="model refused or returned no parsed output")
        return response.output_parsed

    def parse_user_command(self, context: dict, message: str):
        s = get_settings()
        user_text = json.dumps({"context": context, "message": message}, ensure_ascii=False)
        result = self._call(s.openai_command_model,
            [{"role": "system", "content": self._command_prompt},
             {"role": "user", "content": [{"type": "input_text", "text": user_text}]}],
            ParsedUserCommand)
        return _normalize(result) if isinstance(result, ParsedUserCommand) else result

    def extract_expense(self, image_url: str):
        s = get_settings()
        return self._call(s.openai_vision_model,
            [{"role": "system", "content": self._expense_prompt},
             {"role": "user", "content": [
                 {"type": "input_image", "image_url": image_url},  # plain string per Responses API
                 {"type": "input_text", "text": "Extract the expense from this image."}]}],
            ExpenseExtraction)

@lru_cache
def get_command_parser() -> CommandParser:
    return OpenAICommandParser()
