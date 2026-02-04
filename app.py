import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import tempfile

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
WORKERS_PER_DAY = 10
MAX_SUPERVISORS = 3
REQUIRED_WORK_DAYS = 18   # ⬅️ CORE RULE

# ---------------- SESSION STATE ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
        "IWUNZE", "OZUA", "JAMES", "OLABANJI",
        "NURUDEEN", "ENEH", "MUSA", "SANI",
        "ADENIJI", "JOSEPH", "IDOWU"
    ]

if "supervisors" not in st.session_state:
    st.session_state.supervisors = [
        "SUPERVISOR A",
        "SUPERVISOR B",
        "SUPERVISOR C"
    ]

if "supervisor_assignments" not in st.session_state:
    st.session_state.supervisor_assignments = {
        sup: [] for sup in st.session_state.supervisors
    }

# ---------------- SIDEBAR ----------------
st.sidebar.header("1️⃣ Worker Management")

new_worker = st.sidebar.text_input("Add Worker")
if st.sidebar.button("➕ Add Worker"):
    if new_worker and new_worker.upper() not in st.session_state.workers:
        st.session_state.workers.append(new_worker.upper())

st.sidebar.subheader("Edit / Remove Workers")
remove_workers = []

for i, w in enumerate(st.session_state.workers):
    c1, c2 = st.sidebar.columns([4, 1])
    with c1:
        st.session_state.workers[i] = st.text_input(
            f"Worker {i+1}", w, key=f"worker_{i}"
        )
    with c2:
        if st.button("❌", key=f"remove_worker_{i}"):
            remove_workers.append(w)

for w in remove_workers:
    st.session_state.workers.remove(w)

# ---------------- SUPERVISOR MANAGEMENT ----------------
st.sidebar.divider()
st.sidebar.header("2️⃣ Supervisor Management (10 Workers Each)")

for i in range(MAX_SUPERVISORS):
    sup_name = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        key=f"sup_{i}"
    ).upper()

    old_name = st.session_state.supervisors[i]
    st.session_state.supervisors[i] = sup_name

    if old_name != sup_name:
        st.session_state.supervisor_assignments[sup_name] = (
            st.session_state.supervisor_assignments.pop(old_name, [])
        )

    assigned = st.sidebar.multiselect(
        f"{sup_name} → Select 10 Workers",
        st.session_state.workers,
        default=st.session_state.supervisor_assignments.get(sup_name, []),
        key=f"sup_assign_{i}"
    )

    if len(assigned) > WORKERS_PER_DAY:
        st.sidebar.error("❌ Maximum is 10 workers")
    elif len(assigned) < WORKERS_PER_DAY:
        st.sidebar.warning(f"⚠️ {len(assigned)} / 10 selected")

    st.session_state.supervisor_assignments[sup_name] = assigned

# ---------------- DATE SETTINGS ----------------
st.sidebar.divider()
st.sidebar.header("3️⃣ Date Selection")

month = st.sidebar.selectbox(
    "Month", list(range(1, 13)), index=datetime.now().month - 1
)
year = st.sidebar.number_input("Year", 2024, 2030, 2026)
num_days = monthrange(year, month)[1]

OFF_DAYS_PER_WORKER = num_days - REQUIRED_WORK_DAYS

st.sidebar.info(
    f"📌 Each worker will work **{REQUIRED_WORK_DAYS} days**\n"
    f"📌 Off days per worker: **{OFF_DAYS_PER_WORKER} days**"
)

# ---------------- LEAVE MANAGEMENT ----------------
st.sidebar.header("4️⃣ Leave Management")
st.sidebar.info("Format:\nONYEWUNYI: 5, 6, 7")

leave_input = st.sidebar.text_area("Leave Requests")
leave_requests = {}

if leave_input:
    for line in leave_input.split("\n"):
        if ":" in line:
            name, days = line.split(":")
            leave_requests[name.strip().upper()] = [
                int(d.strip())
                for d in days.split(",")
                if d.strip().isdigit() and 1 <= int(d.strip()) <= num_days
            ]

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    days = list(range(1, num_days + 1))
    day_letters = [
        pd.to_datetime(f"{year}-{month:02d}-{d:02d}").strftime("%a")[0]
        for d in days
    ]

    roster_matrix = {"NAME": st.session_state.workers}
    for d in days:
        roster_matrix[d] = ["X"] * len(st.session_state.workers)

    df_matrix = pd.DataFrame(roster_matrix).set_index("NAME")

    worker_shift_counts = {w: 0 for w in st.session_state.workers}

    for d in days:
        available = [
            w for w in st.session_state.workers
            if d not in leave_requests.get(w, [])
            and worker_shift_counts[w] < REQUIRED_WORK_DAYS
        ]

        available.sort(key=lambda x: worker_shift_counts[x])
        selected = available[:WORKERS_PER_DAY]

        if len(selected) < WORKERS_PER_DAY:
            st.warning(f"⚠️ Day {d}: Not enough workers to fill all slots.")

        for w in selected:
            df_matrix.loc[w, d] = "M"
            worker_shift_counts[w] += 1

        for w, leave_days in leave_requests.items():
            if d in leave_days and w in df_matrix.index:
                df_matrix.loc[w, d] = "L"

    header_rows = pd.DataFrame(
        [["DATE"] + days, ["DAY"] + day_letters],
        columns=["NAME"] + days
    )

    export_df = pd.concat(
        [header_rows, df_matrix.reset_index()],
        ignore_index=True
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 Final Roster")
        st.dataframe(export_df, use_container_width=True)

    with col2:
        st.subheader("📊 Duty Days per Worker")

        workload_df = (
            pd.DataFrame(worker_shift_counts.items(), columns=["Worker", "Duty Days"])
            .set_index("Worker")
            .sort_values("Duty Days", ascending=False)
        )

        st.bar_chart(workload_df)

        st.caption("✅ Each worker should show **18 duty days**")

    st.download_button(
        "📥 Download CSV",
        export_df.to_csv(index=False),
        file_name="airline_roster.csv",
        mime="text/csv"
    )

    # ---------------- PDF EXPORT ----------------
    def export_pdf(df):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_path = temp.name
        temp.close()

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        data = [df.columns.tolist()] + df.values.tolist()

        table = Table(data, repeatRows=2)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ]))

        doc.build([table])
        return pdf_path

    pdf_file = export_pdf(export_df)

    with open(pdf_file, "rb") as f:
        st.download_button(
            "📄 Download PDF",
            f,
            file_name="airline_roster.pdf",
            mime="application/pdf"
        )
