"""
PURPOSE: The app's front door: a resident chats with the service desk, with a ticket preview panel beside the chat.
LAYER:   Integration/Experience
SESSION: S00 (resident chat page and ticket preview card from S02)
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

from src.intelligence.resident_chat import stream_reply_to_resident  # noqa: E402
from src.intelligence.ticket_card import fill_ticket_card  # noqa: E402

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
    card = st.session_state.get("card")
    if card:
        st.markdown(
            f"**Category:** {card['category']}  \n**Urgency:** {card['urgency']}  \n"
            f"**Unit:** {card['unit']}  \n**Summary:** {card['summary']}"
        )
        st.caption(f"Input tokens for the card: {st.session_state.card_tokens}")
    else:
        st.caption("The triage card appears after the first reply.")

with chat_column:
    turn = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(f"Input tokens this turn: {st.session_state.input_tokens[turn]}")
                turn += 1

    live_turn = st.container()  # the new turn is drawn here, above the input box, while the reply streams in
    text = st.chat_input("Describe your problem")
    if text:
        st.session_state.messages.append({"role": "user", "content": text})
        try:
            with live_turn:
                with st.chat_message("user"):
                    st.write(text)
                with st.chat_message("assistant"):
                    result = {}
                    # write_stream shows each piece as it arrives and returns the whole reply when it ends.
                    reply = st.write_stream(stream_reply_to_resident(st.session_state.messages, result))
            conversation = st.session_state.messages + [{"role": "assistant", "content": reply}]
            with st.spinner("Updating the ticket preview..."):
                card, card_tokens = fill_ticket_card(conversation)
            st.session_state.messages = conversation
            st.session_state.input_tokens.append(result["input_tokens"])
            st.session_state.card = card
            st.session_state.card_tokens = card_tokens
            st.rerun()
        except Exception as error:  # keep the page running and show the problem plainly
            st.session_state.messages.pop()  # drop the unanswered message so the conversation stays in step
            st.error(f"{type(error).__name__}: {error}")
            st.caption("Copy this message into your tutor chat after 'stuck:'.")
