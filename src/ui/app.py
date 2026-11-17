"""
PURPOSE: The app's front door: a resident chats with the service desk, with a ticket preview panel beside the chat.
LAYER:   Integration/Experience
SESSION: S00 (resident chat page from S02)
Run:     streamlit run src/ui/app.py   (from the capstone folder, virtual environment active)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st  # noqa: E402

from src.intelligence.resident_chat import reply_to_resident  # noqa: E402

st.set_page_config(page_title="Property Service Desk", layout="wide")

product = os.getenv("PRODUCT_NAME") or "Property Service Desk"
st.title(product)
st.caption("Contoso Living (fictional) · resident service desk · v0.2 in progress")

# The conversation the app keeps and resends every turn, and the input tokens of each reply.
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.input_tokens = []

chat_column, ticket_column = st.columns([3, 1])

with ticket_column:
    st.subheader("Ticket preview")
    st.caption("Empty for now. The triage card comes later.")

with chat_column:
    turn = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(f"Input tokens this turn: {st.session_state.input_tokens[turn]}")
                turn += 1

    text = st.chat_input("Describe your problem")
    if text:
        st.session_state.messages.append({"role": "user", "content": text})
        try:
            with st.spinner("The service desk is replying..."):
                reply, input_tokens = reply_to_resident(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.input_tokens.append(input_tokens)
            st.rerun()
        except Exception as error:  # keep the page running and show the problem plainly
            st.session_state.messages.pop()  # drop the unanswered message so the conversation stays in step
            st.error(f"{type(error).__name__}: {error}")
            st.caption("Copy this message into your tutor chat after 'stuck:'.")
