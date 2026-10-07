"""The ``dietverse`` command."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from pydantic import ValidationError

from .analytics import associations, cfr_vs_deaths, load_covariates
from .assistant import Assistant, AssistantError, OfflineBrain, OpenAIBrain
from .config import ConfigError, Settings
from .data import GROUPS, DataError, load_dataset
from .plan import Profile, make_plan
from .screener import ScreenerAnswers, score
from .synthetic import write_synthetic
from .tts import build_speech


def _settings(args) -> Settings:
    s = Settings.from_env()
    if getattr(args, "data_dir", None):
        s = replace(s, data_dir=Path(args.data_dir))
    return s


def build_assistant(s: Settings) -> Assistant:
    brain = OfflineBrain() if s.llm_provider == "offline" else OpenAIBrain(
        s.llm_base_url, s.llm_model, s.llm_api_key, s.llm_timeout_s)
    return Assistant(brain, build_speech(s.tts_provider, s.audio_dir, s.tts_voice), s.max_history_turns)


def cmd_synth(args) -> int:
    print(f"wrote synthetic files to {write_synthetic(Path(args.out))}")
    return 0


def cmd_explore(args) -> int:
    ds = load_dataset(_settings(args).data_dir)
    if args.country:
        print(json.dumps(ds.country_profile(args.country, args.measure, args.top), indent=2))
    else:
        rep = {m: r.__dict__ for m, r in ds.reports.items()}
        print(json.dumps({"countries": len(ds.countries()), "load_reports": rep}, indent=2, default=str))
    return 0


def cmd_analyze(args) -> int:
    s = _settings(args)
    ds = load_dataset(s.data_dir)
    cov_path = Path(args.covariates) if args.covariates else s.covariates
    cov = load_covariates(cov_path) if cov_path else None
    res = associations(ds, args.exposures or ["Animal fats", "obesity_pct"], args.outcome, measure=args.measure,
                       covariates=cov, n_boot=args.n_boot, seed=args.seed)
    res["cfr_check"] = cfr_vs_deaths(ds)
    print(json.dumps(res, indent=2))
    return 0


def cmd_plan(args) -> int:
    s = _settings(args)
    data = json.loads(Path(args.profile).read_text(encoding="utf-8")) if args.profile else {
        "age": args.age, "sex": args.sex, "weight_kg": args.weight, "height_cm": args.height,
        "activity": args.activity, "goal": args.goal, "diet": args.diet, "allergies": args.allergy or [],
        "intolerances": args.intolerance or [], "conditions": args.condition or [],
        "pregnant_or_breastfeeding": args.pregnant, "country": args.country}
    profile = Profile.model_validate(data)
    ctx = None
    if profile.country:
        ctx = load_dataset(s.data_dir).country_profile(profile.country)
    print(json.dumps(make_plan(profile, ctx).model_dump(), indent=2))
    return 0


def cmd_screener(args) -> int:
    print(json.dumps(score(ScreenerAnswers(phq2=args.phq2, gad2=args.gad2)), indent=2))
    return 0


def cmd_chat(args) -> int:
    a = build_assistant(_settings(args))
    sid = a.new_session()
    for message in args.messages:
        r = a.ask(sid, message, speak=args.speak)
        print(f"> {message}\n{r.text}" + (f"\n[audio: {r.audio}]" if r.audio else ""))
    return 0


def cmd_serve(args) -> int:  # pragma: no cover - needs the "api" extra
    import uvicorn

    from .api import create_app

    s = _settings(args)
    try:
        ds = load_dataset(s.data_dir)
    except FileNotFoundError:
        ds = None
    uvicorn.run(create_app(build_assistant(s), ds, s.audio_dir, s.api_token), host=args.host, port=args.port)
    return 0


def cmd_web(args) -> int:  # pragma: no cover - needs the "web" extra
    app = Path(__file__).parent / "web" / "streamlit_app.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)])


def cmd_demo(args) -> int:
    out = Path(args.out or ".dietverse/demo")
    data = write_synthetic(out)
    ds = load_dataset(data)
    print("[explore]", json.dumps(ds.country_profile(ds.countries()[0])))
    res = associations(ds, ["Animal fats", "obesity_pct"], "deaths_per_100k", covariates=load_covariates(data / "covariates.csv"),
                       n_boot=300, seed=0)
    for r in res["results"]:
        print(f"[analyze] {r['exposure']} vs deaths_per_100k: spearman {r['spearman']}, partial {r['partial_spearman']} "
              f"{r['partial_ci95']} (n={r['n_countries']}, controls {r['controls']})")
    print("[analyze]", res["caveat"])
    p = Profile(age=45, sex="female", weight_kg=72, height_cm=165, activity="light", goal="lose", diet="vegetarian",
                allergies=["peanut"], conditions=["hypertension"], country=ds.countries()[0])
    plan = make_plan(p, ds.country_profile(p.country))
    print(f"[plan] BMI {plan.bmi} ({plan.bmi_category}), target {plan.energy['target_kcal']} kcal, pattern {plan.pattern_kcal}")
    for t in plan.targets:
        print(f"[plan]   {t.group}: {t.amount} {t.unit} e.g. {', '.join(t.examples[:3])}")
    print("[screener]", score(ScreenerAnswers(phq2=[1, 1], gad2=[2, 2]))["message"])
    a = Assistant(OfflineBrain())
    sid = a.new_session()
    print("[chat]", a.ask(sid, "How much salt is OK?").text)
    print("[chat]", a.ask(sid, "I have chest pain").text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dietverse", description="Diet analytics with correct units and a diet guide.")
    p.add_argument("--data-dir")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("synth", help="write synthetic data files")
    sp.add_argument("--out", default="data/synthetic")
    sp.set_defaults(func=cmd_synth)

    sp = sub.add_parser("explore", help="load report, or the top food groups of one country")
    sp.add_argument("--country")
    sp.add_argument("--measure", default="energy", choices=["energy", "quantity", "fat", "protein"])
    sp.add_argument("--top", type=int, default=6)
    sp.set_defaults(func=cmd_explore)

    sp = sub.add_parser("analyze", help="country-level associations with controls")
    sp.add_argument("--outcome", default="deaths_per_100k", choices=["deaths_per_100k", "obesity_pct", "cfr_pct"])
    sp.add_argument("--exposure", dest="exposures", action="append", help=f"repeat. Choices: {GROUPS} or obesity_pct")
    sp.add_argument("--measure", default="energy", choices=["energy", "quantity", "fat", "protein"])
    sp.add_argument("--covariates", help="CSV with Country and control columns")
    sp.add_argument("--n-boot", type=int, default=500)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("plan", help="diet guide for one adult")
    sp.add_argument("--profile", help="JSON file with the profile")
    sp.add_argument("--age", type=int)
    sp.add_argument("--sex", choices=["female", "male"])
    sp.add_argument("--weight", type=float)
    sp.add_argument("--height", type=float)
    sp.add_argument("--activity", default="sedentary")
    sp.add_argument("--goal", default="maintain")
    sp.add_argument("--diet", default="omnivore")
    sp.add_argument("--allergy", action="append")
    sp.add_argument("--intolerance", action="append")
    sp.add_argument("--condition", action="append")
    sp.add_argument("--pregnant", action="store_true")
    sp.add_argument("--country")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("screener", help="PHQ-2 and GAD-2 scores")
    sp.add_argument("--phq2", type=int, nargs=2, required=True)
    sp.add_argument("--gad2", type=int, nargs=2, required=True)
    sp.set_defaults(func=cmd_screener)

    sp = sub.add_parser("chat", help="ask the assistant one or more messages")
    sp.add_argument("messages", nargs="+")
    sp.add_argument("--speak", action="store_true")
    sp.set_defaults(func=cmd_chat)

    sp = sub.add_parser("serve", help="start the backend for the VR client (extra: api)")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)
    sp.set_defaults(func=cmd_serve)

    sub.add_parser("web", help="start the Streamlit dashboard (extra: web)").set_defaults(func=cmd_web)

    sp = sub.add_parser("demo", help="offline demo on synthetic data")
    sp.add_argument("--out")
    sp.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValidationError as exc:
        print(f"error: {exc.errors(include_url=False)[0]['msg']}", file=sys.stderr)
        return 2
    except (ConfigError, DataError, AssistantError, FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
