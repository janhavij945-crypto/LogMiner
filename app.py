"""
app.py
Implements LogMinerInterface from the Class Diagram: uploadLog(),
viewAnalysis(), exportReport(). This is the Streamlit web dashboard
(FR-06 / Section 4.1 of the SRS).

Run with:  streamlit run app.py
"""

import os
import tempfile
import streamlit as st
import pandas as pd
import plotly.express as px

from pipeline import LogMinerPipeline

st.set_page_config(page_title="LogMiner", layout="wide")

st.title("🔍 LogMiner — Intelligent Log Analytics & Root Cause Anomaly Detection")
st.caption("Upload a log file to parse it, detect anomalies, and get a ranked root-cause suggestion.")

with st.sidebar:
    st.header("Settings")
    threshold = st.slider("Anomaly score threshold", 0.0, 1.0, 0.6, 0.05)
    st.markdown("---")
    st.markdown("**User:** admin_janhavi")
    st.markdown("Accepted formats: `.log` `.txt` `.csv`")

if "pipeline" not in st.session_state or st.session_state.get("threshold") != threshold:
    st.session_state.pipeline = LogMinerPipeline(threshold=threshold)
    st.session_state.threshold = threshold

uploaded_file = st.file_uploader("Upload a log file", type=["log", "txt", "csv"])

if uploaded_file is not None:
    if st.button("Run Analysis", type="primary"):
        with st.spinner("Processing logs — parsing, detecting anomalies, correlating root cause..."):
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(tmp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            result = st.session_state.pipeline.process_logs(
                uploaded_file.name, tmp_path, uploaded_file.size
            )
            st.session_state.last_result = result
            st.session_state.last_file_name = uploaded_file.name

if st.session_state.get("last_result"):
    result = st.session_state.last_result

    if not result["success"]:
        st.error(result["error"])
    else:
        st.success(f"Analysis complete — status: {st.session_state.pipeline.status}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Parsed entries", result["parsed_entries"])
        c2.metric("Skipped lines", result["skipped_lines"])
        c3.metric("Distinct templates", result["template_count"])
        c4.metric("Anomalous windows", len(result["flagged_windows"]))

        st.subheader("📈 Timeline — Event Volume & Error Rate")
        windows_df = pd.DataFrame(result["windows"])
        if not windows_df.empty:
            windows_df["is_anomaly"] = windows_df["anomaly_score"] >= threshold
            fig = px.bar(
                windows_df,
                x="window_start",
                y="event_count",
                color="is_anomaly",
                color_discrete_map={True: "#d62728", False: "#1f77b4"},
                labels={"window_start": "Time window", "event_count": "Events", "is_anomaly": "Anomaly"},
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(windows_df[["window_start", "event_count", "error_count", "error_rate", "anomaly_score"]])

        st.subheader("🚨 Suggested Root Causes")
        if not result["incidents"]:
            st.info("No incidents were detected above the current threshold. Try lowering it in the sidebar.")
        else:
            for i, inc in enumerate(result["incidents"], start=1):
                with st.expander(f"Incident {i} — {inc['severity']} severity — {inc['root_cause_time']}"):
                    st.write(inc["root_cause_msg"])
                    if inc["evidence"]:
                        st.write("**Evidence:**")
                        for ev in inc["evidence"]:
                            st.write(f"- {ev}")

        st.subheader("📄 Export")
        if st.button("Export Incident Report (PDF)"):
            pdf_path = st.session_state.pipeline.export_report(
                result["file_id"], st.session_state.last_file_name, result
            )
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download Report", f, file_name=os.path.basename(pdf_path), mime="application/pdf"
                )
else:
    st.info("Upload a log file and click **Run Analysis** to begin.")
