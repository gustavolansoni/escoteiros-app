import json
from pathlib import Path
from typing import Dict, Optional

STATE_PATH = Path("data/last_seen.json")


class LastSeenStore:
    def __init__(self, state_path: Path = STATE_PATH):
        self.state_path = state_path

    def load(self) -> Dict[str, Optional[str]]:
        if not self.state_path.exists():
            return {"article_id": None, "updated_at": None}

        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        return {
            "article_id": raw.get("article_id"),
            "updated_at": raw.get("updated_at"),
        }

    def save(self, article_id: int, updated_at: str) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"article_id": article_id, "updated_at": updated_at}
        self.state_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
