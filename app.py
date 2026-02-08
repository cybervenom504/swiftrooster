import streamlit as st
import pandas as pd
import json
import os
import tempfile
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SwiftRoster Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
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

# ---------------- STATE LOAD (SAFE) ----------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)

        # If file corrupted → reset it
        except json.JSONDecodeError:
            os.remove(STATE_FILE)
            return {}

    return {}

# ---------------- STATE SAVE (ATOMIC) ----------------
def save_state():
    data = {k: st.session_state.get(k) for k in PERSIST_KEYS}

    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(data, f, indent=2)

    os.replace(temp_file, STATE_FILE)

# ---------------- LOAD STORED ----------------
stored = load_state()
for k, v in stored.items():
    st.session_state.setdefault(k, v)

# ---------------- DEFAULT STATE ----------------
st.session_state.setdefault("workers_per_day", 10)
st.session_state.setdefault("required_work_days", 18)
st.session_state.setdefault("max_supervisors", 3)
st.session_state.setdefault("is_admin", False)
st.session_state.setdefault("admin_pin", "1234")
st.session_state.setdefault("roster", None)

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

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Control Panel")

# ---- ADMIN LOGIN ----
with st.sidebar.expander("🔐 Admin Access", expanded=True):

    pin = st.text_input("Enter Admin PIN", type="password")

    if pin:
        if pin == st.session_state.admin_pin:
            st.session_state.is_admin = True
            st.success("Admin access granted")
        else:
            st.session_state.is_admin = False
            st.error("Invalid PIN")

# ---- ADMIN SETTINGS ----
if st.session_state.is_admin:

    with st.sidebar.expander("🛠 Admin Settings", expanded=True):

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
                st.session_state.workers.append(
                    new_worker.upper()
                )

# ---- SUPERVISORS ----
if st.session_state.is_admin:

    with st.sidebar.expander("🧑‍✈️ Supervisors", expanded=True):

        for i in range(st.session_state.max_supervisors):

            sup = st.text_input(
                f"Supervisor {i+1}",
                st.session_state.supervisors[i]
            ).upper()

            old = st.session_state.supervisors[i]
            st.session_state.supervisors[i] = sup

            st.session_state.supervisor_assignments[sup] = \
                st.session_state.supervisor_assignments.pop(old, [])

            assigned = st.multiselect(
                f"{sup} → Workers",
                st.session_state.workers,
                st.session_state.supervisor_assignments[sup]
            )

            st.session_state.supervisor_assignments[sup] = assigned

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({
    w for workers in
    st.session_state.supervisor_assignments.values()
    for w in workers
})

st.info(
    f"✅ Active Workers: {', '.join(active_workers)}"
    if active_workers else
    "No workers assigned yet"
)

# ---------------- LEAVE / OFF DAYS ----------------
with st.sidebar.expander("📆 Leave / OFF Days", expanded=False):

    max_days = 31 - st.session_state.required_work_days

    for w in active_workers:

        if st.session_state.is_admin:

            leave = st.multiselect(
                f"{w} – Leave",
                DAYS,
                st.session_state.leave_days.get(w, [])
            )

            if len(leave) <= max_days:
                st.session_state.leave_days[w] = leave

        else:

            blocked = set(
                st.session_state.leave_days.get(w, [])
            )

            off = st.multiselect(
                f"{w} – OFF",
                [d for d in DAYS if d not in blocked],
                st.session_state.off_days.get(w, [])
            )

            if len(off) <= max_days:
                st.session_state.off_days[w] = off

# ---------------- GENERATE ROSTER ----------------
st.divider()

if st.button(
    "🚀 Generate Roster",
    type="primary",
    use_container_width=True
):

    if not active_workers:
        st.error("No active workers assigned")

    else:

        roster = pd.DataFrame(
            "O",
            index=active_workers,
            columns=DAYS
        )

        duty_count = {
            w: 0 for w in active_workers
        }

        # Apply OFF
        for w, offs in st.session_state.off_days.items():
            for d in offs:
                if w in roster.index:
                    roster.loc[w, d] = "O"

        # Apply Leave
        for w, leaves in st.session_state.leave_days.items():
            for d in leaves:
                if w in roster.index:
                    roster.loc[w, d] = "L"

        # Assign Duties
        for d in DAYS:

            available = [
                w for w in active_workers
                if roster.loc[w, d] == "O"
                and duty_count[w]
                < st.session_state.required_work_days
            ]

            available.sort(
                key=lambda x: duty_count[x]
            )

            for w in available[
                :st.session_state.workers_per_day
            ]:
                roster.loc[w, d] = "M"
                duty_count[w] += 1

        st.session_state.roster = roster
        st.session_state.duty_count = duty_count

        st.success("Roster generated successfully")

# ---------------- DISPLAY ----------------
if st.session_state.roster is not None:

    tab1, tab2, tab3 = st.tabs(
        ["📋 Roster", "📊 Workload", "⬇️ Export"]
    )

    with tab1:
        st.dataframe(
            st.session_state.roster.reset_index(),
            use_container_width=True
        )

    with tab2:

        chart_df = pd.DataFrame.from_dict(
            st.session_state.duty_count,
            orient="index",
            columns=["Days Worked"]
        )

        st.bar_chart(chart_df)

    with tab3:

        # CSV
        st.download_button(
            "📥 Download CSV",
            st.session_state.roster
            .reset_index()
            .to_csv(index=False),
            "roster.csv"
        )

        # PDF
        def export_pdf(df):

            tmp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            )

            doc = SimpleDocTemplate(
                tmp.name,
                pagesize=landscape(A4)
            )

            table = Table(
                [["NAME"] + DAYS] +
                df.reset_index().values.tolist()
            )

            table.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("FONTSIZE", (0,0), (-1,-1), 7)
            ]))

            doc.build([table])

            return tmp.name

        with open(
            export_pdf(st.session_state.roster),
            "rb"
        ) as f:

            st.download_button(
                "📄 Download PDF",
                f,
                "roster.pdf"
            )

# ---------------- SAVE STATE ----------------
save_state()
