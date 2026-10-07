"""The nutrition assistant behind the VR client and the web page.

- A health-safe system prompt, a capped history and a configurable model.
- Red-flag messages get a fixed urgent-care answer before any model call.
- The offline assistant answers from the diet guide and a small FAQ, with no key and no network.
- Each answer can get its own audio file. Calls are synchronous, and errors go back to the caller.
"""

from __future__ import annotations

import re
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .guidelines import LIMITS
from .tts import NoSpeech, Speech

SYSTEM_PROMPT = (
    "You are a nutrition assistant in a learning app. Give general, evidence-based diet information in at most "
    "120 words. Do not diagnose, do not change medicines and do not give advice for pregnancy, eating disorders "
    "or kidney disease: tell the user to ask a clinician. If the user describes an emergency, tell them to call "
    "emergency services. Say when you are not sure."
)
URGENT = ("This can be an emergency. Call your local emergency number now, or go to the nearest emergency department.")
RED_FLAGS = re.compile(
    r"\b(chest pain|can'?t breathe|shortness of breath|faint(?:ed|ing)?|suicid\w*|kill myself|self[- ]harm|"
    r"overdose|severe allergic|anaphyla\w*|throat (?:is )?swelling)\b", re.I)
MAX_CHARS = 800

FAQ = [
    (("protein", "vegan", "vegetarian"), "Plant protein comes from beans, lentils, tofu, nuts and seeds. "
     "Eat a mix of them over the day to get all essential amino acids."),
    (("sugar", "sweet", "dessert"), f"Keep added sugars {LIMITS['added_sugars']}. Water, milk and unsweetened "
     "drinks are better choices than soft drinks."),
    (("salt", "sodium"), f"Keep sodium {LIMITS['sodium']}. Most sodium comes from processed and restaurant food."),
    (("fruit", "vegetable", "veggies"), "Fill half of your plate with vegetables and fruit, and choose many colours."),
    (("covid", "recover", "recovery"), "While you recover from COVID-19, eat enough energy and protein and drink "
     "enough fluid. If you lost weight, ask for a dietitian referral."),
    (("water", "drink", "hydrat"), "Drink water through the day. Your needs go up with heat and exercise."),
    (("fat", "oil", "butter"), f"Choose plant oils instead of butter. Keep saturated fat {LIMITS['saturated_fat']}."),
]
FALLBACK = ("I can answer general questions about food groups, protein, sugar, salt, fats and drinks. "
            "For advice about your own health, talk to a doctor or a registered dietitian.")


class AssistantError(RuntimeError):
    pass


class OfflineBrain:
    name = "offline-faq"

    def reply(self, messages: list[dict]) -> str:
        text = messages[-1]["content"].lower()
        for words, answer in FAQ:
            if any(w in text for w in words):
                return answer
        return FALLBACK


class OpenAIBrain:
    """Any OpenAI-compatible /chat/completions endpoint. The key stays in the backend environment."""

    def __init__(self, base_url: str, model: str, api_key: str, timeout_s: float, transport=None):
        if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
            raise AssistantError("DIETVERSE_LLM_API_KEY is empty")
        self.name = f"openai:{model}"
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(timeout=timeout_s, headers=headers, transport=transport)

    def reply(self, messages: list[dict]) -> str:
        try:
            r = self._client.post(self._url, json={"model": self._model, "messages": messages, "temperature": 0.2,
                                                   "max_tokens": 300})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise AssistantError(f"chat model failed: {exc}") from exc


@dataclass
class Reply:
    text: str
    status: str  # answered | urgent | error
    audio: str | None = None
    turns_in_context: int = 0


@dataclass
class Assistant:
    brain: object
    speech: Speech = field(default_factory=NoSpeech)
    max_history_turns: int = 6
    _sessions: dict[str, list[dict]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def new_session(self) -> str:
        sid = secrets.token_urlsafe(16)
        with self._lock:
            self._sessions[sid] = []
        return sid

    def ask(self, session_id: str, text: str, *, speak: bool = False) -> Reply:
        text = re.sub(r"\s+", " ", (text or "")).strip()
        if not text:
            raise ValueError("the message is empty")
        if len(text) > MAX_CHARS:
            raise ValueError(f"the message has more than {MAX_CHARS} characters")
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("unknown session")
            history = list(self._sessions[session_id])
        if RED_FLAGS.search(text):
            reply = Reply(URGENT, "urgent")
        else:
            window = history[-2 * self.max_history_turns:] if self.max_history_turns else []
            messages = [{"role": "system", "content": SYSTEM_PROMPT}, *window, {"role": "user", "content": text}]
            try:
                reply = Reply(self.brain.reply(messages), "answered", turns_in_context=len(window) // 2)
            except AssistantError as exc:
                return Reply(f"The assistant is not available now. ({exc})", "error")
        if speak:
            path = self.speech.synthesize(reply.text)
            reply.audio = Path(path).name if path else None
        with self._lock:
            turns = self._sessions[session_id]
            turns += [{"role": "user", "content": text}, {"role": "assistant", "content": reply.text}]
            del turns[: max(0, len(turns) - 2 * max(self.max_history_turns, 1) * 4)]
        return reply
