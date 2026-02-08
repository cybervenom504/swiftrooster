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

DAYS = list(range(1, 32))
STATE_FILE = "roster_state.json"

PERSIST_KEYS = [
    "workers",
    "supervisors",
    "supervisor_assignments",
    "leave_days",
    "off_days",
    "workers_per_day",
    "required_work_days",
    "max_supervisors",
    "admin_pin"
]

# ---------------- LOAD / SAVE ----------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state():
    data = {k: st.session_state.get(k) for k in PERSIST_KEYS}
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

stored = load_state()
for k, v in stored.items():
    st.session_state.setdefault(k, v)

# ---------------- DEFAULTS ----------------
st.session_state.setdefault("workers_per_day", 10)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)
st.session_state.setdefault("admin_pin", "1234")
st.session_state.setdefault("is_admin", False)
st.session_state.setdefault("roster", None)

st.session_state.setdefault("workers", [
    "ONYEWUNYI","NDIMELE","BELLO","FASEYE","IWUNZE",
    "OZUA","JAMES","OLABANJI","NURUDEEN","ENEH",
    "MUSA","SANI","ADENIJI","JOSEPH","IDOWU"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR 1","SUPERVISOR 2","SUPERVISOR 3"
])

st.session_state.setdefault("supervisor_assignments", {})
st.session_state.setdefault("leave_days", {})
st.session_state.setdefault("off_days", {})

# ensure supervisor list size
while len(st.session_state.supervisors) < st.session_state.max_supervisors:
    st.session_state.supervisors.append(
        f"SUPERVISOR {len(st.session_state.supervisors)+1}"
    )

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Control Panel")

# ADMIN LOGIN
with st.sidebar.expander("🔐 Admin Access", True):

    pin = st.text_input("Enter Admin PIN", type="password")

    if st.button("Login"):
        if pin == st.session_state.admin_pin:
            st.session_state.is_admin = True
            st.success("Admin access granted")
        else:
            st.session_state.is_admin = False
            st.error("Invalid PIN")

# ---------------- ADMIN SETTINGS ----------------
if st.session_state.is_admin:

    with st.sidebar.expander("🛠 Admin Settings", True):

        st.session_state.workers_per_day = st.number_input(
            "Workers per day", 1, 50,
            st.session_state.workers_per_day
        )

        st.session_state.required_work_days = st.number_input(
            "Required work days", 1, 31,
            st.session_state.required_work_days
        )

        new_worker = st.text_input("Add Worker")

        if st.button("➕ Add Worker"):
            if new_worker:
                st.session_state.workers.append(new_worker.upper())

# ---------------- SUPERVISORS ----------------
if st.session_state.is_admin:

    with st.sidebar.expander("🧑‍✈️ Supervisors", True):

        new_assignments = {}

        for i in range(st.session_state.max_supervisors):

            old_sup = st.session_state.supervisors[i]

            sup = st.text_input(
                f"Supervisor {i+1}",
                old_sup
            ).upper()

            st.session_state.supervisors[i] = sup

            current_workers = st.session_state.supervisor_assignments.get(old_sup, [])

            assigned = st.multiselect(
                f"{sup} → Workers",
                st.session_state.workers,
                current_workers
            )

            new_assignments[sup] = assigned

        st.session_state.supervisor_assignments = new_assignments

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({
    w for workers in
    st.session_state.supervisor_assignments.values()
    for w in workers
})

st.info(
    f"✅ Active Workers: {', '.join(active_workers)}"
    if active_workers else "No workers assigned yet"
)

# ---------------- GENERATE ----------------
st.divider()

if st.button("🚀 Generate Roster", use_container_width=True):

    if not active_workers:
        st.error("No active workers assigned")

    else:

        roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
        duty_count = {w: 0 for w in active_workers}

        for d in DAYS:
            available = [
                w for w in active_workers
                if duty_count[w] < st.session_state.required_work_days
            ]

            available.sort(key=lambda x: duty_count[x])

            for w in available[:st.session_state.workers_per_day]:
                roster.loc[w, d] = "M"
                duty_count[w] += 1

        st.session_state.roster = roster
        st.success("Roster generated")

# ---------------- DISPLAY ----------------
if st.session_state.roster is not None:
    st.dataframe(st.session_state.roster, use_container_width=True)

save_state()
