import streamlit as st
import pandas as pd
import json
import os
import tempfile
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
DAYS = list(range(1, 32))
STATE_FILE = "roster_state.json"

# ---------------- PERSISTENT STORAGE ----------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(dict(st.session_state), f, indent=4)

stored = load_state()
for k, v in stored.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- DEFAULTS ----------------
st.session_state.setdefault("workers_per_day", 10)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)
st.session_state.setdefault("is_admin", False)

st.session_state.setdefault("workers", [
    "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
    "IWUNZE", "OZUA", "JAMES", "OLABANJI",
    "NURUDEEN", "ENEH", "MUSA", "SANI",
    "ADENIJI", "JOSEPH", "IDOWU"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A", "SUPERVISOR B", "SUPERVISOR C"
])

st.session_state.setdefault(
    "supervisor_assignments",
    {sup: [] for sup in st.session_state.supervisors}
)

st.session_state.setdefault("leave_days", {})
st.session_state.setdefault("admin_pin", "1234")  # CHANGE IN PROD

# ---------------- SIDEBAR : ADMIN LOGIN ----------------
st.sidebar.header("🔐 Admin Access")

pin_input = st.sidebar.text_input("Enter Admin PIN", type="password")

if pin_input:
    if pin_input == st.session_state.admin_pin:
        st.session_state.is_admin = True
        st.sidebar.success("Admin access granted")
    else:
        st.session_state.is_admin = False
        st.sidebar.error("Invalid PIN")

# ---------------- ADMIN SETTINGS ----------------
st.sidebar.divider()
st.sidebar.header("⚙️ System Settings")

if st.session_state.is_admin:
    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers Per Day", 1, 50, st.session_state.workers_per_day
    )
else:
    st.sidebar.info("Viewer mode")

# ---------------- WORKER MANAGEMENT ----------------
st.sidebar.divider()
st.sidebar.header("👷 Worker Management")

if st.session_state.is_admin:
    new_worker = st.sidebar.text_input("Add Worker")
    if st.sidebar.button("Add Worker"):
        if new_worker and new_worker.upper() not in st.session_state.workers:
            st.session_state.workers.append(new_worker.upper())
else:
    st.sidebar.caption("Admin only")

# ---------------- SUPERVISORS ----------------
st.sidebar.divider()
st.sidebar.header("🧑‍✈️ Supervisors")

if st.session_state.is_admin:
    for i in range(st.session_state.max_supervisors):
        sup = st.sidebar.text_input(
            f"Supervisor {i+1}",
            st.session_state.supervisors[i]
        ).upper()

        old = st.session_state.supervisors[i]
        st.session_state.supervisors[i] = sup
        st.session_state.supervisor_assignments[sup] = \
            st.session_state.supervisor_assignments.pop(old, [])

        assigned = st.sidebar.multiselect(
            f"{sup} → Assigned Workers",
            st.session_state.workers,
            st.session_state.supervisor_assignments[sup]
        )
        st.session_state.supervisor_assignments[sup] = assigned
else:
    st.sidebar.caption("Admin only")

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({
    w for ws in st.session_state.supervisor_assignments.values() for w in ws
})

st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ---------------- SIDEBAR : LEAVE MANAGEMENT ----------------
st.sidebar.divider()
st.sidebar.header("📅 Off & Leave Management")

if st.session_state.is_admin:
    st.sidebar.info("Leave assignment is Viewer-only")
elif not active_workers:
    st.sidebar.warning("No active workers")
else:
    max_leave = 31 - st.session_state.required_work_days
    st.sidebar.caption(f"Maximum leave per worker: {max_leave} days")

    for w in active_workers:
        leave = st.sidebar.multiselect(
            f"{w} – Leave Days",
            DAYS,
            st.session_state.leave_days.get(w, [])
        )

        if len(leave) > max_leave:
            st.sidebar.error("Too many leave days")
        else:
            st.session_state.leave_days[w] = leave

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    for w, leave in st.session_state.leave_days.items():
        for d in leave:
            if w in roster.index:
                roster.loc[w, d] = "L"

    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == "O"
            and duty[w] < st.session_state.required_work_days
        ]

        available.sort(key=lambda x: duty[x])
        selected = available[:st.session_state.workers_per_day]

        for w in selected:
            roster.loc[w, d] = "M"
            duty[w] += 1

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 31-Day Duty Roster")
        st.dataframe(roster.reset_index(), use_container_width=True)

    with col2:
        st.subheader("📊 Duty Count")
        chart_df = pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"])
        st.bar_chart(chart_df)

    st.download_button(
        "📥 Download CSV",
        roster.reset_index().to_csv(index=False),
        "roster.csv"
    )

    def export_pdf(df):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4))
        table = Table([["NAME"] + DAYS] + df.reset_index().values.tolist())
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE", (0,0), (-1,-1), 7)
        ]))
        doc.build([table])
        return tmp.name

    with open(export_pdf(roster), "rb") as f:
        st.download_button("📄 Download PDF", f, "roster.pdf")

# ---------------- SAVE STATE ----------------
save_state()
