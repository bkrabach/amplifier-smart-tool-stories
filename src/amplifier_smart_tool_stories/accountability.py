"""Executable validation of disclosed transformations; semantic coverage needs review."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from .errors import require


def validate_disclosures(result, story, operation):
    changes = result.get("changes")
    require(isinstance(changes, dict) and isinstance(changes.get("summary"), str), "Submit a change summary.")
    for field in ("material_changes", "omissions", "assumptions"):
        require(
            isinstance(changes.get(field), list) and all(isinstance(v, str) for v in changes[field]),
            f"Submit {field} as text entries.",
        )
    if operation.get("revision_id") and result.get("action") == "revise":
        require(bool(changes["summary"].strip()), "A revision needs a comparison summary.")
    calculations = result.get("calculations")
    require(isinstance(calculations, list) and len(calculations) <= 50, "Submit at most 50 calculations.")
    evidence = {e["id"]: e for e in result.get("evidence", [])}
    seen = set()
    for item in calculations:
        require(isinstance(item, dict), "Calculation must be an object.")
        require(isinstance(item.get("id"), str) and item["id"] not in seen, "Calculation IDs must be unique.")
        seen.add(item["id"])
        inputs = item.get("inputs")
        require(isinstance(inputs, list) and 1 <= len(inputs) <= 20, "Calculation needs 1–20 inputs.")
        values = []
        for operand in inputs:
            require(isinstance(operand, dict), "Calculation input must be an object.")
            fact = evidence.get(operand.get("evidence_id"))
            value = operand.get("value")
            require(
                fact is not None and isinstance(value, str) and len(value) <= 100,
                "Calculation input needs evidence and numeric text.",
            )
            require(
                re.fullmatch(r"-?\d+(?:\.\d+)?", value) is not None,
                "Use plain decimal inputs without separators.",
            )
            numbers = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", fact["quote"].replace(",", ""))
            require(value in numbers, "Calculation input is not present in its cited quote.")
            values.append(Decimal(value))
        places = item.get("decimal_places")
        require(type(places) is int and 0 <= places <= 12, "decimal_places must be 0–12.")
        require(isinstance(item.get("unit"), str), "Calculation needs a unit label.")
        name = item.get("operation")
        require(
            name in {"sum", "difference", "product", "ratio", "percent_change"},
            "Unsupported calculation operation.",
        )
        if name != "sum":
            require(len(values) == 2, "This calculation requires exactly two ordered inputs.")
        with localcontext() as ctx:
            ctx.prec = 250
            if name == "sum":
                expected = sum(values)
            elif name == "difference":
                expected = values[0] - values[1]
            elif name == "product":
                expected = values[0] * values[1]
            else:
                denominator = values[0] if name == "percent_change" else values[1]
                require(denominator != 0, "Calculation divides by zero.")
                expected = (
                    ((values[1] - values[0]) / denominator * 100)
                    if name == "percent_change"
                    else values[0] / denominator
                )
            try:
                stated = Decimal(item["result"])
                require(
                    stated.is_finite()
                    and stated == expected.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP),
                    "Calculation result does not match its inputs and rounding.",
                )
            except (InvalidOperation, KeyError, TypeError, ValueError):
                require(False, "Invalid calculation result.")
        item["verification"] = (
            "passed: decimal arithmetic; quoted inputs; semantic interpretation requires model review"
        )


def disclosure_hash(result):
    import json

    from .artifacts import digest

    return digest(json.dumps({k: result.get(k) for k in ("changes", "calculations")}, sort_keys=True))
