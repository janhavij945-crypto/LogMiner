"""
log_processor.py
Implements LogProcessor from the Class Diagram: parseLog(), normalizeLog().
Handles FR-01 (Ingestion & Validation) and drives LogParser over every line,
building the structured entry list + template frequency table.
"""

import os
from log_parser import LogParser

ALLOWED_EXTENSIONS = {".log", ".txt", ".csv"}
MAX_FILE_SIZE_MB = 50


class LogProcessor:
    def __init__(self):
        self.parser = LogParser()

    def validate_file(self, file_name: str, file_size_bytes: int):
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type '{ext}'. Allowed: .log, .txt, .csv"
        if file_size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            return False, f"File exceeds the {MAX_FILE_SIZE_MB}MB limit."
        return True, "OK"

    def parse_log(self, file_path: str):
        """Reads the raw file and returns (entries, templates, skipped_count)."""
        entries = []
        templates = {}
        skipped = 0

        with open(file_path, "r", errors="ignore") as f:
            for line_no, raw_line in enumerate(f, start=1):
                parsed = self.parser.extract_pattern(raw_line)
                if parsed is None:
                    skipped += 1
                    continue

                entries.append(
                    {
                        "line_no": line_no,
                        "timestamp": parsed["timestamp"],
                        "severity": parsed["severity"].upper(),
                        "source": parsed["source"],
                        "message": parsed["message"],
                        "template_id": parsed["template_id"],
                    }
                )

                tid = parsed["template_id"]
                if tid not in templates:
                    templates[tid] = {"pattern": parsed["template_str"], "frequency": 0}
                templates[tid]["frequency"] += 1

        normalized = self.normalize_log(entries)
        return normalized, templates, skipped

    def normalize_log(self, entries: list):
        """Sorts entries chronologically and fills any missing severities."""
        for e in entries:
            if not e["severity"]:
                e["severity"] = "INFO"
        entries.sort(key=lambda e: e["timestamp"])
        return entries
