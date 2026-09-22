"""
pipeline.py
Implements LogMinerPipeline from the Class Diagram: processLogs(),
detectAnomalies(), analyzeRootCause(). Orchestrates LogProcessor,
AnomalyDetector, RootCauseAnalyzer, ReportGenerator and LogRepository,
exactly matching the "aggregates" relationships in the Class Diagram and the
call order in the Sequence Diagram.
"""

from log_processor import LogProcessor
from anomaly_detector import AnomalyDetector
from root_cause_analyzer import RootCauseAnalyzer
from report_generator import ReportGenerator
from log_repository import LogRepository


class LogMinerPipeline:
    def __init__(self, threshold: float = 0.6):
        self.status = "Idle"
        self.processor = LogProcessor()
        self.detector = AnomalyDetector(threshold=threshold)
        self.analyzer = RootCauseAnalyzer()
        self.reporter = ReportGenerator()
        self.repository = LogRepository()

    def process_logs(self, file_name: str, file_path: str, file_size_bytes: int):
        self.status = "Validating"
        ok, message = self.processor.validate_file(file_name, file_size_bytes)
        if not ok:
            self.status = "Failed"
            return {"success": False, "error": message}

        file_id = self.repository.save_log(file_name, file_path)

        self.status = "Parsing"
        entries, templates, skipped = self.processor.parse_log(file_path)
        self.repository.save_entries(file_id, entries)
        self.repository.save_templates(file_id, templates)
        self.repository.update_file_stats(file_id, len(entries), skipped, "Parsed")

        if not entries:
            self.status = "Failed"
            return {"success": False, "error": "No parseable log lines were found."}

        anomaly_result = self.detect_anomalies(file_id, entries)
        incidents = self.analyze_root_cause(file_id, anomaly_result["flagged"])

        self.status = "Complete"
        return {
            "success": True,
            "file_id": file_id,
            "total_lines": len(entries) + skipped,
            "parsed_entries": len(entries),
            "skipped_lines": skipped,
            "template_count": len(templates),
            "windows": anomaly_result["all_windows"],
            "flagged_windows": anomaly_result["flagged"],
            "incidents": incidents,
        }

    def detect_anomalies(self, file_id: int, entries: list):
        self.status = "Detecting anomalies"
        all_windows, flagged = self.detector.detect_anomaly(entries)
        if flagged:
            self.repository.save_anomalies(file_id, flagged)
        return {"all_windows": all_windows, "flagged": flagged}

    def analyze_root_cause(self, file_id: int, flagged_windows: list):
        self.status = "Analyzing root cause"
        incidents = self.analyzer.analyze_root_cause(flagged_windows)
        for inc in incidents:
            self.repository.save_incident(file_id, inc)
        return incidents

    def export_report(self, file_id: int, file_name: str, result: dict) -> str:
        stats = {
            "Total lines": result["total_lines"],
            "Parsed entries": result["parsed_entries"],
            "Skipped lines": result["skipped_lines"],
            "Distinct templates": result["template_count"],
            "Anomalous windows": len(result["flagged_windows"]),
            "Incidents": len(result["incidents"]),
        }
        report = self.reporter.generate_report(file_name, stats, result["incidents"])
        pdf_path = self.reporter.export_pdf(report)
        self.repository.save_report(file_id, pdf_path)
        return pdf_path
