"""Settings from environment variables. Credentials come only from the environment of the backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigError(ValueError):
    pass


def _get(env, name, default):
    v = env.get(name, "")
    return v.strip() if v and v.strip() else default


def _int(env, name, default, low, high):
    raw = _get(env, name, str(default))
    try:
        v = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if not low <= v <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return v


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("data/covid-healthy-diet")
    covariates: Path | None = None
    llm_provider: str = "offline"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_s: int = 30
    max_history_turns: int = 6
    tts_provider: str = "none"
    tts_voice: str = "Matthew"
    audio_dir: Path = Path(".dietverse/audio")
    api_token: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        llm = _get(env, "DIETVERSE_LLM_PROVIDER", cls.llm_provider).lower()
        if llm not in {"offline", "openai"}:
            raise ConfigError("DIETVERSE_LLM_PROVIDER must be offline or openai")
        tts = _get(env, "DIETVERSE_TTS_PROVIDER", cls.tts_provider).lower()
        if tts not in {"none", "offline", "polly"}:
            raise ConfigError("DIETVERSE_TTS_PROVIDER must be none, offline or polly")
        cov = _get(env, "DIETVERSE_COVARIATES", "")
        return cls(
            data_dir=Path(_get(env, "DIETVERSE_DATA_DIR", str(cls.data_dir))),
            covariates=Path(cov) if cov else None,
            llm_provider=llm,
            llm_base_url=_get(env, "DIETVERSE_LLM_BASE_URL", cls.llm_base_url),
            llm_model=_get(env, "DIETVERSE_LLM_MODEL", cls.llm_model),
            llm_api_key=_get(env, "DIETVERSE_LLM_API_KEY", ""),
            llm_timeout_s=_int(env, "DIETVERSE_LLM_TIMEOUT_S", cls.llm_timeout_s, 1, 600),
            max_history_turns=_int(env, "DIETVERSE_MAX_HISTORY_TURNS", cls.max_history_turns, 0, 50),
            tts_provider=tts,
            tts_voice=_get(env, "DIETVERSE_TTS_VOICE", cls.tts_voice),
            audio_dir=Path(_get(env, "DIETVERSE_AUDIO_DIR", str(cls.audio_dir))),
            api_token=_get(env, "DIETVERSE_API_TOKEN", ""),
        )
