"""
PURPOSE: The app's front door: a resident chats with the service desk, with a ticket preview panel beside the chat.
LAYER:   Integration/Experience
SESSION: S00 (resident chat page and ticket preview card from S02, tool calls from S03)
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

from src.tools.work_order_tools import reply_with_tools  # noqa: E402
from src.intelligence.ticket_card import fill_ticket_card  # noqa: E402

st.set_page_config(page_title="Property Service Desk", layout="wide")

product = os.getenv("PRODUCT_NAME") or "Property Service Desk"
st.title(product)
st.caption("Contoso Living (fictional) · resident service desk · v0.2 in progress")


def show_tool_calls(log: list[dict]) -> None:
    """Show every tool call of one reply: name, arguments, result and seconds."""
    with st.expander("Tool calls"):
        if not log:
            st.caption("No tool calls this turn.")
        for call in log:
            st.markdown(f"**{call['name']}** ({call['seconds']} s)")
            st.code(f"arguments: {call['arguments']}\nresult:    {call['result']}")


# The conversation the app keeps and resends every turn, and the input tokens and tool calls of each reply.
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.input_tokens = []
    st.session_state.tool_logs = []
if "tool_logs" not in st.session_state:  # a chat started before S03 has no tool log yet
    st.session_state.tool_logs = [[] for _ in st.session_state.input_tokens]

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
    if st.session_state.get("card_failed"):
        st.caption("The card was not updated this turn.")

with chat_column:
    turn = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(f"Input tokens this turn: {st.session_state.input_tokens[turn]}")
                show_tool_calls(st.session_state.tool_logs[turn])
                turn += 1

    live_turn = st.container()  # the new turn is drawn here, above the input box, while the reply is prepared
    text = st.chat_input("Describe your problem")
    if text:
        st.session_state.messages.append({"role": "user", "content": text})
        try:
            with live_turn:
                with st.chat_message("user"):
                    st.write(text)
                with st.chat_message("assistant"):
                    # Tool turns do not stream: the app may run functions between model calls, so the reply comes whole.
                    with st.spinner("Looking that up..."):
                        reply, tool_log, input_tokens = reply_with_tools(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.input_tokens.append(input_tokens)
            st.session_state.tool_logs.append(tool_log)
            try:
                with st.spinner("Updating the ticket preview..."):
                    card, card_tokens = fill_ticket_card(st.session_state.messages)
                st.session_state.card = card
                st.session_state.card_tokens = card_tokens
                st.session_state.card_failed = False
            except Exception:  # the reply is kept; only the card misses this turn, and the earlier card stays
                st.session_state.card_failed = True
            st.rerun()
        except Exception as error:  # keep the page running and show the problem plainly
            st.session_state.messages.pop()  # drop the unanswered message so the conversation stays in step
            st.error(f"{type(error).__name__}: {error}")
            st.caption("Copy this message into your tutor chat after 'stuck:'.")
