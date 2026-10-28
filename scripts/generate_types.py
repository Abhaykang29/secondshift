"""Generate frontend/src/api/types.ts from the Pydantic domain schemas.

Why: the frontend contract must never drift from the backend contract
(spec section 17, rule 9). types.ts is GENERATED - do not edit it by hand.
Run: `make types`. The drift test (tests/test_schema_drift.py) regenerates
the content in memory and fails if the committed file differs in any field.
"""

import enum as enum_mod
import inspect
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import secondshift.domain.checkup as checkup_mod  # noqa: E402
import secondshift.domain.enums as enums_mod  # noqa: E402
import secondshift.domain.eval as eval_mod  # noqa: E402
import secondshift.domain.hazards as hazards_mod  # noqa: E402
import secondshift.domain.rules as rules_mod  # noqa: E402
import secondshift.domain.watch as watch_mod  # noqa: E402
from pydantic import BaseModel  # noqa: E402

OUT = Path(__file__).parent.parent / "frontend" / "src" / "api" / "types.ts"
MODULES = [checkup_mod, hazards_mod, rules_mod, watch_mod, eval_mod]


def _collect_models() -> list[type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for module in MODULES:
        for _, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == module.__name__
            ):
                models[obj.__name__] = obj
    return [models[name] for name in sorted(models)]


def _collect_enums() -> list[type[enum_mod.Enum]]:
    found: list[type[enum_mod.Enum]] = []
    for _, obj in vars(enums_mod).items():
        if (
            inspect.isclass(obj)
            and issubclass(obj, enum_mod.Enum)
            and obj.__module__ == enums_mod.__name__
        ):
            found.append(obj)
    return found


def _ts_type(schema: dict[str, Any], defs: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "enum" in schema:
        parts = [json.dumps(v) if isinstance(v, str) else str(v) for v in schema["enum"]]
        return " | ".join(parts)
    if "anyOf" in schema:
        parts: list[str] = []
        for s in schema["anyOf"]:
            part = _ts_type(s, defs)
            if part not in parts:
                parts.append(part)
        return " | ".join(parts)
    if "allOf" in schema and len(schema["allOf"]) == 1:
        return _ts_type(schema["allOf"][0], defs)
    t = schema.get("type")
    if t == "string":
        return "string"
    if t in ("integer", "number"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"
    if t == "array":
        if "prefixItems" in schema:  # fixed-length tuple, e.g. bbox / roi
            inner = ", ".join(_ts_type(s, defs) for s in schema["prefixItems"])
            return f"[{inner}]"
        items = schema.get("items", {})
        return f"{_ts_type(items, defs)}[]"
    if t == "object":
        addl = schema.get("additionalProperties")
        if isinstance(addl, dict):
            return f"Record<string, {_ts_type(addl, defs)}>"
        return "Record<string, unknown>"
    if "properties" in schema:  # inline object
        return "Record<string, unknown>"
    return "unknown"


def render_types() -> str:
    """Render the full types.ts content from the current domain schemas."""
    lines: list[str] = [
        "/**",
        " * GENERATED from the Pydantic domain schemas by scripts/generate_types.py.",
        " * Do not edit by hand - run `make types`. The drift test fails on any diff.",
        " * Frontend-only response shapes live in ./extra.ts.",
        " */",
        "",
    ]
    for cls in _collect_enums():
        values = []
        for member in cls:
            v = member.value
            values.append(json.dumps(v) if isinstance(v, str) else str(v))
        lines.append(f"export type {cls.__name__} = {' | '.join(values)};")
    lines.append("")
    for model in _collect_models():
        schema = model.model_json_schema()
        defs: dict[str, Any] = schema.get("$defs", {})
        props: dict[str, Any] = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append(f"export interface {model.__name__} {{")
        for field_name, field_schema in props.items():
            ts = _ts_type(field_schema, defs)
            opt = "" if field_name in required else "?"
            lines.append(f"  {field_name}{opt}: {ts};")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Write the generated types to frontend/src/api/types.ts."""
    OUT.write_text(render_types())
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
