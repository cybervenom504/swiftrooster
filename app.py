import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SwiftRoster Pro",
    layout="wide"
)

st.title("📅 SwiftRoster Pro – Airline Roster Generator")

# ---------------- CONSTANTS ----------------
WORKERS_PER_DAY = 8

# ---------------- SESSION STATE ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
        "IWUNZE", "OZUA", "JAMES", "OLABANJI",
        "NURUDEEN", "ENEH", "MUSA", "SANI",
        "ADENIJI", "JOSEPH", "IDOWU"
    ]

# ---------------- SIDEBAR ----------------
st.sidebar.header("1️⃣ Worker Management")

new_worker = st.sidebar.text_input("Add Worker")
if st.sidebar.button("➕ Add Worker"):
    if new_worker and new_worker not in st.session_state.workers:
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

# ---------------- DATE SETTINGS ----------------
st.sidebar.header("2️⃣ Date Selection")

month = st.sidebar.selectbox(
    "Month", list(range(1, 13)), index=datetime.now().month - 1
)
year = st.sidebar.number_input(
    "Year", min_value=2024, max_value=2030, value=2026
)

num_days = monthrange(year, month)[1]

# ---------------- LEAVE MANAGEMENT ----------------
st.sidebar.header("3️⃣ Leave Management")
st.sidebar.info("Format:\nONYEWUNYI: 5, 6, 7")

leave_input = st.sidebar.text_area("Leave Requests")

leave_requests = {}
if leave_input:
    for line in leave_input.split("\n"):
        if ":" in line:
            name, days = line.split(":")
            day_list = [
                int(d.strip())
                for d in days.split(",")
                if d.strip().isdigit() and 1 <= int(d.strip()) <= num_days
            ]
            leave_requests[name.strip().upper()] = day_list

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):

    if len(st.session_state.workers) < WORKERS_PER_DAY:
        st.error("❌ Not enough workers.")
        st.stop()

    days = list(range(1, num_days + 1))
    day_names = [
        pd.to_datetime(f"{year}-{month:02d}-{d:02d}").strftime("%a")[0]
        for d in days
    ]

    # Create empty matrix
    roster_matrix = {
        "NAME": st.session_state.workers
    }

    for d in days:
        roster_matrix[d] = ["X"] * len(st.session_state.workers)

    df_matrix = pd.DataFrame(roster_matrix).set_index("NAME")

    worker_shift_counts = {w: 0 for w in st.session_state.workers}

    for d in days:
        available_workers = [
            w for w in st.session_state.workers
            if d not in leave_requests.get(w, [])
        ]

        available_workers.sort(key=lambda x: worker_shift_counts[x])
        selected = available_workers[:WORKERS_PER_DAY]

        for w in selected:
            df_matrix.loc[w, d] = "M"
            worker_shift_counts[w] += 1

        for w, leave_days in leave_requests.items():
            if d in leave_days and w in df_matrix.index:
                df_matrix.loc[w, d] = "L"

    # ---------------- ADD HEADER ROWS ----------------
    header_rows = pd.DataFrame(
        [
            ["DATE"] + days,
            ["DAY"] + day_names,
        ],
        columns=["NAME"] + days
    )

    export_df = pd.concat(
        [header_rows, df_matrix.reset_index()],
        ignore_index=True
    )

    st.subheader("📋 Roster Preview")
    st.dataframe(export_df, use_container_width=True)

    # ---------------- CSV EXPORT ----------------
    st.download_button(
        "📥 Download CSV (Image Layout)",
        export_df.to_csv(index=False),
        file_name="airline_roster.csv",
        mime="text/csv"
    )

    # ---------------- PDF EXPORT ----------------
    def export_pdf(df):
        pdf_path = "/mnt/data/airline_roster.pdf"

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
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,1), colors.lightgrey),
            ("ALIGN", (1,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
        ]))

        doc.build([table])
        return pdf_path

    pdf_file = export_pdf(export_df)

    with open(pdf_file, "rb") as f:
        st.download_button(
            "📄 Download PDF (Image Layout)",
            f,
            file_name="airline_roster.pdf",
            mime="application/pdf"
        )
