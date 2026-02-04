import streamlit as st
import pandas as pd
import json
import os
import tempfile
from datetime import datetime
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

stored_state = load_state()
for k, v in stored_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- DEFAULTS ----------------
st.session_state.setdefault("workers_per_day", 10)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)

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

# ---------------- SECURITY ----------------
st.session_state.setdefault("admin_pin", "1234")  # CHANGE IN PRODUCTION
st.session_state.setdefault("current_role", "Viewer")
st.session_state.setdefault("audit_log", [])

def is_admin():
    return st.session_state.current_role == "Admin"

# ---------------- SIDEBAR : ACCESS ----------------
st.sidebar.header("👤 User Access")

role = st.sidebar.selectbox("Role", ["Viewer", "Admin"])
if role == "Admin":
    pin = st.sidebar.text_input("Admin PIN", type="password")
    if pin == st.session_state.admin_pin:
        st.session_state.current_role = "Admin"
        st.sidebar.success("Admin access granted")
    else:
        st.session_state.current_role = "Viewer"
        if pin:
            st.sidebar.error("Invalid PIN")
else:
    st.session_state.current_role = "Viewer"

# ---------------- SIDEBAR : SETTINGS ----------------
st.sidebar.divider()
st.sidebar.header("⚙️ Roster Settings")

if is_admin():
    st.session_state.workers_per_day = st.sidebar.number_input(
        "Workers per Day", 1, 50, st.session_state.workers_per_day
    )
    st.session_state.required_work_days = st.sidebar.number_input(
        "Required Work Days", 1, 31, st.session_state.required_work_days
    )
    st.session_state.max_supervisors = st.sidebar.number_input(
        "Number of Supervisors", 1, 10, st.session_state.max_supervisors
    )
else:
    st.sidebar.info("🔒 Admin access required")

# ---------------- WORKER MANAGEMENT ----------------
st.sidebar.divider()
st.sidebar.header("👷 Workers")

new_worker = st.sidebar.text_input("Add Worker")
if is_admin() and st.sidebar.button("Add"):
    if new_worker and new_worker.upper() not in st.session_state.workers:
        st.session_state.workers.append(new_worker.upper())

# ---------------- SUPERVISORS ----------------
st.sidebar.divider()
st.sidebar.header("🧑‍✈️ Supervisors")

for i in range(st.session_state.max_supervisors):
    sup_name = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i] if i < len(st.session_state.supervisors) else f"SUPERVISOR {i+1}"
    ).upper()

    if i < len(st.session_state.supervisors):
        old = st.session_state.supervisors[i]
        st.session_state.supervisors[i] = sup_name
        st.session_state.supervisor_assignments[sup_name] = \
            st.session_state.supervisor_assignments.pop(old, [])
    else:
        st.session_state.supervisors.append(sup_name)
        st.session_state.supervisor_assignments[sup_name] = []

    assigned = st.sidebar.multiselect(
        f"{sup_name} → Workers",
        st.session_state.workers,
        st.session_state.supervisor_assignments.get(sup_name, [])
    )

    st.session_state.supervisor_assignments[sup_name] = assigned

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({
    w for ws in st.session_state.supervisor_assignments.values() for w in ws
})

st.subheader("✅ Active Workers")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ---------------- SUPERVISOR TABLE ----------------
st.subheader("🧑‍✈️ Supervisor Assignments")
sup_df = pd.DataFrame([
    {"Supervisor": s, "Workers": ", ".join(w), "Count": len(w)}
    for s, w in st.session_state.supervisor_assignments.items()
])
st.dataframe(sup_df, use_container_width=True)

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    if not active_workers:
        st.error("No assigned workers")
        st.stop()

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    counts = {w: 0 for w in active_workers}

    for d in DAYS:
        available = [w for w in active_workers if counts[w] < st.session_state.required_work_days]
        available.sort(key=lambda x: counts[x])
        selected = available[:st.session_state.workers_per_day]

        for w in selected:
            roster.loc[w, d] = "M"
            counts[w] += 1

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 31-Day Roster")
        st.dataframe(roster.reset_index(), use_container_width=True)

    with col2:
        st.subheader("📊 Duty Days")
        chart_df = pd.DataFrame.from_dict(counts, orient="index", columns=["Duty Days"])
        st.bar_chart(chart_df)

    # ---------------- EXPORTS ----------------
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

    pdf = export_pdf(roster)
    with open(pdf, "rb") as f:
        st.download_button("📄 Download PDF", f, "roster.pdf")

# ---------------- AUDIT LOG ----------------
st.subheader("📜 Audit Log")
if st.session_state.audit_log:
    st.dataframe(pd.DataFrame(st.session_state.audit_log), use_container_width=True)
else:
    st.info("No audit events yet")

# ---------------- ADMIN RESET ----------------
st.sidebar.divider()
st.sidebar.header("🛡️ Admin Controls")

if is_admin():
    confirm = st.sidebar.checkbox("I understand this will erase all data")
    if st.sidebar.button("RESET ALL DATA", disabled=not confirm):
        st.session_state.audit_log.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "RESET",
            "by": "Admin"
        })
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        st.session_state.clear()
        st.experimental_rerun()

# ---------------- SAVE STATE ----------------
save_state()
