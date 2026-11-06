"""
Tests for the shared LLM request helper in AIProvider (`_call_llm` / `_call_llm_json`).

No real network traffic: `requests.post` is replaced with a fake that records the call.
"""
import json
import logging

import pytest
import requests

import app.services.ai as ai_module
from app.api.v1.health import check_health
from app.main import health_check
from app.services.ai import AIProvider, AIProviderError, AIConfigError, EvaluationDTO
from app.services.resume_parser import ResumeParserService

SECRET_KEY = "sk-test-SECRET-123456"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def make_provider(name, model=None):
    provider = AIProvider()
    provider.provider_name = name
    provider.api_key = SECRET_KEY
    provider.model = provider._resolve_model(model)
    return provider


def gemini_reply(text):
    return FakeResponse(payload={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def openai_reply(text):
    return FakeResponse(payload={"choices": [{"message": {"content": text}}]})


@pytest.fixture
def fake_post(monkeypatch):
    """Patch requests.post; set `fake_post.response` (or `.raises`) before calling."""
    class Recorder:
        calls = []
        response = None
        raises = None

        def __call__(self, url, json=None, headers=None, timeout=None):
            self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
            if self.raises:
                raise self.raises
            return self.response

    rec = Recorder()
    rec.calls = []
    monkeypatch.setattr(ai_module.requests, "post", rec)
    return rec


# ---------------------------------------------------------------------------
# Request shape
# ---------------------------------------------------------------------------
def test_gemini_key_sent_in_header_not_url(fake_post):
    provider = make_provider("gemini")
    fake_post.response = gemini_reply('{"ok": true}')

    assert provider._call_llm_json("hi", system="sys") == {"ok": True}

    call = fake_post.calls[0]
    assert SECRET_KEY not in call["url"]
    assert "key=" not in call["url"]
    assert call["headers"]["x-goog-api-key"] == SECRET_KEY
    assert call["url"].endswith("/gemini-2.5-flash:generateContent")
    assert call["json"]["systemInstruction"] == {"parts": [{"text": "sys"}]}
    assert call["json"]["generationConfig"] == {"responseMimeType": "application/json"}


def test_openai_uses_configured_model_and_system_prompt(fake_post):
    provider = make_provider("openai", model="gpt-4.1-mini")
    fake_post.response = openai_reply('{"ok": true}')

    provider._call_llm_json("hi", system="sys")

    body = fake_post.calls[0]["json"]
    assert body["model"] == "gpt-4.1-mini"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["messages"][-1] == {"role": "user", "content": "hi"}
    assert body["response_format"] == {"type": "json_object"}


def test_text_mode_omits_json_settings(fake_post):
    provider = make_provider("openai")
    fake_post.response = openai_reply("plain text")

    assert provider._call_llm("hi", json_mode=False) == "plain text"
    assert "response_format" not in fake_post.calls[0]["json"]


@pytest.mark.parametrize(
    "provider_name, configured, expected",
    [
        ("gemini", None, "gemini-2.5-flash"),
        ("gemini", "", "gemini-2.5-flash"),
        ("gemini", "gemini-2.5-pro", "gemini-2.5-pro"),
        ("gemini", "gpt-4o-mini", "gemini-2.5-flash"),  # wrong provider's model -> default
        ("openai", None, "gpt-4o-mini"),
        ("openai", "gpt-4.1", "gpt-4.1"),
        ("openai", "gemini-1.5-flash", "gpt-4o-mini"),  # old .env.example value -> default
        ("mock", "anything", None),
    ],
)
def test_resolve_model(provider_name, configured, expected):
    provider = AIProvider()
    provider.provider_name = provider_name
    assert provider._resolve_model(configured) == expected


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
def test_history_mapped_for_gemini_and_openai(fake_post):
    history = [
        {"role": "user", "content": "first q"},
        {"role": "assistant", "content": "first a"},
        {"role": "user", "content": ""},  # empty entries are skipped
    ]

    gemini = make_provider("gemini")
    fake_post.response = gemini_reply("reply")
    gemini._call_llm("now", json_mode=False, history=history)
    contents = fake_post.calls[-1]["json"]["contents"]
    assert [(c["role"], c["parts"][0]["text"]) for c in contents] == [
        ("user", "first q"), ("model", "first a"), ("user", "now"),
    ]

    openai = make_provider("openai")
    fake_post.response = openai_reply("reply")
    openai._call_llm("now", json_mode=False, history=history)
    messages = fake_post.calls[-1]["json"]["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "first q"), ("assistant", "first a"), ("user", "now"),
    ]


def test_coach_chat_sends_prior_turns_without_duplicating_current_message(fake_post):
    provider = make_provider("openai")
    fake_post.response = openai_reply("Work on indexing.")
    history = [
        {"role": "user", "content": "What should I study?"},
        {"role": "assistant", "content": "Databases."},
        {"role": "user", "content": "Which part?"},  # frontend appends the current message
    ]

    reply = provider.generate_coach_chat({"user_name": "Sam"}, "Which part?", history)

    assert reply == "Work on indexing."
    messages = fake_post.calls[0]["json"]["messages"]
    contents = [m["content"] for m in messages]
    assert "What should I study?" in contents
    assert "Databases." in contents
    assert "Which part?" not in contents  # only appears inside the final prompt
    assert sum("Which part?" in c for c in contents) == 1


# ---------------------------------------------------------------------------
# Errors and key redaction
# ---------------------------------------------------------------------------
def test_http_error_is_redacted(fake_post):
    provider = make_provider("openai")
    fake_post.response = FakeResponse(status_code=401, text=f"Incorrect API key provided: {SECRET_KEY}")

    with pytest.raises(AIProviderError) as exc:
        provider._call_llm("hi")
    assert "HTTP 401" in str(exc.value)
    assert SECRET_KEY not in str(exc.value)


def test_network_error_is_redacted(fake_post):
    provider = make_provider("gemini")
    fake_post.raises = requests.ConnectionError(f"failed for ?key={SECRET_KEY}")

    with pytest.raises(AIProviderError) as exc:
        provider._call_llm("hi")
    assert SECRET_KEY not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__


def test_malformed_responses_raise_provider_error(fake_post):
    provider = make_provider("gemini")

    fake_post.response = FakeResponse(payload={"unexpected": True})
    with pytest.raises(AIProviderError):
        provider._call_llm("hi")

    fake_post.response = gemini_reply("not json")
    with pytest.raises(AIProviderError):
        provider._call_llm_json("hi")

    fake_post.response = gemini_reply("[1, 2]")
    with pytest.raises(AIProviderError):
        provider._call_llm_json("hi")


def test_missing_key_and_mock_raise_config_error(fake_post):
    provider = make_provider("openai")
    provider.api_key = None
    with pytest.raises(AIConfigError):
        provider._call_llm("hi")

    mock = AIProvider()
    mock.provider_name = "mock"
    with pytest.raises(AIConfigError):
        mock._call_llm("hi")
    assert fake_post.calls == []


def test_evaluation_falls_back_and_logs_without_key(fake_post, caplog):
    provider = make_provider("gemini")
    fake_post.response = FakeResponse(status_code=500, text=f"boom {SECRET_KEY}")

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        result = provider.evaluate_answer("What is a primary key?", "It uniquely identifies a row.")

    assert isinstance(result, EvaluationDTO)
    assert "answer evaluation failed" in caplog.text
    assert "Falling back to mock output" in caplog.text
    assert SECRET_KEY not in caplog.text


def test_evaluation_uses_llm_result_and_enforces_relevance_gate(fake_post):
    provider = make_provider("openai")
    fake_post.response = openai_reply(json.dumps({
        "score": 9, "correctness": 0.9, "relevance": 0.2, "technical_depth": 0.8,
        "communication_quality": 0.9, "strengths": [], "weaknesses": [], "feedback": "ok",
    }))

    result = provider.evaluate_answer("What is a primary key?", "Python was created by Guido.")
    assert result.score == 2


# ---------------------------------------------------------------------------
# Resume parsing (previously called a non-existent `_post_request`)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("provider_name, reply", [("gemini", gemini_reply), ("openai", openai_reply)])
def test_resume_ai_extraction_works_for_both_providers(fake_post, provider_name, reply):
    provider = make_provider(provider_name)
    profile = {"skills": ["Python", "FastAPI"], "inferred_role": "Backend Developer", "projects": []}
    fake_post.response = reply(json.dumps(profile))

    parser = ResumeParserService(ai_provider=provider)
    assert parser._ai_extract_profile("Python and FastAPI developer") == profile
    assert len(fake_post.calls) == 1


def test_resume_ai_extraction_skipped_for_mock(fake_post):
    provider = AIProvider()
    provider.provider_name = "mock"
    parser = ResumeParserService(ai_provider=provider)
    assert parser._ai_extract_profile("anything") is None
    assert fake_post.calls == []


# ---------------------------------------------------------------------------
# Health endpoint exposes non-secret AI status
# ---------------------------------------------------------------------------
def test_health_reports_ai_status_without_key():
    for body in (health_check(), check_health()):
        assert set(body["ai"]) == {"provider", "model", "api_key_configured"}
        assert SECRET_KEY not in json.dumps(body)
