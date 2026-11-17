"""
PURPOSE: Answer a manager's question about the tickets with code_interpreter, and check the one test question in plain pandas.
LAYER:   Orchestration/Action
SESSION: S03
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from mock_systems import work_orders
from src.core.config import get_settings
from src.core.foundry import direct_openai_client

TEST_QUESTION = "How many tickets per category in the last 30 days, and the average days open for closed tickets?"


def ask_manager_question(question: str) -> dict:
    """Send all ticket rows as CSV with the question; the model answers with code it runs. Returns the answer, the code and the input tokens."""
    tickets_csv = pd.DataFrame(work_orders.read_tickets()).to_csv(index=False)
    instructions = (
        "You answer a property manager's questions about maintenance tickets for Contoso Living.\n"
        "The tickets are in the CSV in the message. Columns: id, unit, category, urgency, summary, status, "
        "created_at, closed_at. created_at and closed_at are ISO date-times; closed_at is empty for open tickets.\n"
        f"The current date and time is {datetime.now().isoformat(timespec='seconds')}.\n"
        "Use the python tool for every calculation. Do not work anything out in your head."
    )
    client = direct_openai_client()
    # AI-103 2.1.c: code_interpreter gives the model a Python sandbox in Microsoft's cloud (no network access);
    # "container: auto" lets the service create it. The rows sent here leave the app for that sandbox.
    response = client.responses.create(
        model=get_settings().chat_deployment,
        instructions=instructions,
        input=f"{question}\n\nTickets:\n{tickets_csv}",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        tool_choice="auto",
    )
    # AI-103 2.1.c: each code_interpreter_call item holds the Python the model wrote and the sandbox ran.
    code = [item.code for item in response.output if item.type == "code_interpreter_call" and item.code]
    return {"answer": response.output_text, "code": code, "input_tokens": response.usage.input_tokens}


def compute_test_answer(tickets: pd.DataFrame, now: datetime) -> dict:
    """The true answer to TEST_QUESTION in plain pandas: tickets per category in the last 30 days, and average days open of closed tickets."""
    created = pd.to_datetime(tickets["created_at"])
    closed = pd.to_datetime(tickets["closed_at"])
    recent = tickets[created >= now - timedelta(days=30)]
    days_open = (closed - created).dropna().dt.total_seconds() / 86400
    return {
        "tickets_per_category_last_30_days": recent["category"].value_counts().sort_index().to_dict(),
        "average_days_open_closed_tickets": round(days_open.mean(), 2),
    }


def built_in_check(question: str) -> dict | None:
    """The plain-pandas answer when the question is the test question, otherwise None."""
    if question.strip() != TEST_QUESTION:
        return None
    return compute_test_answer(pd.DataFrame(work_orders.read_tickets()), datetime.now())
