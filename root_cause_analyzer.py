"""
root_cause_analyzer.py
Implements RootCauseAnalyzer from the Class Diagram: analyzeRootCause(), generateInsight().
Covers FR-05 (Root-Cause Correlation) from the SRS: groups anomalies that
occur close together in time, then ranks candidate root-cause events by
earliest occurrence and severity/frequency.
"""

from datetime import datetime, timedelta

INCIDENT_GAP_MINUTES = 5


class RootCauseAnalyzer:
    def __init__(self, incident_gap_minutes: int = INCIDENT_GAP_MINUTES):
        self.incident_gap = timedelta(minutes=incident_gap_minutes)

    def _to_dt(self, s):
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

    def group_incidents(self, flagged_windows: list):
        """Groups anomalous windows that are within `incident_gap` of each other."""
        if not flagged_windows:
            return []

        windows = sorted(flagged_windows, key=lambda w: w["window_start"])
        incidents = [[windows[0]]]

        for w in windows[1:]:
            prev_end = self._to_dt(incidents[-1][-1]["window_end"])
            cur_start = self._to_dt(w["window_start"])
            if cur_start - prev_end <= self.incident_gap:
                incidents[-1].append(w)
            else:
                incidents.append([w])
        return incidents

    def analyze_root_cause(self, flagged_windows: list):
        """Returns a ranked list of incident dicts with root-cause insight."""
        incident_groups = self.group_incidents(flagged_windows)
        results = []
        for group in incident_groups:
            # earliest, most severe window = likely trigger
            trigger = max(group, key=lambda w: (w["error_rate"], -self._to_dt(w["window_start"]).timestamp()))
            insight = self.generate_insight(group, trigger)
            results.append(
                {
                    "root_cause_msg": insight["summary"],
                    "root_cause_time": trigger["window_start"],
                    "severity": insight["severity"],
                    "evidence": insight["evidence"],
                    "window_count": len(group),
                }
            )
        # rank by severity score then earliest time
        results.sort(key=lambda r: (-{"High": 2, "Medium": 1, "Low": 0}[r["severity"]], r["root_cause_time"]))
        return results

    def generate_insight(self, group: list, trigger: dict):
        top_templates = trigger.get("top_templates", [])
        evidence = [f"template {tid} occurred {count}x" for tid, count in top_templates]

        if trigger["error_rate"] >= 0.5:
            severity = "High"
        elif trigger["error_rate"] >= 0.2:
            severity = "Medium"
        else:
            severity = "Low"

        summary = (
            f"Spike starting at {trigger['window_start']} "
            f"({trigger['error_count']} errors / {trigger['event_count']} events, "
            f"{trigger['error_rate']*100:.1f}% error rate) is the likely trigger "
            f"for an incident spanning {len(group)} window(s)."
        )
        return {"summary": summary, "severity": severity, "evidence": evidence}
