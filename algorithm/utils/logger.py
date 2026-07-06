"""统一JSON格式日志"""
import json
import logging
from datetime import datetime, timezone

class JsonLogger:
    @staticmethod
    def log(level: str, module: str, event: str, detail: dict, trace_id: str):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "module": module,
            "event": event,
            "detail": detail,
            "trace_id": trace_id
        }
        print(json.dumps(record, ensure_ascii=False))
