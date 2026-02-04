import streamlit as st
import pandas as pd
import json
import os
import tempfile
from datetime import datetime
from calendar import monthrange
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Duty Roster")

# ---------------- DATE SAFE SETUP ----------------
year, month = datetime.now().year, datetime.now().month
TOTAL_DAYS = monthrange(year, month)[1]
DAYS = list(range(1, TOTAL_DAYS + 1))

# ---------------- STATE ----------------
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
st.session_state.setdefault("workers_per_day", 3)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)
st.session_state.setdefault("is_admin", False)

st.session_state.setdefault("workers", [
    "ONYEWUNYI","NDIMELE","BELLO","FASEYE","IWUNZE","OZUA",
    "JAMES","OLABANJI","NURUDEEN","ENEH","MUSA","SANI"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A","SUPERVISOR B","SUPERVISOR C"
])

st.session_state.setdefault(
    "supervisor_assignments",
    {s: [] for s in st.session_state.supervisors}
)

st.session_state.setdefault("leave_days", {})
st.session_state.setdefault("off_days", {})
st.session_state.setdefault("admin_pin", "1234")

# ---------------- SIDEBAR : ADMIN ACCESS ----------------
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
        "Workers Per Day", 1, 50, st.session_state.workers_per_day
    )

    st.session_state.required_work_days = st.sidebar.number_input(
        "Required Work Days / Month", 1, TOTAL_DAYS, st.session_state.required_work_days
    )

    st.sidebar.subheader("🧑‍✈️ Supervisors")
    for i in range(st.session_state.max_supervisors):
        old = st.session_state.supervisors[i]
        sup = st.sidebar.text_input(f"Supervisor {i+1}", old).upper()
        st.session_state.supervisors[i] = sup
        st.session_state.supervisor_assignments[sup] = st.session_state.supervisor_assignments.pop(old, [])
        st.session_state.supervisor_assignments[sup] = st.sidebar.multiselect(
            f"{sup} → Workers",
            st.session_state.workers,
            st.session_state.supervisor_assignments[sup]
        )

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({w for v in st.session_state.supervisor_assignments.values() for w in v})
st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ---------------- OFF / LEAVE LIMITS ----------------
MAX_OFF = TOTAL_DAYS - st.session_state.required_work_days

st.sidebar.divider()
st.sidebar.header("📆 OFF Days Control")
st.sidebar.caption(f"Max OFF days per worker: **{MAX_OFF}**")

# ---------------- VIEWER / ADMIN OFF DAYS ----------------
for w in active_workers:
    blocked = set(st.session_state.leave_days.get(w, []))
    selected = st.sidebar.multiselect(
        f"{w} – OFF Days",
        [d for d in DAYS if d not in blocked],
        st.session_state.off_days.get(w, [])
    )
    if len(selected) <= MAX_OFF:
        st.session_state.off_days[w] = selected
    else:
        st.sidebar.error(f"{w} exceeded OFF limit ({MAX_OFF})")

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    for w, offs in st.session_state.off_days.items():
        for d in offs:
            roster.loc[w, d] = "O"

    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == "O" and duty[w] < st.session_state.required_work_days
        ]
        available.sort(key=lambda x: duty[x])
        for w in available[:st.session_state.workers_per_day]:
            roster.loc[w, d] = "M"
            duty[w] += 1

    # ---------------- RESPONSIVE ROSTER ----------------
    days_header = [datetime(year, month, d).strftime("%a")[0] for d in DAYS]

    def cell(val):
        colors = {"M": "#9be7a1", "O": "#e0e0e0", "L": "#ff9a9a"}
        return f"<td style='background:{colors[val]};text-align:center'>{val}</td>"

    html = """
    <style>
    .roster-wrap { overflow-x:auto; }
    table { border-collapse: collapse; min-width: 900px; }
    th, td { border:1px solid #aaa; padding:6px; font-size:14px; }
    th:first-child, td:first-child {
        position: sticky;
        left: 0;
        background: #111;
        color: white;
        font-weight: bold;
    }
    </style>
    <div class="roster-wrap">
    <table>
    <tr><th>Worker</th>""" + "".join(f"<th>{d}</th>" for d in days_header) + "</tr>"

    for w in roster.index:
        html += f"<tr><td>{w}</td>" + "".join(cell(roster.loc[w, d]) for d in DAYS) + "</tr>"

    html += "</table></div>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    st.subheader("📊 Duty Summary")
    st.bar_chart(pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"]))

    st.download_button("📥 Download CSV", roster.reset_index().to_csv(index=False), "roster.csv")

# ---------------- SAVE ----------------
save_state()
