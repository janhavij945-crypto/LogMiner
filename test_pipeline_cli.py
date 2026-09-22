"""
test_pipeline_cli.py
End-to-end smoke test of LogMinerPipeline without the Streamlit UI.
Run:  python test_pipeline_cli.py
"""

import os
from pipeline import LogMinerPipeline

LOG_FILE = "sample_server_log.txt"

if os.path.exists("logminer.db"):
    os.remove("logminer.db")

pipeline = LogMinerPipeline(threshold=0.6)
size = os.path.getsize(LOG_FILE)
result = pipeline.process_logs(LOG_FILE, LOG_FILE, size)

assert result["success"], result.get("error")

print("STATUS:", pipeline.status)
print("Parsed entries:", result["parsed_entries"])
print("Skipped lines:", result["skipped_lines"])
print("Templates:", result["template_count"])
print("Windows:", len(result["windows"]))
print("Flagged windows:", len(result["flagged_windows"]))
print("Incidents:", len(result["incidents"]))

for i, inc in enumerate(result["incidents"], start=1):
    print(f"\nIncident {i} [{inc['severity']}] @ {inc['root_cause_time']}")
    print(" ", inc["root_cause_msg"])
    for ev in inc["evidence"]:
        print("   -", ev)

pdf_path = pipeline.export_report(result["file_id"], LOG_FILE, result)
print("\nReport written to:", pdf_path)
assert os.path.exists(pdf_path)
print("\nSMOKE TEST PASSED")
