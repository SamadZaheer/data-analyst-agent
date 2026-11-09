"""Scoring functions for the evaluation. No API calls, testable logic."""
import re
import numpy as np
import pandas as pd

# A number: optional minus (not when a digit comes right before it, as in "2007-2015"),
# digits with optional thousands commas, optional decimals.
NUMBER_RE = re.compile(r"(?<!\d)-?\d+(?:,\d{3})*(?:\.\d+)?")
CODE_BLOCK_RE = re.compile(r"```.*?(?:```|$)", re.DOTALL)  # closed or unclosed fences

def strip_code(answer:str) -> str:
    """Remove fenced code blocks, so numbers in the echoed SQL don't count."""
    return CODE_BLOCK_RE.sub(" ", answer or "")

def extract_numbers(text: str) -> list[float]:
    """All numbers in the text, wiht thousands comma removed."""
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
    """Integers must match exactly; decimals may be rounded to 0, 1 or 3 places."""
    if gold == int(gold):
        return gold in found
    return any(round(gold, d) == n for d in (0, 1, 2) for n in found)

def check_numbers(answer: str, gold_df: pd.DataFrame) -> tuple[bool, str]:
    """Pass if every gold number appears in the answer's prose (code block excluded)."""
    found = extract_numbers(strip_code(answer))
    missing = [g for g in gold_numbers(gold_df) if not number_found(g, found)]
    if missing:
        return False, f"missing numbers: {missing}"
    return True, f"all gold numbers found"
