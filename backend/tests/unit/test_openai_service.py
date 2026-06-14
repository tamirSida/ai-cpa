import openai, pytest, httpx
from pydantic import ValidationError
from app.services.openai_service import OpenAICommandParser, get_command_parser
from app.schemas.ai_commands import ParsedUserCommand, ParserFailure

class _FakeUsage:
    def __init__(self, input_tokens=123, output_tokens=45):
        self.input_tokens, self.output_tokens = input_tokens, output_tokens

class _FakeResponses:
    def __init__(self, exc=None, parsed="unset", usage="unset"):
        self.exc, self.parsed = exc, parsed
        self.usage = _FakeUsage() if usage == "unset" else usage
    def parse(self, **kwargs):
        if self.exc: raise self.exc
        return type("R", (), {"output_parsed": self.parsed, "usage": self.usage})()
class _FakeClient:
    def __init__(self, exc=None, parsed="unset", usage="unset"):
        self.responses = _FakeResponses(exc, parsed, usage)

def _parser(exc=None, parsed="unset", usage="unset"):
    p = OpenAICommandParser(); p._client = _FakeClient(exc, parsed, usage); return p

def test_timeout_maps_to_failure():
    r, usage, model = _parser(exc=openai.APITimeoutError(request=httpx.Request("POST", "https://x"))).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "timeout"
    assert usage is None and isinstance(model, str)

def test_refusal_when_output_parsed_none():
    r, usage, model = _parser(parsed=None).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "refusal"
    assert usage is None and isinstance(model, str)

def test_success_normalizes_scalar_defaults():
    cmd = ParsedUserCommand(intent="UNKNOWN")
    r, usage, model = _parser(parsed=cmd).parse_user_command({}, "hi")
    assert r.missing_fields == [] and r.requires_confirmation is True and r.language == "unknown"

def test_parse_user_command_returns_usage_and_model():
    cmd = ParsedUserCommand(intent="UNKNOWN")
    fake_usage = _FakeUsage(input_tokens=200, output_tokens=50)
    r, usage, model = _parser(parsed=cmd, usage=fake_usage).parse_user_command({}, "hi")
    assert r is cmd
    assert usage is fake_usage
    assert usage.input_tokens == 200 and usage.output_tokens == 50
    assert isinstance(model, str) and model

def test_get_command_parser_is_cached_and_lazy():
    assert get_command_parser() is get_command_parser()
    assert get_command_parser()._client is None  # no OpenAI() constructed at import/instantiation

def test_rate_limit_maps_to_failure():
    exc = openai.RateLimitError(
        message="rate",
        response=httpx.Response(429, request=httpx.Request("POST", "https://x")),
        body=None,
    )
    r, usage, model = _parser(exc=exc).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "rate_limit"
    assert usage is None and isinstance(model, str)

def test_api_status_error_maps_to_api_error():
    # Use a plain 400 status — not a RateLimitError (which is 429) — to test the
    # APIStatusError branch independently. RateLimitError is caught first in _call.
    exc = openai.APIStatusError(
        message="bad",
        response=httpx.Response(400, request=httpx.Request("POST", "https://x")),
        body=None,
    )
    r, usage, model = _parser(exc=exc).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "api_error"
    assert usage is None and isinstance(model, str)

def test_length_finish_reason_maps_to_length():
    class _Len(openai.LengthFinishReasonError):
        def __init__(self): pass

    r, usage, model = _parser(exc=_Len()).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "length"
    assert usage is None and isinstance(model, str)

def test_connection_error_maps_to_api_error():
    r, usage, model = _parser(exc=openai.APIConnectionError(request=httpx.Request("POST", "https://x"))).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "api_error"
    assert usage is None and isinstance(model, str)
