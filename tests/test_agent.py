from datetime import date
from types import SimpleNamespace

import pytest

from api import agent as agent_module
from api.agent import AgentConfig, ChatAgent
from api.tools import HANDLERS


def _found_citation():
    return {
        "status": "found",
        "authority": {
            "title": "Absconding Debtors",
            "chapter_number": "8:08",
            "section_ref": "4",
            "heading": "Power to arrest",
            "chunk_text": "A debtor may be arrested in the prescribed case.",
            "chunk_index": 0,
            "chunk_id": 42,
            "version_id": 1,
            "download_id": 105522,
            "as_at_date": date(2009, 12, 31),
            "version_label": "2009 revision",
        },
        "alternatives": [],
    }


class FakeDB:
    def __init__(self, citation=None):
        self.citation = citation or _found_citation()

    async def resolve_citation(self, chapter, section, as_at_date=None):
        return self.citation


def _message(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(name="resolve_citation", arguments=None):
    return SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(
            name=name,
            arguments=arguments or '{"chapter": "8:08", "section": "4"}',
        ),
    )


def _response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture
def agent(configured):
    return ChatAgent(FakeDB())


@pytest.fixture
def unconfigured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _stub_client(monkeypatch, responses):
    client = ScriptedClient(responses)
    monkeypatch.setattr(agent_module, "AsyncOpenAI", lambda **kw: client)
    return client


@pytest.mark.asyncio
async def test_unconfigured_returns_unconfigured(unconfigured):
    result = await ChatAgent(FakeDB()).run(
        [{"role": "user", "content": "What does s. 4 say?"}]
    )
    assert result["status"] == "unconfigured"


@pytest.mark.asyncio
async def test_grounded_answer_returns_sources(monkeypatch, agent):
    client = _stub_client(
        monkeypatch,
        [
            _response(_message("", [_tool_call()])),
            _response(
                _message(
                    '{"answer": "Section 4 of the Absconding Debtors Act allows '
                    'arrest in the prescribed case.", "source_ids": ["chunk:42"]}'
                )
            ),
        ],
    )
    result = await agent.run([{"role": "user", "content": "What does s. 4 say?"}])
    assert result["status"] == "ok"
    assert "prescribed case" in result["answer"]
    assert [s["id"] for s in result["sources"]] == ["chunk:42"]
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_unknown_source_id_is_refused(monkeypatch, agent):
    _stub_client(
        monkeypatch,
        [
            _response(_message("", [_tool_call()])),
            _response(
                _message(
                    '{"answer": "Section 4 says something.", '
                    '"source_ids": ["chunk:999"]}'
                )
            ),
        ],
    )
    result = await agent.run([{"role": "user", "content": "What does s. 4 say?"}])
    assert result["status"] == "refused"


@pytest.mark.asyncio
async def test_empty_source_ids_is_refused(monkeypatch, agent):
    _stub_client(
        monkeypatch,
        [
            _response(_message("", [_tool_call()])),
            _response(
                _message('{"answer": "I recall it says X.", "source_ids": []}')
            ),
        ],
    )
    result = await agent.run([{"role": "user", "content": "What does s. 4 say?"}])
    assert result["status"] == "refused"


@pytest.mark.asyncio
async def test_conversational_plain_text_passes_through(monkeypatch, agent):
    _stub_client(
        monkeypatch,
        [_response(_message("Hello! I can look up provisions of the Laws of T&T."))],
    )
    result = await agent.run([{"role": "user", "content": "Hi"}])
    assert result["status"] == "ok"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_plain_text_after_tools_is_refused(monkeypatch, agent):
    _stub_client(
        monkeypatch,
        [
            _response(_message("", [_tool_call()])),
            _response(_message("I think section 4 says something about arrest.")),
        ],
    )
    result = await agent.run([{"role": "user", "content": "What does s. 4 say?"}])
    assert result["status"] == "refused"


@pytest.mark.asyncio
async def test_iteration_budget_is_capped(monkeypatch, agent):
    responses = [_response(_message("", [_tool_call()])) for _ in range(9)]
    _stub_client(monkeypatch, responses)
    result = await agent.run([{"role": "user", "content": "Keep going"}])
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_llm_error_returns_error(monkeypatch, agent):
    class BoomClient:
        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        async def create(self, **kwargs):
            raise RuntimeError("model down")

    monkeypatch.setattr(agent_module, "AsyncOpenAI", lambda **kw: BoomClient())
    result = await agent.run([{"role": "user", "content": "Hi"}])
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_parse_structured_reply_tolerates_prose():
    parsed = agent_module._parse_structured_reply(
        'Here you go:\n{"answer": "Yes", "source_ids": ["chunk:1"]}\nThanks.'
    )
    assert parsed == {"answer": "Yes", "source_ids": ["chunk:1"]}


def test_tool_schemas_are_registered():
    names = {t["function"]["name"] for t in agent_module.TOOL_DEFINITIONS}
    assert names == set(HANDLERS)


@pytest.mark.asyncio
async def test_chat_endpoint_wiring_returns_unconfigured(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from api.main import app

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "What does s. 4 say?"}],
                "mode": "research",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unconfigured"
    assert body["sources"] == []