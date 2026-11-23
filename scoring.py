"""Scoring functions for the evaluation. No API calls, testable logic."""
import re
import numpy as np
import pandas as pd
from prompts import REFUSAL_PHRASE

# A number: optional minus (not when a digit comes right before it, as in "2007-2015"),
# digits with optional thousands commas, optional decimals.
NUMBER_RE = re.compile(r"(?<!\d)-?\d+(?:,\d{3})*(?:\.\d+)?")
CODE_BLOCK_RE = re.compile(r"```.*?(?:```|$)", re.DOTALL)  # closed or unclosed fences

def strip_code(answer:str) -> str:
    """Remove fenced code blocks, so numbers in the echoed SQL don't count."""
    return CODE_BLOCK_RE.sub(" ", answer or "")

def extract_numbers(text: str) -> list[float]:
    """All numbers in the text, with thousands comma removed."""
    return [float(m.replace(",", "")) for m in NUMBER_RE.findall(text)]

def gold_numbers(df: pd.DataFrame) -> list[float]:
    """Every numeric (non-null) cell in a gold result, as float."""
    nums = []
    for v in df.to_numpy().ravel():
        if isinstance(v, (bool, np.bool_)) or pd.isna(v):
            continue
        if isinstance(v, (int, float, np.integer, np.floating)):
            nums.append(float(v))
    return nums

def number_found(gold: float, found: list[float]) -> bool:
    """Integers must match exactly. Decimals may be rounded to 1-3 places, or to a
    whole number only if the value is 10 or more (so a stray '1' can't match 1.106)."""
    if gold == int(gold):
        return gold in found
    places = (0, 1, 2, 3) if abs(gold) >= 10 else (1, 2, 3)
    return any(round(gold, d) == n for d in places for n in found)

def check_numbers(answer: str, gold_df: pd.DataFrame) -> tuple[bool, str]:
    """Pass if every gold number appears in the answer's prose (code block excluded)."""
    found = extract_numbers(strip_code(answer))
    missing = [g for g in gold_numbers(gold_df) if not number_found(g, found)]
    if missing:
        return False, f"missing numbers: {missing}"
    return True, f"all gold numbers found"

def _normalise(text: str) -> str:
    """Lowercase, drop Markdown emphasis marks, collapse whitespace."""
    text = re.sub(r"[*_`]", "", text)  # **bold**, _italic_, `code`
    text = re.sub(r"\s+", " ", text)    # line breaks / double spaces -> one space
    return text.lower().strip()

def _contains(text:str, phrase:str) -> bool:
    """whole-word, case-insensitive match, after normalising both sides"""
    pattern = r"(?<!\w)" + re.escape(_normalise(phrase)) + r"(?!\w)"
    return re.search(pattern, _normalise(text)) is not None

def is_refusal(answer: str) -> bool:
    """True if the answer contains the fixed refusal phrase (outside code blocks)"""
    text = _normalise(strip_code(answer))
    return _normalise(REFUSAL_PHRASE) in text

def check_refuse(answer: str) -> tuple[bool, str]:
    """Pass if the agent used the fixed refusal phrase."""
    if is_refusal(answer):
       return True, "refusal phrase found"
    return False, "refusal phrase not found"

def lead_paragraph(answer: str) -> str:
    """The first prose paragraph of the answer (code removed, Markdown headings skipped)."""
    for block in re.split(r"\n\s*\n", strip_code(answer)):
        lines = [ln for ln in block.strip().splitlines() if not ln.lstrip().startswith("#")]
        text = " ".join(lines).strip()
        if text:
            return text
    return ""

def check_top(answer: str, gold_df: pd.DataFrame) -> tuple[bool, str]:
    """Pass if the first cell of the gold result appears in the answer's first pararagraph."""
    if gold_df.empty:
        return False, "gold result is empty"
    top = gold_df.iloc[0,0]
    if hasattr(top, "item"):
        top = top.item()    # Numpy Scalar -> plain Python in/float/str
    lead = lead_paragraph(answer)

    if isinstance(top, str):
        found = _contains(lead, top)
    else:
        found = number_found(float(top), extract_numbers(lead))

    if found:
        return True, f"top value {top!r} in first paragraph"
    return False, f"top value {top!r} not in first paragraph"

def check_must_include(answer: str, required) -> tuple[bool, str]:
    """Pass if every required item appears in the prose (code blocks excluded).
    An item is a string, or a tuple of alternatives where any one is enough."""
    if not required:
        return True, "nothing required"
    if isinstance(required, str):       # "June" -> ["June"], not ["J", "u", ...]
        required = [required]

    prose = strip_code(answer)
    missing = []
    for item in required:
        options = (item,) if isinstance(item, str) else tuple(item)
        if not any(_contains(prose, opt) for opt in options):
            missing.append(item)

    if missing:
        return False, f"missing required: {missing}"
    return True, f"all required terms found"

GOLD_CHECKS = {"numbers": check_numbers, "top": check_top}

def score_case(case: dict, answer: dict, gold_df: pd.DataFrame | None) -> tuple[bool, str]:
    """Score one agent answer against one eval case. Pure: no database, no API."""
    check = case["check"]

    if check == "refuse":
        passed, reason = check_refuse(answer)
    elif check in GOLD_CHECKS:
        if gold_df is None:
            raise ValueError(f"{case['id']}: check '{check}' needa a gold result")
        if is_refusal(answer):
            passed, reason = False, "false refusal: answerable question was refused"
        else:
            passed, reason = GOLD_CHECKS[check](answer, gold_df)
    else:
        raise ValueError(f"{case['id']}: unknown check '{check}")

    mi_passed, mi_reason = check_must_include(answer, case.get("must_include"))
    reasons = [reason] if mi_reason == "nothing required" else [reason, mi_reason]
    return passed and mi_passed, "; ".join(reasons)

def query_has_gold(df: pd.DataFrame | None, check: str, gold_df: pd.DataFrame) -> bool:
    """Does one executed query's result contain the gold answers?"""
    if df is None or df.empty or gold_df.empty:
        return False
    if check == "numbers":
        found = gold_numbers(df)
        return all(number_found(g, found) for g in gold_numbers(gold_df))
    if check == "top":
        top = gold_df.iloc[0,0]
        first_row = df.iloc[0]
        if isinstance(top, str):
            return any(isinstance(v, str) and _normalise(v) == _normalise(top) for v in first_row)
        return number_found(float(top), gold_numbers(df.iloc[[0]]))
    return False

def execution_match(case: dict, queries: list, gold_df: pd.DataFrame | None) -> bool |None:
    """Did ANY successful query return the gold answer? None for refuse cases (no gold)."""
    if case["check"] == "refuse":
        return None
    return any(q.ok and query_has_gold(q.data, case["check"], gold_df) for q in queries)

def diagnose(passed: bool, exec_match: bool | None) -> str:
    """Combine the answer score and the execution match into one failure label."""
    if exec_match is None:                      # refuse cases
        return "correct" if passed else "missed_refusal"
    if passed and exec_match:
        return "correct"
    if passed:
        return "pass_unverified"
    if exec_match:
        return "reporting_error"
    return "sql_error"