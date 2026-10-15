"""
PURPOSE: The app's front door. In S00 it has one box: a resident says hello and the
         service desk answers through your Foundry deployment. It grows every session.
LAYER:   Integration/Experience
SESSION: S00
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

from src.intelligence.hello import first_reply  # noqa: E402

st.set_page_config(page_title="Property Service Desk")

product = os.getenv("PRODUCT_NAME") or "Property Service Desk"
st.title(product)
st.caption("Contoso Living (fictional) · resident service desk · v0.1 in progress")

message = st.text_input("Resident message", value="Hi, the AC in my apartment is not cooling.")

if st.button("Send", type="primary"):
    try:
        with st.spinner("Asking the service desk..."):
            reply = first_reply(message)
        st.chat_message("assistant").write(reply)
    except NotImplementedError as todo:
        st.info(f"This feature is not built yet ({todo}).")
    except RuntimeError as problem:
        st.warning(str(problem))
    except Exception as error:  # show anything else plainly so it can go to the tutor
        st.error(f"{type(error).__name__}: {error}")
        st.caption("Copy this message into your tutor chat after 'stuck:'.")
