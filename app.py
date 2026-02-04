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
today = datetime.now()
YEAR = today.year
MONTH = today.month
TOTAL_DAYS = monthrange(YEAR, MONTH)[1]
DAYS = list(range(1, TOTAL_DAYS + 1))

# ---------------- STATE STORAGE ----------------
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

# ---------------- DEFAULT VALUES ----------------
st.session_state.setdefault("admin_pin", "1234")
st.session_state.setdefault("is_admin", False)

st.session_state.setdefault("workers", [
    "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
    "IWUNZE", "OZUA", "JAMES", "OLABANJI",
    "NURUDEEN", "ENEH"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A", "SUPERVISOR B", "SUPERVISOR C"
])

st.session_state.setdefault(
    "supervisor_assignments",
    {s: [] for s in st.session_state.supervisors}
)

st.session_state.setdefault(
    "worker_lock",
    {w: True for w in st.session_state.workers}
)

st.session_state.setdefault("off_days", {})
st.session_state.setdefault("workers_per_day", 3)
st.session_state.setdefault("required_work_days", 18)

# ---------------- ADMIN LOGIN (FIXED) ----------------
st.sidebar.header("🔐 Admin Access")
pin = st.sidebar.text_input("Enter Admin PIN", type="password")

if pin:
    if pin == st.session_state.admin_pin:
        st.session_state.is_admin = True
        st.sidebar.success("✅ Admin access granted")
    else:
        st.session_state.is_admin = False
        st.sidebar.error("❌ Invalid PIN")

# ---------------- ADMIN CONTROLS ----------------
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("⚙️ Admin Controls")

    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers per Day", 1, 20, st.session_state.workers_per_day
    )

    st.session_state.required_work_days = st.sidebar.number_input(
        "Required Work Days",
        1,
        TOTAL_DAYS,
        st.session_state.required_work_days
    )

    st.sidebar.subheader("🔒 Unlock Workers via Supervisors")

    for sup in st.session_state.supervisors:
        current = st.session_state.supervisor_assignments.get(sup, [])

        selectable = [
            w for w in st.session_state.workers
            if st.session_state.worker_lock[w] or w in current
        ]

        chosen = st.sidebar.multiselect(
            f"{sup}",
            selectable,
            current,
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
st.subheader("🧑‍✈️ Supervisors & Unlocked Workers")

for sup in st.session_state.supervisors:
    workers = st.session_state.supervisor_assignments.get(sup, [])
    with st.expander(f"{sup} ({len(workers)} workers)"):
        if workers:
            st.write(", ".join(workers))
        else:
            st.caption("No workers unlocked")

# ---------------- ACTIVE WORKERS ----------------
active_workers = [
    w for w in st.session_state.workers
    if not st.session_state.worker_lock[w]
]

st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No active workers")

# ---------------- OFF DAYS ----------------
MAX_OFF = TOTAL_DAYS - st.session_state.required_work_days

st.sidebar.divider()
st.sidebar.header("📆 OFF Days")

for w in active_workers:
    selected = st.sidebar.multiselect(
        f"{w} (max {MAX_OFF})",
        DAYS,
        st.session_state.off_days.get(w, [])
    )
    if len(selected) <= MAX_OFF:
        st.session_state.off_days[w] = selected

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster") and active_workers:

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty_count = {w: 0 for w in active_workers}

    for w, offs in st.session_state.off_days.items():
        for d in offs:
            if w in roster.index:
                roster.loc[w, d] = "O"

    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == "O"
            and duty_count[w] < st.session_state.required_work_days
        ]
        available.sort(key=lambda x: duty_count[x])

        for w in available[:st.session_state.workers_per_day]:
            roster.loc[w, d] = "M"
            duty_count[w] += 1

    # ---------------- RESPONSIVE TABLE ----------------
    weekday = [datetime(YEAR, MONTH, d).strftime("%a")[0] for d in DAYS]

    def cell(v):
        return f"<td style='text-align:center;background:{'#9be7a1' if v=='M' else '#eee'}'>{v}</td>"

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
    <div class='wrap'><table>
    <tr><th>Worker</th>""" + "".join(f"<th>{d}</th>" for d in weekday) + "</tr>"

    for w in roster.index:
        html += f"<tr><td>{w}</td>" + "".join(cell(roster.loc[w, d]) for d in DAYS) + "</tr>"

    html += "</table></div>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    st.subheader("📊 Duty Summary")
    st.bar_chart(pd.DataFrame.from_dict(duty_count, orient="index", columns=["Days Worked"]))

# ---------------- SAVE STATE ----------------
save_state()
