import streamlit as st
import pandas as pd
import json
import os
import tempfile
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ================= PAGE CONFIG =================
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ================= CONSTANTS =================
DAYS = list(range(1, 32))
STATE_FILE = "roster_state.json"

# ================= PERSISTENT STORAGE =================
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

# ================= DEFAULT STATE =================
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
st.session_state.setdefault("workers_per_day", 10)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("admin_pin", "1234")  # CHANGE IN PROD
st.session_state.setdefault("is_admin", False)
st.session_state.setdefault("admin_viewer_mode", False)

# ================= ADMIN AUTH =================
st.sidebar.header("🔐 Admin Access")
pin = st.sidebar.text_input("Admin PIN", type="password")

if pin:
    if pin == st.session_state.admin_pin:
        st.session_state.is_admin = True
        st.sidebar.success("Admin unlocked")
    else:
        st.session_state.is_admin = False
        st.sidebar.error("Invalid PIN")

# ================= MODE CONTROL =================
if st.session_state.is_admin:
    st.sidebar.divider()
    st.sidebar.header("🔁 Mode Control")
    st.session_state.admin_viewer_mode = st.sidebar.toggle(
        "Switch to Viewer Mode",
        value=st.session_state.admin_viewer_mode
    )

CAN_ADMIN = st.session_state.is_admin and not st.session_state.admin_viewer_mode

# ================= SYSTEM SETTINGS =================
st.sidebar.divider()
st.sidebar.header("⚙️ System Settings")

st.sidebar.number_input(
    "Workers Per Day",
    min_value=1,
    max_value=20,
    value=st.session_state.workers_per_day,
    disabled=not CAN_ADMIN
)

st.sidebar.number_input(
    "Required Work Days",
    min_value=1,
    max_value=31,
    value=st.session_state.required_work_days,
    disabled=not CAN_ADMIN
)

# ================= WORKER MANAGEMENT =================
st.sidebar.divider()
st.sidebar.header("👷 Workers")

if CAN_ADMIN:
    new_worker = st.sidebar.text_input("Add Worker")
    if st.sidebar.button("➕ Add Worker"):
        if new_worker and new_worker.upper() not in st.session_state.workers:
            st.session_state.workers.append(new_worker.upper())
else:
    st.sidebar.text_input("Add Worker", disabled=True)

# ================= SUPERVISOR MANAGEMENT =================
st.sidebar.divider()
st.sidebar.header("🧑‍✈️ Supervisors")

for i in range(len(st.session_state.supervisors)):
    disabled = not CAN_ADMIN

    sup_name = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        disabled=disabled
    ).upper()

    old = st.session_state.supervisors[i]
    if CAN_ADMIN:
        st.session_state.supervisors[i] = sup_name
        st.session_state.supervisor_assignments[sup_name] = (
            st.session_state.supervisor_assignments.pop(old, [])
        )

    st.session_state.supervisor_assignments[sup_name] = st.sidebar.multiselect(
        f"{sup_name} → Assigned Workers",
        st.session_state.workers,
        st.session_state.supervisor_assignments[sup_name],
        disabled=disabled,
        help="Unlock admin to edit"
    )

# ================= ACTIVE WORKERS =================
active_workers = sorted({
    w for ws in st.session_state.supervisor_assignments.values() for w in ws
})

st.subheader("✅ Active Workers (Assigned to Supervisors)")
st.write(", ".join(active_workers) if active_workers else "No workers assigned")

# ================= OFF & LEAVE (VIEWER + ADMIN) =================
st.sidebar.divider()
st.sidebar.header("📅 Off & Leave Scheduling")

max_non_work = 31 - st.session_state.required_work_days

if active_workers:
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

        if len(set(leave + off)) <= max_non_work:
            st.session_state.leave_days[w] = leave
            st.session_state.off_days[w] = off
        else:
            st.sidebar.error(f"{w}: Too many off/leave days")

# ================= GENERATE ROSTER =================
if st.button("🚀 Generate 31-Day Roster"):

    roster = pd.DataFrame("O", index=active_workers, columns=DAYS)
    duty_count = {w: 0 for w in active_workers}

    for w in active_workers:
        for d in st.session_state.leave_days.get(w, []):
            roster.loc[w, d] = "L"
        for d in st.session_state.off_days.get(w, []):
            roster.loc[w, d] = "O"

    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == "O"
            and duty_count[w] < st.session_state.required_work_days
        ]

        available.sort(key=lambda x: duty_count[x])
        selected = available[:st.session_state.workers_per_day]

        for w in selected:
            roster.loc[w, d] = "M"
            duty_count[w] += 1

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 Duty Roster (31 Days)")
        st.dataframe(roster.reset_index(), use_container_width=True)

    with col2:
        st.subheader("📊 Days Worked")
        st.bar_chart(
            pd.DataFrame.from_dict(duty_count, orient="index", columns=["Days Worked"])
        )

    # CSV EXPORT
    st.download_button(
        "📥 Download CSV",
        roster.reset_index().to_csv(index=False),
        file_name="roster.csv"
    )

    # PDF EXPORT (FIXED)
    def export_pdf(df):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4))
        table = Table([["NAME"] + DAYS] + df.reset_index().values.tolist())
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ]))
        doc.build([table])
        return tmp.name

    pdf_path = export_pdf(roster)
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Download PDF",
            f,
            file_name="roster.pdf",
            mime="application/pdf"
        )

# ================= ADMIN RESET =================
st.sidebar.divider()
st.sidebar.header("🛡️ Admin Controls")

if st.sidebar.button("♻️ RESET ALL DATA"):
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    st.session_state.clear()
    st.experimental_rerun()

# ================= SAVE STATE =================
save_state()
