"""Dice roller — parses expressions like 1d20+5, 2d6, 1d20adv, 1d20dis."""
import random
import re


def roll(expr: str) -> dict:
    """Parse and roll a dice expression. Returns a result dict."""
    original = expr.strip()
    expr = original.lower()

    advantage = expr.endswith("adv")
    disadvantage = expr.endswith("dis")
    if advantage or disadvantage:
        expr = expr[:-3].strip()

    match = re.fullmatch(r"(\d*)d(\d+)([+-]\d+)?", expr.replace(" ", ""))
    if not match:
        # Plain number
        try:
            val = int(expr)
            return {"expr": original, "all_rolls": [val], "kept": [val], "modifier": 0, "total": val}
        except ValueError:
            return {"expr": original, "all_rolls": [], "kept": [], "modifier": 0, "total": 0,
                    "error": f"Cannot parse: {original}"}

    count = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if count < 1 or sides < 1:
        return {"expr": original, "all_rolls": [], "kept": [], "modifier": modifier, "total": modifier}

    rolls_a = [random.randint(1, sides) for _ in range(count)]

    if advantage or disadvantage:
        rolls_b = [random.randint(1, sides) for _ in range(count)]
        sum_a, sum_b = sum(rolls_a), sum(rolls_b)
        if advantage:
            kept = rolls_a if sum_a >= sum_b else rolls_b
        else:
            kept = rolls_a if sum_a <= sum_b else rolls_b
        all_rolls = rolls_a + rolls_b
    else:
        kept = rolls_a
        all_rolls = rolls_a

    total = sum(kept) + modifier
    return {
        "expr": original,
        "all_rolls": all_rolls,
        "kept": kept,
        "modifier": modifier,
        "total": total,
        "advantage": advantage,
        "disadvantage": disadvantage,
    }


def format_result(r: dict) -> str:
    if r.get("error"):
        return f"Error: {r['error']}"
    parts = [str(x) for x in r["kept"]]
    s = " + ".join(parts) if len(parts) > 1 else (parts[0] if parts else "0")
    if r["modifier"] > 0:
        s += f" + {r['modifier']}"
    elif r["modifier"] < 0:
        s += f" - {abs(r['modifier'])}"
    label = ""
    if r.get("advantage"):
        label = " (adv)"
    elif r.get("disadvantage"):
        label = " (dis)"
    return f"{r['expr']}{label} = {r['total']}  [{s}]"
