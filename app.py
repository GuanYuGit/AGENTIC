import streamlit as st
import subprocess
import sys
import json
from pathlib import Path

# Path to your orchestrator
PROJECT_ROOT = Path("/Users/guanyu/AGENTIC")
ORCHESTRATOR = PROJECT_ROOT / "orchestrator.py"
FINAL_SUMMARY_OUTPUT = PROJECT_ROOT / "news_validity_summary.json"

st.set_page_config(page_title="Fake News Analyzer", page_icon="📰", layout="wide")

# --- Chat UI state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("📰 Fake News Analyzer")
st.write("Enter a news article URL and get a validity analysis powered by your agents.")

# --- Chat rendering ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- User input ---
if url := st.chat_input("Paste a news article URL..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": url})
    with st.chat_message("user"):
        st.markdown(url)

    # Run orchestrator in background
    with st.chat_message("assistant"):
        with st.spinner("Analyzing the article... this may take a while ⏳"):
            completed = subprocess.run(
                [sys.executable, str(ORCHESTRATOR), url],
                capture_output=True,
                text=True,
            )

            if completed.returncode != 0:
                error_msg = f"❌ Error:\n{completed.stderr}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                # Load the final summary JSON
                try:
                    with open(FINAL_SUMMARY_OUTPUT, "r", encoding="utf-8") as f:
                        summaries = json.load(f)
                    entry = summaries.get(url, {})
                    summary_text = entry.get("summary") or entry.get("error") or "No summary available."

                    st.markdown(f"**Summary for {url}:**\n\n{summary_text}")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": summary_text}
                    )
                except Exception as e:
                    err = f"⚠️ Could not load summary: {e}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
