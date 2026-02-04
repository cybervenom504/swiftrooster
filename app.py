import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from calendar import monthrange

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Locked Supervisor Roster")

# ---------------- DATE SETUP ----------------
year, month = datetime.now().year, datetime.now().month
TOTAL_DAYS = monthrange(year, month)[1]
DAYS = list(range(1, TOTAL_DAYS + 1))

# ---------------- STATE FILE ----------------
STATE_FILE = "roster_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(dict(st.session_state), f, indent=2)

stored = load_state()
for k, v in stored.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- DEFAULTS ----------------
st.session_state.setdefault("admin_pin", "1234")
st.session_state.setdefault("is_admin", False)

st.session_state.setdefault("workers", [
    "ONYEWUNYI","NDIMELE","BELLO","FASEYE","IWUNZE",
    "OZUA","JAMES","OLABANJI","NURUDEEN","ENEH"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A","SUPERVISOR B","SUPERVISOR C"
])

# supervisor -> workers
st.session_state.setdefault(
    "supervisor_assignments",
    {s: [] for s in st.session_state.supervisors}
)

# worker -> locked/unlocked
st.session_state.setdefault(
    "worker_lock",
    {w: True for w in st.session_state.workers}
)

st.session_state.setdefault("off_days", {})
st.session_state.setdefault("workers_per_day", 3)
st.session_state.setdefault("required_work_days", 18)

# ---------------- ADMIN ACCESS ----------------
st.sidebar.header("🔐 Admin Access")
pin = st.sidebar.text_input("Admin PIN", type="password")
if pin:
    st.session_state.is_admin = pin == st.session_state.admin_pin
    st.sidebar.success("Admin access") if st.session_state.is_admin else st.sidebar.error("Invalid PIN")

# ---------------- ADMIN CONTROLS ----------------
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("⚙️ Admin Controls")

    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers Per Day", 1, 20, st.session_state.workers_per_day
    )

    st.session_state.required_work_days = st.sidebar.number_input(
        "Required Work Days", 1, TOTAL_DAYS, st.session_state.required_work_days
    )

    st.sidebar.subheader("🔒 Worker Locking (Unlock via Supervisor)")
    for sup in st.session_state.supervisors:
        assigned = st.session_state.supervisor_assignments.get(sup, [])
        selectable = [
            w for w in st.session_state.workers
            if st.session_state.worker_lock[w] or w in assigned
        ]

        chosen = st.sidebar.multiselect(
            f"{sup} → Workers",
            selectable,
            assigned,
            key=f"assign_{sup}"
        )

        # Remove worker from other supervisors
        for w in chosen:
            for other in st.session_state.supervisors:
                if other != sup and w in st.session_state.supervisor_assignments[other]:
                    st.session_state.supervisor_assignments[other].remove(w)

        st.session_state.supervisor_assignments[sup] = chosen

    # Update lock status
    for w in st.session_state.workers:
        st.session_state.worker_lock[w] = not any(
            w in v for v in st.session_state.supervisor_assignments.values()
        )

# ---------------- SUPERVISOR OVERVIEW ----------------
st.subheader("🧑‍✈️ Supervisors & Workers")

for sup in st.session_state.supervisors:
    workers = st.session_state.supervisor_assignments.get(sup, [])
    with st.expander(f"{sup} ({len(workers)} unlocked)"):
        if workers:
            st.write(", ".join(workers))
        else:
            st.caption("No workers unlocked")

# ---------------- ACTIVE WORKERS ----------------
active_workers = [w for w in st.session_state.workers if not st.session_state.worker_lock[w]]

st.subheader("✅ Active (Unlocked) Workers")
st.write(", ".join(active_workers) if active_workers else "No active workers")

# ---------------- OFF DAYS ----------------
MAX_OFF = TOTAL_DAYS - st.session_state.required_work_days
st.sidebar.divider()
st.sidebar.header("📆 OFF Days")

for w in active_workers:
    off = st.sidebar.multiselect(
        f"{w} – OFF Days (max {MAX_OFF})",
        DAYS,
        st.session_state.off_days.get(w, [])
    )
    if len(off) <= MAX_OFF:
        st.session_state.off_days[w] = off

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster") and active_workers:

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    for w, offs in st.session_state.off_days.items():
        for d in offs:
            if w in roster.index:
                roster.loc[w, d] = "O"

    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == "O"
            and duty[w] < st.session_state.required_work_days
        ]
        available.sort(key=lambda x: duty[x])
        for w in available[:st.session_state.workers_per_day]:
            roster.loc[w, d] = "M"
            duty[w] += 1

    # ---------------- RESPONSIVE TABLE ----------------
    days_header = [datetime(year, month, d).strftime("%a")[0] for d in DAYS]

    def cell(val):
        colors = {"M": "#9be7a1", "O": "#e0e0e0"}
        return f"<td style='background:{colors[val]};text-align:center'>{val}</td>"

    html = """
    <style>
    .wrap { overflow-x:auto; }
    table { border-collapse:collapse; min-width:900px; }
    th, td { border:1px solid #999; padding:6px; }
    th:first-child, td:first-child {
        position:sticky; left:0;
        background:#111; color:white;
        font-weight:bold;
    }
    </style>
    <div class="wrap"><table>
    <tr><th>Worker</th>""" + "".join(f"<th>{d}</th>" for d in days_header) + "</tr>"

    for w in roster.index:
        html += f"<tr><td>{w}</td>" + "".join(cell(roster.loc[w, d]) for d in DAYS) + "</tr>"

    html += "</table></div>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    st.subheader("📊 Duty Summary")
    st.bar_chart(pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"]))

# ---------------- SAVE ----------------
save_state()
