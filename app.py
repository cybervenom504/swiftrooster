import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import tempfile

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
WORKERS_PER_DAY = 8
TOTAL_SUPERVISORS = 3

# ---------------- SESSION STATE ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
        "IWUNZE", "OZUA", "JAMES", "OLABANJI",
        "NURUDEEN", "ENEH", "MUSA", "SANI",
        "ADENIJI", "JOSEPH", "IDOWU"
    ]

if "supervisors" not in st.session_state:
    st.session_state.supervisors = [
        "SUPERVISOR A", "SUPERVISOR B", "SUPERVISOR C"
    ]

# ---------------- SIDEBAR ----------------
st.sidebar.header("1️⃣ Worker Management")

new_worker = st.sidebar.text_input("Add Worker")
if st.sidebar.button("➕ Add Worker"):
    if new_worker and new_worker.upper() not in st.session_state.workers:
        st.session_state.workers.append(new_worker.upper())

st.sidebar.header("2️⃣ Supervisor Management (3 Total)")
for i in range(TOTAL_SUPERVISORS):
    st.session_state.supervisors[i] = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        key=f"sup_{i}"
    ).upper()

# ---------------- DATE SETTINGS ----------------
st.sidebar.header("3️⃣ Date Selection")
month = st.sidebar.selectbox("Month", list(range(1, 13)), index=datetime.now().month - 1)
year = st.sidebar.number_input("Year", 2024, 2030, 2026)
num_days = monthrange(year, month)[1]

# ---------------- LEAVE MANAGEMENT ----------------
st.sidebar.header("4️⃣ Leave Management")
st.sidebar.info("Format:\nONYEWUNYI: 5, 6, 7")

leave_input = st.sidebar.text_area("Leave Requests")
leave_requests = {}

if leave_input:
    for line in leave_input.split("\n"):
        if ":" in line:
            name, days
