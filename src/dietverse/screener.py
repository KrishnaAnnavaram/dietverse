"""PHQ-2 and GAD-2 short screeners. Information only, not a diagnosis.

Both questionnaires ask about the last 2 weeks. Each item has a score from 0 to 3. A total of 3 or
more is a positive screen: the person can discuss the result with a health professional.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

OPTIONS = {0: "Not at all", 1: "Several days", 2: "More than half the days", 3: "Nearly every day"}
QUESTIONS = {
    "phq2": ["Little interest or pleasure in doing things", "Feeling down, depressed, or hopeless"],
    "gad2": ["Feeling nervous, anxious, or on edge", "Not being able to stop or control worrying"],
}
CUTOFF = 3
RESOURCES = (
    "If you think about harming yourself, contact your local emergency number or a crisis line now. "
    "For other concerns, talk to your doctor or a mental health professional."
)


class ScreenerAnswers(BaseModel):
    phq2: list[int] = Field(min_length=2, max_length=2)
    gad2: list[int] = Field(min_length=2, max_length=2)


def score(answers: ScreenerAnswers) -> dict:
    out = {}
    for name in ("phq2", "gad2"):
        values = getattr(answers, name)
        if any(v not in OPTIONS for v in values):
            raise ValueError(f"{name} answers must be 0, 1, 2 or 3")
        total = sum(values)
        out[name] = {"total": total, "positive": total >= CUTOFF}
    if out["phq2"]["positive"] or out["gad2"]["positive"]:
        msg = ("Your answers are a positive screen. A screen is not a diagnosis. "
               "Talk to a doctor or a mental health professional about how you feel.")
    else:
        msg = "Your answers are below the screening cut-off. If you are worried about how you feel, talk to a professional."
    out["message"] = msg
    out["resources"] = RESOURCES
    return out
