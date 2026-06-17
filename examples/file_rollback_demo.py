from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.core.db import initialize_database
from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.core.snapshot import SnapshotEngine


def main() -> None:
    root = Path.cwd()
    demo_path = root / "demo.txt"

    initialize_database(root)

    if not demo_path.exists():
        demo_path.write_text("original demo content\n", encoding="utf-8")

    action = Action(
        action_type="file.write",
        target="demo.txt",
        status="approved",
        params={"content": "updated demo content"},
    )

    log = ActionLog(root=root)
    log.add_action(action)

    snapshot = SnapshotEngine(root=root).create_snapshot(action)
    log.add_snapshot(snapshot)

    demo_path.write_text("updated demo content\n", encoding="utf-8")

    print(f"Action ID: {action.id}")
    print("demo.txt has been modified.")
    print("Run this to undo it:")
    print("runewall rollback --last")


if __name__ == "__main__":
    main()
