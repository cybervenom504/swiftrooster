import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from calendar import monthrange

# ---------------- CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Supervisor OFF & Admin LEAVE")

YEAR = datetime.now().year
MONTH = datetime.now().month
TOTAL_DAYS = monthrange(YEAR, MONTH)[1]
DAYS = list(range(1, TOTAL_DAYS + 1))

STATE_FILE = "roster_state.json"

# ---------------- PERSISTENCE ----------------
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
st.session_state.setdefault("active_supervisor", None)

st.session_state.setdefault("workers", [
    "ONYEWUNYI","NDIMELE","BELLO","FASEYE",
    "IWUNZE","OZUA","JAMES","OLABANJI"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A","SUPERVISOR B"
])

st.session_state.setdefault(
    "supervisor_assignments",
    {s: [] for s in st.session_state.supervisors}
)

st.session_state.setdefault(
    "worker_lock",
    {w: True for w in st.session_state.workers}
)

st.session_state.setdefault("off_days", {})     # Supervisor
st.session_state.setdefault("leave_days", {})   # Admin

st.session_state.setdefault("workers_per_day", 3)
st.session_state.setdefault("required_work_days", 18)

# ---------------- ADMIN LOGIN ----------------
st.sidebar.header("🔐 Admin Login")
pin = st.sidebar.text_input("Admin PIN", type="password")

if pin:
    st.session_state.is_admin = pin == st.session_state.admin_pin
    st.sidebar.success("Admin access granted") if st.session_state.is_admin else st.sidebar.error("Invalid PIN")

# ---------------- ADMIN PANEL ----------------
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("⚙️ Admin Controls")

    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers per day", 1, 20, st.session_state.workers_per_day
    )

    st.session_state.required_work_days = st.sidebar.number_input(
        "Required work days", 1, TOTAL_DAYS, st.session_state.required_work_days
    )

    st.sidebar.subheader("🧑‍✈️ Supervisor Assignments")

    for sup in st.session_state.supervisors:
        current = st.session_state.supervisor_assignments.get(sup, [])
        selected = st.sidebar.multiselect(
            sup, st.session_state.workers, current, key=f"sup_{sup}"
        )

        # Remove from other supervisors
        for w in selected:
            for other in st.session_state.supervisors:
                if other != sup and w in st.session_state.supervisor_assignments[other]:
                    st.session_state.supervisor_assignments[other].remove(w)

        st.session_state.supervisor_assignments[sup] = selected

    # Lock logic
    for w in st.session_state.workers:
        st.session_state.worker_lock[w] = not any(
            w in v for v in st.session_state.supervisor_assignments.values()
        )

    # -------- ADMIN LEAVE --------
    st.sidebar.divider()
    st.sidebar.header("🏖 Admin Leave Control")

    for sup, workers in st.session_state.supervisor_assignments.items():
        for w in workers:
            leave = st.sidebar.multiselect(
                f"{w} – LEAVE",
                DAYS,
                st.session_state.leave_days.get(w, [])
            )
            st.session_state.leave_days[w] = leave

# ---------------- SUPERVISOR LOGIN ----------------
st.sidebar.divider()
st.sidebar.header("🧑‍✈️ Supervisor Login")

st.session_state.active_supervisor = st.sidebar.selectbox(
    "Select Supervisor",
    ["None"] + st.session_state.supervisors
)

# ---------------- SUPERVISOR OFF CONTROL ----------------
if st.session_state.active_supervisor != "None":
    sup = st.session_state.active_supervisor
    workers = st.session_state.supervisor_assignments.get(sup, [])

    st.subheader(f"📆 OFF Control – {sup}")

    for w in workers:
        blocked = set(st.session_state.leave_days.get(w, []))
        selectable = [d for d in DAYS if d not in blocked]

        off = st.multiselect(
            f"{w} – OFF Days",
            selectable,
            st.session_state.off_days.get(w, [])
        )
        st.session_state.off_days[w] = off

# ---------------- ACTIVE WORKERS ----------------
active_workers = [
    w for w in st.session_state.workers
    if not st.session_state.worker_lock[w]
]

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster") and active_workers:

    roster = pd.DataFrame("", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    # Apply LEAVE
    for w, days in st.session_state.leave_days.items():
        for d in days:
            if w in roster.index:
                roster.loc[w, d] = "L"

    # Apply OFF
    for w, days in st.session_state.off_days.items():
        for d in days:
            if w in roster.index and roster.loc[w, d] == "":
                roster.loc[w, d] = "OFF"

    # Assign DUTY
    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == ""
            and duty[w] < st.session_state.required_work_days
        ]
        available.sort(key=lambda x: duty[x])

        for w in available[:st.session_state.workers_per_day]:
            roster.loc[w, d] = "M"
            duty[w] += 1

    # ---------------- RESPONSIVE DISPLAY ----------------
    def cell(v):
        color = "#eee"
        if v == "M": color = "#9be7a1"
        elif v == "OFF": color = "#f9e79f"
        elif v == "L": color = "#f5b7b1"
        return f"<td style='text-align:center;background:{color}'>{v}</td>"

    html = """
    <style>
    .wrap{overflow-x:auto}
    table{border-collapse:collapse;min-width:900px}
    th,td{border:1px solid #999;padding:6px}
    th:first-child,td:first-child{position:sticky;left:0;background:#111;color:white}
    </style>
    <div class='wrap'><table>
    <tr><th>Worker</th>""" + "".join(f"<th>{d}</th>" for d in DAYS) + "</tr>"

    for w in roster.index:
        html += f"<tr><td>{w}</td>" + "".join(cell(roster.loc[w, d]) for d in DAYS) + "</tr>"

    html += "</table></div>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    st.subheader("📊 Duty Summary")
    st.bar_chart(pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"]))

# ---------------- SAVE ----------------
save_state()
