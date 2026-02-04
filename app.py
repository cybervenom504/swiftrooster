import streamlit as st
import pandas as pd
from datetime import datetime
from calendar import monthrange
from collections import defaultdict
import tempfile
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Daily Supervisor Roster")

# ---------------- MONTH / YEAR SELECTION ----------------
st.sidebar.header("📅 Roster Settings")
year = st.sidebar.selectbox("Year", range(2024, 2031), index=1)
month = st.sidebar.selectbox(
    "Month",
    range(1, 13),
    format_func=lambda m: datetime(2024, m, 1).strftime("%B")
)
total_days = monthrange(year, month)[1]
dates = list(range(1, total_days + 1))

# ---------------- SUPERVISORS & WORKERS ----------------
supervisors = ["Supervisor A", "Supervisor B", "Supervisor C"]
workers = [
    "Alice", "Bob", "Charlie", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia", "Sato"
]

# ---------------- STATE ----------------
st.session_state.setdefault("leave", defaultdict(list))
st.session_state.setdefault("off", defaultdict(list))
st.session_state.setdefault("roster", None)
st.session_state.setdefault("locked", False)
st.session_state.setdefault("workload", {})

# ---------------- SIDEBAR : SETTINGS ----------------
workers_per_day = st.sidebar.number_input(
    "Workers per Day (Max 10)", min_value=1, max_value=10, value=5
)

# ---------------- SIDEBAR : LEAVE ----------------
st.sidebar.header("🏖 Leave Panel")
for w in workers:
    st.session_state.leave[w] = st.sidebar.multiselect(
        w,
        dates,
        st.session_state.leave[w],
        disabled=st.session_state.locked
    )

# ---------------- SIDEBAR : OFF ----------------
st.sidebar.header("📆 Off Panel")
for w in workers:
    st.session_state.off[w] = st.sidebar.multiselect(
        w,
        dates,
        st.session_state.off[w],
        disabled=st.session_state.locked
    )

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    workload = {w: 0 for w in workers}
    rows = []

    for d in dates:
        day_name = datetime(year, month, d).strftime("%A")
        supervisor = supervisors[(d - 1) % 3]

        available = [
            w for w in workers
            if d not in st.session_state.leave[w]
            and d not in st.session_state.off[w]
        ]

        available.sort(key=lambda w: workload[w])
        assigned = available[:workers_per_day]

        for w in assigned:
            workload[w] += 1

        rows.append({
            "Date": d,
            "Day": day_name,
            "Supervisor": supervisor,
            "Workers": ", ".join(assigned)
        })

    st.session_state.roster = pd.DataFrame(rows)
    st.session_state.workload = workload
    st.session_state.locked = True

# ---------------- DISPLAY ROSTER ----------------
if st.session_state.roster is not None:
    st.subheader("📋 Duty Roster")
    st.dataframe(st.session_state.roster, use_container_width=True)

    st.subheader("📊 Worker Workload Balance")
    workload_df = pd.DataFrame.from_dict(
        st.session_state.workload, orient="index", columns=["Days Worked"]
    )
    st.bar_chart(workload_df)

    # ---------------- EXPORT ----------------
    csv = st.session_state.roster.to_csv(index=False)
    st.download_button("📥 Download Excel/CSV", csv, "roster.csv")

    # PDF Export
    def export_pdf(df):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4))
        table = Table([df.columns.tolist()] + df.values.tolist())
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE", (0,0), (-1,-1), 8)
        ]))
        doc.build([table])
        return tmp.name

    with open(export_pdf(st.session_state.roster), "rb") as f:
        st.download_button("📄 Download PDF", f, "roster.pdf")

# ---------------- UNLOCK ----------------
if st.session_state.locked:
    if st.button("🔓 Unlock Roster"):
        st.session_state.locked = False
        st.session_state.roster = None
        st.session_state.workload = {}
