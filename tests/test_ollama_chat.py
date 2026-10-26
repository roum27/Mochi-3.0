from __future__ import annotations

import json

import pytest

from mochi import ollama_chat
from mochi.ollama_chat import OllamaChat, OllamaError, clean_reply


class _FakeServer:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        self.calls.append((url, payload))
        return {"message": {"role": "assistant", "content": self.replies.pop(0)}}


def test_first_reply_creates_files_and_sends_identity(tmp_path) -> None:
    server = _FakeServer("allo toi 🌱")
    chat = OllamaChat(tmp_path, post=server)

    assert chat.reply("  salut mochi ") == "allo toi 🌱"

    assert json.loads((tmp_path / "config.json").read_text())["host"] == ollama_chat.DEFAULT_HOST
    url, payload = server.calls[0]
    assert url == f"{ollama_chat.DEFAULT_HOST}/api/chat"
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert "Mochi" in payload["messages"][0]["content"]
    assert payload["messages"][-1] == {"role": "user", "content": "salut mochi"}
    assert json.loads((tmp_path / "history.json").read_text()) == [
        {"role": "user", "content": "salut mochi"},
        {"role": "assistant", "content": "allo toi 🌱"},
    ]


def test_config_system_prompt_memory_and_history_are_used(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"host": "http://192.168.1.207:11434/", "model": "gemma3:4b"})
    )
    (tmp_path / "system.md").write_text("tu es mochi.")
    (tmp_path / "memory.md").write_text("- aime le café\n")
    (tmp_path / "history.json").write_text(
        json.dumps([{"role": "user", "content": "yo"}, {"role": "assistant", "content": "yo!"}])
    )
    server = _FakeServer("oui")
    OllamaChat(tmp_path, post=server).reply("ça va?")

    url, payload = server.calls[0]
    assert url == "http://192.168.1.207:11434/api/chat"
    assert payload["model"] == "gemma3:4b"
    system = payload["messages"][0]["content"]
    assert system.startswith("tu es mochi.")
    assert "- aime le café" in system
    assert [item["content"] for item in payload["messages"][1:]] == ["yo", "yo!", "ça va?"]


def test_failed_request_leaves_history_untouched(tmp_path) -> None:
    def unreachable(url, payload, timeout):
        raise OllamaError("connection refused")

    chat = OllamaChat(tmp_path, post=unreachable)
    with pytest.raises(OllamaError):
        chat.reply("allo?")
    assert not (tmp_path / "history.json").exists()


def test_malformed_response_raises_ollama_error(tmp_path) -> None:
    chat = OllamaChat(tmp_path, post=lambda url, payload, timeout: {"error": "no model"})
    with pytest.raises(OllamaError):
        chat.reply("allo?")


def test_reply_cleanup_strips_thinking_and_caps_length() -> None:
    assert clean_reply("<think>hmm</think>\n  coucou ") == "coucou"
    long = clean_reply("a" * 1000)
    assert len(long) == ollama_chat.MAX_REPLY_CHARS
    assert long.endswith("…")


def test_compaction_moves_old_exchanges_into_memory(tmp_path) -> None:
    history = []
    for index in range(ollama_chat.MAX_HISTORY_MESSAGES // 2 + 1):
        history.append({"role": "user", "content": f"message {index}"})
        history.append({"role": "assistant", "content": f"réponse {index}"})
    (tmp_path / "history.json").write_text(json.dumps(history))
    (tmp_path / "memory.md").write_text("- aime le café\n")
    server = _FakeServer("- aime le café\n- code mochi le soir\nblabla")
    chat = OllamaChat(tmp_path, post=server)

    assert chat.compact_if_needed() is True

    prompt = server.calls[0][1]["messages"][0]["content"]
    assert "humain: message 0" in prompt
    assert "- aime le café" in prompt
    assert (tmp_path / "memory.md").read_text() == "- aime le café\n- code mochi le soir\n"
    remaining = json.loads((tmp_path / "history.json").read_text())
    assert remaining == history[ollama_chat.COMPACT_MESSAGES :]


def test_short_history_is_not_compacted(tmp_path) -> None:
    server = _FakeServer()
    chat = OllamaChat(tmp_path, post=server)
    assert chat.compact_if_needed() is False
    assert server.calls == []
