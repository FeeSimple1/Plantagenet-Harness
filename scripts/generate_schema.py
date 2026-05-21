"""Regenerate data/schema/state.schema.json from the Pydantic state model.

Keeps the published JSON Schema in lockstep with `plantagenet.state.GameState`.
Run after changing the state model.
"""

from __future__ import annotations

import json
from pathlib import Path

from plantagenet.state import GameState

OUT = Path("src/plantagenet/data/schema/state.schema.json")


def main() -> None:
    schema = GameState.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://plantagenet-harness/state.schema.json"
    schema["title"] = "Plantagenet game state"
    OUT.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {OUT} ({len(schema.get('$defs', {}))} definitions)")


if __name__ == "__main__":
    main()
