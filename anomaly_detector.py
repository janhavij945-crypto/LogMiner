"""
anomaly_detector.py
Implements AnomalyDetector from the Class Diagram: detectAnomaly(), calculateScore().
Covers FR-03 (Feature Extraction) and FR-04 (Anomaly Detection) from the SRS.

Approach:
  1. Bucket parsed log entries into fixed-size time windows (default 60s).
  2. For each window compute: event_count, error_count, error_rate,
     and frequency of the top log templates.
  3. Fit an unsupervised Isolation Forest over the windows' numeric features.
  4. Windows whose anomaly score crosses `threshold` are flagged.
"""

from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

WINDOW_SECONDS = 60
ERROR_SEVERITIES = {"ERROR", "CRITICAL", "FATAL"}


class AnomalyDetector:
    def __init__(self, threshold: float = 0.6, window_seconds: int = WINDOW_SECONDS):
        self.threshold = threshold
        self.window_seconds = window_seconds

    def _window_key(self, ts_str: str):
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        epoch = int(ts.timestamp())
        bucket = epoch - (epoch % self.window_seconds)
        return bucket

    def build_feature_windows(self, entries: list):
        buckets = defaultdict(lambda: {"event_count": 0, "error_count": 0, "templates": defaultdict(int)})

        for e in entries:
            key = self._window_key(e["timestamp"])
            buckets[key]["event_count"] += 1
            if e["severity"] in ERROR_SEVERITIES:
                buckets[key]["error_count"] += 1
            buckets[key]["templates"][e["template_id"]] += 1

        rows = []
        for bucket_start, stats in sorted(buckets.items()):
            error_rate = stats["error_count"] / stats["event_count"] if stats["event_count"] else 0
            top_templates = sorted(stats["templates"].items(), key=lambda kv: kv[1], reverse=True)[:3]
            rows.append(
                {
                    "window_start": datetime.fromtimestamp(bucket_start).strftime("%Y-%m-%d %H:%M:%S"),
                    "window_end": datetime.fromtimestamp(bucket_start + self.window_seconds).strftime("%Y-%m-%d %H:%M:%S"),
                    "event_count": stats["event_count"],
                    "error_count": stats["error_count"],
                    "error_rate": round(error_rate, 4),
                    "top_templates": top_templates,
                }
            )
        return pd.DataFrame(rows)

    def calculate_score(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        if feature_df.empty:
            feature_df["anomaly_score"] = []
            return feature_df

        X = feature_df[["event_count", "error_count", "error_rate"]].values

        # Isolation Forest needs >=2 samples; fall back to a rule-based score
        # for very small demo files.
        if len(X) < 2:
            feature_df["anomaly_score"] = feature_df["error_rate"]
            return feature_df

        model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
        model.fit(X)
        raw_scores = -model.score_samples(X)  # higher = more anomalous
        # normalise to 0..1 for a human-readable score
        normalized = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)
        feature_df["anomaly_score"] = np.round(normalized, 4)
        return feature_df

    def detect_anomaly(self, entries: list):
        """Returns list[dict] of windows flagged as anomalous."""
        feature_df = self.build_feature_windows(entries)
        scored_df = self.calculate_score(feature_df)
        flagged = scored_df[scored_df["anomaly_score"] >= self.threshold]
        return scored_df.to_dict("records"), flagged.to_dict("records")
