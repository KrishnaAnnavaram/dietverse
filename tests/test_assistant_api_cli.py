import json
import tomllib
import wave
from pathlib import Path

import httpx
import pytest

from dietverse.assistant import SYSTEM_PROMPT, URGENT, Assistant, AssistantError, OfflineBrain, OpenAIBrain
from dietverse.cli import main
from dietverse.config import ConfigError, Settings
from dietverse.tts import OfflineTone


class RecordingBrain:
    name = "recording"

    def __init__(self):
        self.calls = []

    def reply(self, messages):
        self.calls.append(messages)
        return f"answer {len(self.calls)}"


def test_history_is_capped_and_system_prompt_is_first():
    brain = RecordingBrain()
    a = Assistant(brain, max_history_turns=2)
    sid = a.new_session()
    for i in range(6):
        r = a.ask(sid, f"question {i} about fruit")
    last = brain.calls[-1]
    assert last[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert len(last) == 1 + 2 * 2 + 1 and r.turns_in_context == 2
    assert last[-1]["content"] == "question 5 about fruit"


def test_red_flags_skip_the_model():
    brain = RecordingBrain()
    a = Assistant(brain)
    sid = a.new_session()
    r = a.ask(sid, "I have chest pain after dinner")
    assert r.status == "urgent" and r.text == URGENT and brain.calls == []


def test_input_and_session_checks():
    a = Assistant(OfflineBrain())
    with pytest.raises(KeyError):
        a.ask("missing", "hi")
    sid = a.new_session()
    with pytest.raises(ValueError):
        a.ask(sid, "   ")
    with pytest.raises(ValueError):
        a.ask(sid, "x" * 900)
    assert "sodium" in a.ask(sid, "Is salt bad?").text.lower()


def test_each_answer_gets_its_own_audio_file(tmp_path):
    a = Assistant(OfflineBrain(), OfflineTone(tmp_path))
    sid = a.new_session()
    r1, r2 = a.ask(sid, "salt?", speak=True), a.ask(sid, "sugar?", speak=True)
    assert r1.audio != r2.audio and (tmp_path / r1.audio).exists() and (tmp_path / r2.audio).exists()
    with wave.open(str(tmp_path / r1.audio)) as w:
        assert w.getnframes() > 0


def test_openai_brain_errors_are_reported_not_swallowed():
    ok = OpenAIBrain("http://llm.test/v1", "m", "k", 5,
                     transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": " hi "}}]})))
    assert ok.reply([{"role": "user", "content": "x"}]) == "hi"
    bad = OpenAIBrain("http://llm.test/v1", "m", "k", 5, transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    a = Assistant(bad)
    r = a.ask(a.new_session(), "fruit?")
    assert r.status == "error" and "not available" in r.text
    with pytest.raises(AssistantError):
        OpenAIBrain("https://api.example.com/v1", "m", "", 5)


def test_settings_from_env():
    s = Settings.from_env({"DIETVERSE_TTS_PROVIDER": "offline", "DIETVERSE_MAX_HISTORY_TURNS": "3"})
    assert s.tts_provider == "offline" and s.max_history_turns == 3 and s.llm_provider == "offline"
    with pytest.raises(ConfigError):
        Settings.from_env({"DIETVERSE_LLM_PROVIDER": "magic"})


def test_no_credentials_in_the_client_or_the_package():
    root = Path(__file__).parents[1]
    for path in list((root / "clients").rglob("*.cs")) + list((root / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "AKIA" not in text and "sk-" not in text and "aws_secret_access_key" not in text.lower()


def test_heavy_and_cloud_packages_are_extras_only():
    meta = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    core = " ".join(meta["project"]["dependencies"])
    for pkg in ("boto3", "streamlit", "fastapi", "openai"):
        assert pkg not in core


def test_cli_commands(tmp_path, capsys):
    assert main(["demo", "--out", str(tmp_path / "demo")]) == 0
    out = capsys.readouterr().out
    assert "[plan] BMI" in out and "emergency" in out
    data = str(tmp_path / "demo")
    assert main(["--data-dir", data, "analyze", "--exposure", "Meat", "--n-boot", "20"]) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["exposure"] == "Meat"
    assert main(["--data-dir", data, "plan", "--age", "30", "--sex", "male", "--weight", "80", "--height", "180",
                 "--diet", "vegetarian", "--allergy", "egg"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "plan"
    assert main(["screener", "--phq2", "2", "2", "--gad2", "0", "0"]) == 0
    assert json.loads(capsys.readouterr().out)["phq2"]["positive"] is True
    assert main(["--data-dir", data, "explore", "--country", "Country 002"]) == 0
    assert main(["plan", "--age", "12", "--sex", "male", "--weight", "40", "--height", "150"]) == 2
    assert main(["--data-dir", str(tmp_path / "none"), "explore"]) == 2


def test_api(ds, tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from dietverse.api import create_app

    app = create_app(Assistant(OfflineBrain(), OfflineTone(tmp_path)), ds, tmp_path, api_token="t0k")
    c = TestClient(app)
    assert c.post("/api/session").status_code == 401
    h = {"Authorization": "Bearer t0k"}
    sid = c.post("/api/session", headers=h).json()["session_id"]
    r = c.post("/api/chat", json={"session_id": sid, "message": "salt?", "speak": True}, headers=h).json()
    assert r["status"] == "answered" and r["audio_url"].startswith("/api/audio/")
    assert c.get(r["audio_url"], headers=h).status_code == 200
    assert c.get("/api/audio/..%2Fsecret.txt", headers=h).status_code in (400, 404)
    plan = c.post("/api/plan", json={"age": 40, "sex": "female", "weight_kg": 70, "height_cm": 165,
                                      "country": ds.countries()[0]}, headers=h).json()
    assert plan["status"] == "plan" and plan["country_context"]
    assert c.post("/api/plan", json={"age": 10, "sex": "female", "weight_kg": 30, "height_cm": 130}, headers=h).status_code == 422
    assert c.post("/api/screener", json={"phq2": [3, 3], "gad2": [0, 0]}, headers=h).json()["phq2"]["positive"]


def test_streamlit_app_runs(data_dir, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DIETVERSE_DATA_DIR", str(data_dir))
    app = Path(__file__).parents[1] / "src" / "dietverse" / "web" / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=60).run()
    assert not at.exception
