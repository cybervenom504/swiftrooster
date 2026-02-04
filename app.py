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
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- DATE SAFE SETUP ----------------
year, month = datetime.now().year, datetime.now().month
DAYS = list(range(1, monthrange(year, month)[1] + 1))

# ---------------- CONSTANTS ----------------
STATE_FILE = "roster_state.json"

# ---------------- PERSISTENCE ----------------
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
st.session_state.setdefault("workers_per_day", 3)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)
st.session_state.setdefault("is_admin", False)

st.session_state.setdefault("workers", [
    "ONYEWUNYI","NDIMELE","BELLO","FASEYE","IWUNZE","OZUA",
    "JAMES","OLABANJI","NURUDEEN","ENEH","MUSA","SANI",
    "ADENIJI","JOSEPH","IDOWU"
])

st.session_state.setdefault("supervisors", [
    "SUPERVISOR A","SUPERVISOR B","SUPERVISOR C"
])

st.session_state.setdefault(
    "supervisor_assignments",
    {sup: [] for sup in st.session_state.supervisors}
)

st.session_state.setdefault("leave_days", {})
st.session_state.setdefault("off_days", {})
st.session_state.setdefault("admin_pin", "1234")

# ---------------- SIDEBAR : ADMIN ACCESS ----------------
st.sidebar.header("🔐 Admin Access")
pin = st.sidebar.text_input("Enter Admin PIN", type="password")
if pin:
    st.session_state.is_admin = pin == st.session_state.admin_pin
    if st.session_state.is_admin:
        st.sidebar.success("Admin access granted")
    else:
        st.sidebar.error("Invalid PIN")

# ---------------- ADMIN CONTROLS ----------------
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("⚙️ Admin Controls")

    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers Per Day", 1, 50, st.session_state.workers_per_day
    )

    st.sidebar.subheader("👷 Workers")
    new_worker = st.sidebar.text_input("Add Worker")
    if st.sidebar.button("Add Worker"):
        if new_worker and new_worker.upper() not in st.session_state.workers:
            st.session_state.workers.append(new_worker.upper())

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

    st.sidebar.divider()
    st.sidebar.header("🏖 Admin Controlled Leave")
    max_leave = len(DAYS) - st.session_state.required_work_days
    active_workers = sorted({w for ws in st.session_state.supervisor_assignments.values() for w in ws})
    for w in active_workers:
        leave = st.sidebar.multiselect(
            f"{w} – Leave Days",
            DAYS,
            st.session_state.leave_days.get(w, [])
        )
        if len(leave) <= max_leave:
            st.session_state.leave_days[w] = leave

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({w for ws in st.session_state.supervisor_assignments.values() for w in ws})
st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ---------------- VIEWER : OFF DAYS ----------------
st.sidebar.divider()
st.sidebar.header("📆 Viewer Controlled OFF Days")
if not st.session_state.is_admin and active_workers:
    max_off = len(DAYS) - st.session_state.required_work_days
    for w in active_workers:
        blocked = set(st.session_state.leave_days.get(w, []))
        off = st.sidebar.multiselect(
            f"{w} – OFF Days",
            [d for d in DAYS if d not in blocked],
            st.session_state.off_days.get(w, [])
        )
        if len(off) <= max_off:
            st.session_state.off_days[w] = off

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    for w, leaves in st.session_state.leave_days.items():
        for d in leaves:
            if w in roster.index:
                roster.loc[w, d] = "L"

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

    # ---------------- HTML TABLE (NO STYLER) ----------------
    day_headers = [datetime(year, month, d).strftime("%a")[0] for d in DAYS]

    def cell(val):
        colors_map = {"M": "#90ee90", "O": "#d3d3d3", "L": "#ff7f7f"}
        return f"<td style='background:{colors_map.get(val)};text-align:center;border:1px solid #999'>{val}</td>"

    html = "<table style='border-collapse:collapse;width:100%'>"
    html += "<tr><th style='border:1px solid #999'>Worker</th>"
    html += "".join(f"<th style='border:1px solid #999'>{d}</th>" for d in day_headers)
    html += "</tr>"

    for w in roster.index:
        html += f"<tr><td style='border:1px solid #999'><b>{w}</b></td>"
        html += "".join(cell(roster.loc[w, d]) for d in DAYS)
        html += "</tr>"

    html += "</table>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    st.subheader("📊 Duty Days")
    st.bar_chart(pd.DataFrame.from_dict(duty, orient="index", columns=["Days Worked"]))

    st.download_button("📥 Download CSV", roster.reset_index().to_csv(index=False), "roster.csv")

    # ---------------- PDF EXPORT ----------------
    def export_pdf(df):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4))
        table = Table([["NAME"] + DAYS] + df.reset_index().values.tolist())
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 7)
        ]))
        doc.build([table])
        return tmp.name

    with open(export_pdf(roster), "rb") as f:
        st.download_button("📄 Download PDF", f, "roster.pdf")

# ---------------- SAVE ----------------
save_state()
