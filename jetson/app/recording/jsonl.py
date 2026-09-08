from __future__ import annotations

import json
from pathlib import Path


class JsonlRecorder:
    def __init__(self, directory: str | Path, enabled: bool = True,
                 max_bytes: int = 10_485_760, backup_count: int = 3):
        self.directory = Path(directory)
        self.enabled = enabled
        self.path = self.directory / "session.jsonl"
        self.max_bytes, self.backup_count = max_bytes, backup_count

    def _rotate(self) -> None:
        if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
            return
        oldest = self.path.with_suffix(f".jsonl.{self.backup_count}")
        if oldest.exists():
            oldest.unlink()
        for index in range(self.backup_count - 1, 0, -1):
            source = self.path.with_suffix(f".jsonl.{index}")
            if source.exists():
                source.rename(self.path.with_suffix(f".jsonl.{index + 1}"))
        self.path.rename(self.path.with_suffix(".jsonl.1"))

    def write(self, message: dict) -> None:
        if not self.enabled:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self._rotate()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, separators=(",", ":")) + "\n")


def replay(path: str | Path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)
