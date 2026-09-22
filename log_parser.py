"""
log_parser.py
Implements the LogParser class from the Class Diagram: extractPattern().
Converts one raw log line into a structured record (timestamp, severity,
source, message) and derives a "template" by replacing variable tokens
(numbers, IDs, IPs, UUIDs) with placeholders, so repeated events of the same
type collapse into one template (FR-02 in the SRS).
"""

import re
import hashlib

# Matches lines like:
# 2026-08-23 10:15:32 ERROR [OrderService] Payment gateway timeout after 5000ms (order_id=88213)
LOG_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+"
    r"\[?(?P<source>[\w\-.]+)\]?\s*[:\-]?\s*"
    r"(?P<message>.*)$"
)

# Tokens to generalise when building a template
_VAR_PATTERNS = [
    (re.compile(r"\b\d+\.\d+\.\d+\.\d+\b"), "<IP>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d+ms\b"), "<MS>"),
    (re.compile(r"\b\d+\b"), "<NUM>"),
]


class LogParser:
    """extractPattern(line) -> structured dict | None"""

    def __init__(self, pattern: re.Pattern = LOG_LINE_PATTERN):
        self.pattern = pattern

    def extract_pattern(self, raw_line: str):
        raw_line = raw_line.strip()
        if not raw_line:
            return None
        match = self.pattern.match(raw_line)
        if not match:
            return None
        data = match.groupdict()
        data["template_id"], data["template_str"] = self._build_template(data["message"])
        return data

    def _build_template(self, message: str):
        template = message
        for pattern, placeholder in _VAR_PATTERNS:
            template = pattern.sub(placeholder, template)
        template_id = hashlib.md5(template.encode()).hexdigest()[:10]
        return template_id, template
