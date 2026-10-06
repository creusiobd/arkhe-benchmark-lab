"""Optional synchronous audit export; no transport or queue dependencies."""
import json
from pathlib import Path


class JSONLExporter:
    def __init__(self, path, max_payload_bytes=65536):
        if max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")
        self.path = Path(path)
        self.max_payload_bytes = max_payload_bytes

    def export(self, decision):
        data = decision.model_dump(mode="json")
        line = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        if len(line.encode("utf-8")) > self.max_payload_bytes:
            raise ValueError("audit payload exceeds configured maximum")
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
