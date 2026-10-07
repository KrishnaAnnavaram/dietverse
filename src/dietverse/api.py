"""Backend for the VR client and other clients (extra: api).

The VR client calls only this backend. Model keys and AWS credentials stay in the backend environment.
If ``DIETVERSE_API_TOKEN`` is set, every /api request needs ``Authorization: Bearer <token>``.
"""

from __future__ import annotations

import hmac
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .assistant import Assistant
from .data import Dataset
from .plan import Profile, make_plan
from .screener import ScreenerAnswers, score


class ChatIn(BaseModel):
    session_id: str = Field(max_length=64)
    message: str = Field(max_length=2000)
    speak: bool = False


def create_app(assistant: Assistant, dataset: Dataset | None, audio_dir: Path, api_token: str = "") -> FastAPI:
    app = FastAPI(title="dietverse backend", docs_url=None, redoc_url=None)

    def auth(authorization: str = Header(default="")) -> None:
        if api_token and not hmac.compare_digest(authorization, f"Bearer {api_token}"):
            raise HTTPException(401, "missing or wrong token")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/plan", dependencies=[Depends(auth)])
    def plan(profile: dict) -> dict:
        try:
            p = Profile.model_validate(profile)
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc
        ctx = None
        if p.country and dataset is not None:
            try:
                ctx = dataset.country_profile(p.country)
            except KeyError:
                ctx = None
        return make_plan(p, ctx).model_dump()

    @app.post("/api/screener", dependencies=[Depends(auth)])
    def screener(answers: ScreenerAnswers) -> dict:
        try:
            return score(answers)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/session", dependencies=[Depends(auth)])
    def session() -> dict:
        return {"session_id": assistant.new_session()}

    @app.post("/api/chat", dependencies=[Depends(auth)])
    def chat(body: ChatIn) -> dict:
        try:
            r = assistant.ask(body.session_id, body.message, speak=body.speak)
        except KeyError as exc:
            raise HTTPException(404, "unknown session") from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"text": r.text, "status": r.status, "audio_url": f"/api/audio/{r.audio}" if r.audio else None}

    @app.get("/api/audio/{name}", dependencies=[Depends(auth)])
    def audio(name: str):
        if not name.replace(".", "").isalnum() or name.count(".") != 1:
            raise HTTPException(400, "bad file name")
        path = Path(audio_dir) / name
        if not path.is_file():
            raise HTTPException(404, "no such audio file")
        return FileResponse(path)

    @app.get("/api/countries", dependencies=[Depends(auth)])
    def countries() -> dict:
        return {"countries": dataset.countries() if dataset else []}

    return app
