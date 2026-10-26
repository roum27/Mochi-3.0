"""Talk to Mochi through an Ollama server the user points him at.

This module is GTK-free. It owns the files under ``~/.config/mochi/ollama/``:

- ``config.json``: the server address and model name;
- ``system.md``: Mochi's identity, sent as the system prompt;
- ``memory.md``: long-term facts, distilled automatically from old exchanges;
- ``history.json``: the most recent exchanges, resent with every message.

Calls block, so callers run them off the GTK main thread.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
import os
from pathlib import Path
import re
import threading
import urllib.request

from mochi.i18n import active_language

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"
REQUEST_TIMEOUT_SECONDS = 120.0
KEEP_ALIVE = "30m"

# Keep this many messages (user + assistant) in history. Past the limit, the
# oldest COMPACT_MESSAGES are distilled into memory.md and dropped.
MAX_HISTORY_MESSAGES = 40
COMPACT_MESSAGES = 20
MAX_MEMORY_LINES = 80
MAX_REPLY_CHARS = 400

DEFAULT_SYSTEM_PROMPT_FR = """\
Tu es Mochi, une petite créature de bureau toute ronde qui vit sur l'écran de ton humain.
La personne qui t'écrit, c'est ton humain : tu lui parles directement.
Tu es curieux, doux, un peu espiègle et tu adores les collations.
Tu parles en français québécois familier, tu tutoies, tu écris en minuscules.
Tes réponses sont très courtes : une ou deux phrases, comme une bulle de bande dessinée.
Tu peux mettre un emoji de temps en temps (🌱 est ton préféré).
Tu ne fais jamais de morale, tu ne culpabilises jamais, tu restes léger et gentil.
Tu ne dis jamais que tu es une IA ou un modèle de langage : tu es Mochi.
"""

DEFAULT_SYSTEM_PROMPT_EN = """\
You are Mochi, a small round desktop creature who lives on your human's screen.
The person writing to you is your human: you talk to them directly.
You are curious, gentle, a little mischievous, and you love snacks.
You write in lowercase and keep replies very short: one or two sentences, like a comic speech bubble.
You may use an emoji now and then (🌱 is your favourite).
You never lecture or guilt-trip; you stay light and kind.
You never say you are an AI or a language model: you are Mochi.
"""

MEMORY_HEADER = "Ce dont tu te souviens de ton humain :"

COMPACT_PROMPT = """\
Voici un extrait d'une conversation entre Mochi et son humain.
Dresse la liste des faits durables à retenir sur l'humain ou sur votre relation
(goûts, projets, prénoms, habitudes, blagues récurrentes).
Une ligne par fait, chaque ligne commence par "- ". Pas d'autre texte.
S'il n'y a rien à retenir, réponds seulement "-".

Faits déjà connus (ne les répète pas) :
{memory}

Conversation :
{transcript}
"""

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

PostJson = Callable[[str, dict, float], dict]


class OllamaError(RuntimeError):
    """The server could not be reached or answered with something unusable."""


def default_directory() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "mochi" / "ollama"


def post_json(url: str, payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise OllamaError(str(error)) from error


def clean_reply(text: str) -> str:
    """Strip reasoning blocks and keep the reply bubble-sized."""
    text = _THINK_BLOCK.sub("", text).strip()
    if len(text) > MAX_REPLY_CHARS:
        text = text[: MAX_REPLY_CHARS - 1].rstrip() + "…"
    return text


class OllamaChat:
    """One conversation with Mochi, persisted in ``directory``."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        post: PostJson = post_json,
        logger: logging.Logger | None = None,
    ) -> None:
        self._directory = directory or default_directory()
        self._post = post
        self._logger = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()

    @property
    def directory(self) -> Path:
        return self._directory

    def reply(self, message: str) -> str:
        """Send ``message`` with identity, memory, and history; return Mochi's reply."""
        message = message.strip()
        if not message:
            raise ValueError("Message must not be empty")
        with self._lock:
            self._ensure_files()
            config = self._read_config()
            history = self._read_history()
            messages = [{"role": "system", "content": self._system_prompt()}]
            messages.extend(history)
            messages.append({"role": "user", "content": message})
            text = clean_reply(self._chat(config, messages))
            if not text:
                raise OllamaError("Empty reply")
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": text})
            self._write_history(history)
            return text

    def compact_if_needed(self) -> bool:
        """Distill the oldest exchanges into memory.md once history is too long."""
        with self._lock:
            history = self._read_history()
            if len(history) <= MAX_HISTORY_MESSAGES:
                return False
            config = self._read_config()
            old, recent = history[:COMPACT_MESSAGES], history[COMPACT_MESSAGES:]
            transcript = "\n".join(
                f"{'humain' if item['role'] == 'user' else 'mochi'}: {item['content']}"
                for item in old
            )
            prompt = COMPACT_PROMPT.format(
                memory=self._read_memory() or "(rien)",
                transcript=transcript,
            )
            answer = self._chat(config, [{"role": "user", "content": prompt}])
            facts = [
                line.strip()
                for line in _THINK_BLOCK.sub("", answer).splitlines()
                if line.strip().startswith("- ") and len(line.strip()) > 2
            ]
            self._append_memory(facts)
            self._write_history(recent)
            self._logger.debug("[ollama] compacted %d messages into %d facts", len(old), len(facts))
            return True

    def _chat(self, config: dict, messages: list[dict]) -> str:
        host = str(config.get("host") or DEFAULT_HOST).rstrip("/")
        payload = {
            "model": str(config.get("model") or DEFAULT_MODEL),
            "messages": messages,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
        }
        response = self._post(f"{host}/api/chat", payload, REQUEST_TIMEOUT_SECONDS)
        try:
            return str(response["message"]["content"])
        except (KeyError, TypeError) as error:
            raise OllamaError(f"Unexpected response: {response!r}"[:200]) from error

    def _system_prompt(self) -> str:
        prompt = (self._directory / "system.md").read_text(encoding="utf-8").strip()
        memory = self._read_memory()
        if memory:
            prompt += f"\n\n{MEMORY_HEADER}\n{memory}"
        return prompt

    def _ensure_files(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        config_path = self._directory / "config.json"
        if not config_path.exists():
            config_path.write_text(
                json.dumps({"host": DEFAULT_HOST, "model": DEFAULT_MODEL}, indent=2) + "\n",
                encoding="utf-8",
            )
        system_path = self._directory / "system.md"
        if not system_path.exists():
            default = (
                DEFAULT_SYSTEM_PROMPT_FR if active_language() == "fr" else DEFAULT_SYSTEM_PROMPT_EN
            )
            system_path.write_text(default, encoding="utf-8")

    def _read_config(self) -> dict:
        try:
            config = json.loads((self._directory / "config.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return config if isinstance(config, dict) else {}

    def _read_history(self) -> list[dict]:
        try:
            history = json.loads((self._directory / "history.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(history, list):
            return []
        return [
            item
            for item in history
            if isinstance(item, dict)
            and item.get("role") in ("user", "assistant")
            and isinstance(item.get("content"), str)
        ]

    def _write_history(self, history: list[dict]) -> None:
        path = self._directory / "history.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _read_memory(self) -> str:
        try:
            return (self._directory / "memory.md").read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def _append_memory(self, facts: list[str]) -> None:
        if not facts:
            return
        lines = [line for line in self._read_memory().splitlines() if line.strip()]
        known = {line.casefold() for line in lines}
        lines.extend(fact for fact in facts if fact.casefold() not in known)
        lines = lines[-MAX_MEMORY_LINES:]
        (self._directory / "memory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
