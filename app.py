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

# ---------------- STORAGE ----------------
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
st.session_state.setdefault("admin_viewer_mode", False)

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
st.session_state.setdefault("off_days", {})
st.session_state.setdefault("admin_pin", "1234")  # CHANGE IN PROD

# ---------------- SIDEBAR : ADMIN LOGIN ----------------
st.sidebar.header("🔐 Admin Unlock")

pin = st.sidebar.text_input("Enter Admin PIN", type="password")

if pin:
    if pin == st.session_state.admin_pin:
        st.session_state.is_admin = True
        st.sidebar.success("Admin unlocked")
    else:
        st.session_state.is_admin = False
        st.sidebar.error("Invalid PIN")

# ---------------- MODE SWITCH ----------------
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("🔁 Mode")
    st.session_state.admin_viewer_mode = st.sidebar.toggle(
        "View as Viewer",
        value=st.session_state.admin_viewer_mode
    )

# Effective permissions
CAN_ADMIN = st.session_state.is_admin and not st.session_state.admin_viewer_mode
CAN_ASSIGN_LEAVE = st.session_state.is_admin or not CAN_ADMIN

# ---------------- SYSTEM SETTINGS ----------------
st.sidebar.divider()
st.sidebar.header("⚙️ System Settings")

if CAN_ADMIN:
    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers Per Day", 1, 50, st.session_state.workers_per_day
    )
else:
    st.sidebar.number_input(
        "Workers Per Day",
        value=st.session_state.workers_per_day,
        disabled=True,
        help="Unlock admin to edit"
    )

# ---------------- WORKERS ----------------
st.sidebar.divider()
st.sidebar.header("👷 Workers")

if CAN_ADMIN:
    new_worker = st.sidebar.text_input("Add Worker")
    if st.sidebar.button("Add Worker"):
        if new_worker and new_worker.upper() not in st.session_state.workers:
            st.session_state.workers.append(new_worker.upper())
else:
    st.sidebar.text_input("Add Worker", disabled=True)

# ---------------- SUPERVISORS ----------------
st.sidebar.divider()
st.sidebar.header("🧑‍✈️ Supervisors")

for i in range(st.session_state.max_supervisors):
    disabled = not CAN_ADMIN

    sup = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        disabled=disabled
    ).upper()

    old = st.session_state.supervisors[i]
    if CAN_ADMIN:
        st.session_state.supervisors[i] = sup
        st.session_state.supervisor_assignments[sup] = \
            st.session_state.supervisor_assignments.pop(old, [])

    st.sidebar.multiselect(
        f"{sup} → Workers",
        st.session_state.workers,
        st.session_state.supervisor_assignments[sup],
        disabled=disabled,
        help="Unlock admin to edit"
    )

    if CAN_ADMIN:
        st.session_state.supervisor_assignments[sup] = st.session_state.supervisor_assignments[sup]

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({
    w for ws in st.session_state.supervisor_assignments.values() for w in ws
})

st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ---------------- OFF & LEAVE ----------------
st.sidebar.divider()
st.sidebar.header("📅 Off & Leave Management")

if not active_workers:
    st.sidebar.warning("No active workers")
else:
    max_non_work = 31 - st.session_state.required_work_days
    st.sidebar.caption(f"Off + Leave ≤ {max_non_work} days")

    for w in active_workers:
        leave = st.sidebar.multiselect(
            f"{w} – Leave (L)",
            DAYS,
            st.session_state.leave_days.get(w, [])
        )

        off = st.sidebar.multiselect(
            f"{w} – Off (O)",
            [d for d in DAYS if d not in leave],
            st.session_state.off_days.get(w, [])
        )

        if len(set(leave) | set(off)) > max_non_work:
            st.sidebar.error("Too many non-working days")
        else:
            st.session_state.leave_days[w] = leave
            st.session_state.off_days[w] = off

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    for w in active_workers:
        for d in st.session_state.leave_days.get(w, []):
            roster.loc[w, d] = "L"
        for d in st.session_state.off_days.get(w, []):
            roster.loc[w, d] = "O"

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
        st.bar_chart(
            pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"])
        )

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

    with open(export_pdf(roster), "rb") as
