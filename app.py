import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import tempfile

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
DAYS = list(range(1, 32))
WORKERS_PER_DAY = 10
MAX_SUPERVISORS = 3
REQUIRED_WORK_DAYS = 18
OFF_DAYS = 31 - REQUIRED_WORK_DAYS

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
st.sidebar.header("2️⃣ Supervisor Management (Manual Assignment)")

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
        f"{sup_name} → Assign Workers",
        st.session_state.workers,
        default=st.session_state.supervisor_assignments.get(sup_name, []),
        key=f"sup_assign_{i}"
    )

    st.session_state.supervisor_assignments[sup_name] = assigned

# ---------------- ACTIVE WORKERS ----------------
assigned_workers = sorted({
    w
    for workers in st.session_state.supervisor_assignments.values()
    for w in workers
})

st.subheader("✅ Active Workers (Supervisor Assigned)")
st.write(", ".join(assigned_workers) if assigned_workers else "❌ No workers assigned")

# ---------------- SUPERVISOR DISPLAY ----------------
st.subheader("🧑‍✈️ Supervisor → Worker Assignments")

sup_df = pd.DataFrame([
    {
        "Supervisor": sup,
        "Assigned Workers": ", ".join(workers),
        "Worker Count": len(workers)
    }
    for sup, workers in st.session_state.supervisor_assignments.items()
])

st.dataframe(sup_df, use_container_width=True)

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    if not assigned_workers:
        st.error("❌ No workers assigned to supervisors.")
        st.stop()

    roster_matrix = {"NAME": assigned_workers}
    for d in DAYS:
        roster_matrix[d] = ["O"] * len(assigned_workers)

    df_matrix = pd.DataFrame(roster_matrix).set_index("NAME")

    worker_shift_counts = {w: 0 for w in assigned_workers}

    for d in DAYS:
        available = [
            w for w in assigned_workers
            if worker_shift_counts[w] < REQUIRED_WORK_DAYS
        ]

        available.sort(key=lambda x: worker_shift_counts[x])
        selected = available[:WORKERS_PER_DAY]

        if len(selected) < WORKERS_PER_DAY:
            st.warning(f"⚠️ Day {d}: Staffing shortage")

        for w in selected:
            df_matrix.loc[w, d] = "M"
            worker_shift_counts[w] += 1

    export_df = df_matrix.reset_index()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 31-Day Duty Roster (Assigned Workers Only)")
        st.dataframe(export_df, use_container_width=True)

    with col2:
        st.subheader("📊 Duty Days per Worker")

        workload_df = (
            pd.DataFrame(worker_shift_counts.items(), columns=["Worker", "Duty Days"])
            .set_index("Worker")
            .sort_values("Duty Days", ascending=False)
        )

        st.bar_chart(workload_df)
        st.caption("✅ Each worker should show **18 days**")

    st.download_button(
        "📥 Download CSV",
        export_df.to_csv(index=False),
        file_name="airline_roster_assigned_workers.csv",
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

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
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
            file_name="airline_roster_assigned_workers.pdf",
            mime="application/pdf"
        )
