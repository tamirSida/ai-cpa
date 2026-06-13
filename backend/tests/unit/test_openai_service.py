import openai, pytest, httpx
from pydantic import ValidationError
from app.services.openai_service import OpenAICommandParser, get_command_parser
from app.schemas.ai_commands import ParsedUserCommand, ParserFailure

class _FakeResponses:
    def __init__(self, exc=None, parsed="unset"): self.exc, self.parsed = exc, parsed
    def parse(self, **kwargs):
        if self.exc: raise self.exc
        return type("R", (), {"output_parsed": self.parsed})()
class _FakeClient:
    def __init__(self, exc=None, parsed="unset"): self.responses = _FakeResponses(exc, parsed)

def _parser(exc=None, parsed="unset"):
    p = OpenAICommandParser(); p._client = _FakeClient(exc, parsed); return p

def test_timeout_maps_to_failure():
    r = _parser(exc=openai.APITimeoutError(request=httpx.Request("POST", "https://x"))).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "timeout"

def test_refusal_when_output_parsed_none():
    r = _parser(parsed=None).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "refusal"

def test_success_normalizes_scalar_defaults():
    cmd = ParsedUserCommand(intent="UNKNOWN")
    r = _parser(parsed=cmd).parse_user_command({}, "hi")
    assert r.missing_fields == [] and r.requires_confirmation is True and r.language == "unknown"

def test_get_command_parser_is_cached_and_lazy():
    assert get_command_parser() is get_command_parser()
    assert get_command_parser()._client is None  # no OpenAI() constructed at import/instantiation

def test_rate_limit_maps_to_failure():
    exc = openai.RateLimitError(
        message="rate",
        response=httpx.Response(429, request=httpx.Request("POST", "https://x")),
        body=None,
    )
    r = _parser(exc=exc).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "rate_limit"

def test_api_status_error_maps_to_api_error():
    # Use a plain 400 status — not a RateLimitError (which is 429) — to test the
    # APIStatusError branch independently. RateLimitError is caught first in _call.
    exc = openai.APIStatusError(
        message="bad",
        response=httpx.Response(400, request=httpx.Request("POST", "https://x")),
        body=None,
    )
    r = _parser(exc=exc).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "api_error"

def test_length_finish_reason_maps_to_length():
    class _Len(openai.LengthFinishReasonError):
        def __init__(self): pass

    r = _parser(exc=_Len()).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "length"

def test_connection_error_maps_to_api_error():
    r = _parser(exc=openai.APIConnectionError(request=httpx.Request("POST", "https://x"))).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "api_error"
