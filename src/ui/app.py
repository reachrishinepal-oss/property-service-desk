"""
PURPOSE: The app's front door: a resident chats with the service desk, with a ticket preview panel beside the chat.
LAYER:   Integration/Experience
SESSION: S00 (resident chat page and ticket preview card from S02, tool calls, rules search and the manager question from S03,
         guardrail outcomes shown as a plain fallback from S04)
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

from src.core.config import get_settings  # noqa: E402
from src.governance.filter_outcomes import FilterStop  # noqa: E402

from src.tools.manager_analytics import TEST_QUESTION, ask_manager_question, built_in_check  # noqa: E402
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


def show_rules_searches(searches: list[dict]) -> None:
    """Show what the rules search looked for and each passage it found, with its file name and score."""
    with st.expander("Rules searched"):
        if not searches:
            st.caption("Not used this turn.")
        for search in searches:
            st.markdown("**Queries:** " + "; ".join(search["queries"]))
            for passage in search["passages"]:
                st.code(f"{passage['file']}  score {passage['score']}\n{passage['text']}", wrap_lines=True)


# The conversation the app keeps and resends every turn, and the input tokens and tool calls of each reply.
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.input_tokens = []
    st.session_state.tool_logs = []
    st.session_state.rules_searches = []
if "rules_searches" not in st.session_state:  # a chat started before S03 has no tool log or rules searches yet
    st.session_state.tool_logs = [[] for _ in st.session_state.input_tokens]
    st.session_state.rules_searches = [[] for _ in st.session_state.input_tokens]

try:
    if not get_settings().vector_store_id:
        st.info("Rules search is off: VECTOR_STORE_ID is missing")
except RuntimeError as error:  # missing settings: show them plainly; the chat below reports the same on first use
    st.error(str(error))

with st.sidebar:
    st.header("Manager question (demo, no sign-in yet)")
    question = st.text_area("Question about the tickets", value=TEST_QUESTION)
    if st.button("Ask"):
        try:
            with st.spinner("The model is writing and running code..."):
                st.session_state.manager = ask_manager_question(question)
                st.session_state.manager_check = built_in_check(question)
        except Exception as error:  # keep the page running and show the problem plainly
            st.session_state.pop("manager", None)
            st.error(f"The question could not be answered: {type(error).__name__}: {error}")
    if "manager" in st.session_state:
        st.markdown(st.session_state.manager["answer"])
        st.caption(f"Input tokens: {st.session_state.manager['input_tokens']}")
        with st.expander("Code the model ran"):
            for code in st.session_state.manager["code"] or ["(no code was run)"]:
                st.code(code, language="python")
        st.subheader("Computed here")
        if st.session_state.manager_check:
            st.json(st.session_state.manager_check)
        else:
            st.caption("No built-in check for this question")

chat_column, ticket_column = st.columns([3, 1])

with ticket_column:
    st.subheader("Ticket preview")
    card = st.session_state.get("card")
    if card:
        st.markdown(
            f"**Category:** {card['category']}  \n**Urgency:** {card['urgency']}  \n"
            f"**Building:** {card.get('building', 'unknown')}  \n**Unit number:** {card.get('unit_number', card.get('unit'))}  \n"
            f"**Summary:** {card['summary']}"
        )
        st.caption(f"Input tokens for the card: {st.session_state.card_tokens}")
    else:
        st.caption("The triage card appears after the first reply.")
    if st.session_state.get("card_failed"):
        st.caption(st.session_state.get("card_note") or "The card was not updated this turn.")

with chat_column:
    turn = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(f"Input tokens this turn: {st.session_state.input_tokens[turn]}")
                tools_column, rules_column = st.columns(2)
                with tools_column:
                    show_tool_calls(st.session_state.tool_logs[turn])
                with rules_column:
                    show_rules_searches(st.session_state.rules_searches[turn])
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
                        try:
                            reply, tool_log, searches, input_tokens = reply_with_tools(st.session_state.messages)
                        except FilterStop as stop:  # a guardrail or a length limit stopped the reply: show its plain message
                            reply, tool_log, searches, input_tokens = stop.message, [], [], 0
                            if stop.safety:  # do not resend the stopped message, or every later turn is blocked too
                                st.session_state.messages[-1]["content"] = "(message not kept: stopped by the safety filter)"
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.input_tokens.append(input_tokens)
            st.session_state.tool_logs.append(tool_log)
            st.session_state.rules_searches.append(searches)
            try:
                with st.spinner("Updating the ticket preview..."):
                    card, card_tokens = fill_ticket_card(st.session_state.messages)
                st.session_state.card = card
                st.session_state.card_tokens = card_tokens
                st.session_state.card_failed = False
            except FilterStop as stop:  # the guardrail stopped the card call: keep the earlier card and say why
                st.session_state.card_failed = True
                st.session_state.card_note = f"The card was not updated: {stop.message}"
            except Exception:  # the reply is kept; only the card misses this turn, and the earlier card stays
                st.session_state.card_failed = True
                st.session_state.card_note = None
            st.rerun()
        except Exception as error:  # keep the page running and show the problem plainly
            st.session_state.messages.pop()  # drop the unanswered message so the conversation stays in step
            st.error(f"{type(error).__name__}: {error}")
            st.caption("Copy this message into your tutor chat after 'stuck:'.")
