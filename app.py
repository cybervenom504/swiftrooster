import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime


# ---------------- CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro – Official Duty Roster")

WORKERS_PER_DAY = 8
SUPERVISORS = ["SUPERVISOR A", "SUPERVISOR B", "SUPERVISOR C"]

# ---------------- SESSION ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "ONYEWUENYI", "NDIMELE", "BELLO", "FASEYE",
        "IWUNZE", "OZUA", "JAMES", "OLABANJI",
        "NURUDEEN", "ENEH", "MUSA", "SANI",
        "ADENIJI", "JOSEPH", "IDOWU"
    ]

# ---------------- SIDEBAR ----------------
st.sidebar.header("Month & Year")
month = st.sidebar.selectbox("Month", range(1, 13), index=0)
year = st.sidebar.number_input("Year", value=2026)

st.sidebar.header("Leave (one per line)")
st.sidebar.info("Format: NAME: 5, 12, 18")
leave_input = st.sidebar.text_area("Leave Input")

leave_requests = {}
if leave_input:
    for line in leave_input.split("\n"):
        if ":" in line:
            name, days = line.split(":")
            leave_requests[name.strip()] = [
                int(d.strip()) for d in days.split(",") if d.strip().isdigit()
            ]

# ---------------- GENERATE ----------------
if st.button("🚀 Generate & Download Excel"):
    num_days = monthrange(year, month)[1]

    worker_counts = {w: 0 for w in st.session_state.workers}
    supervisor_counts = {s: 0 for s in SUPERVISORS}

    roster = {}
    supervisors_by_day = {}

    for day in range(1, num_days + 1):
        # Supervisor rotation
        sup = sorted(SUPERVISORS, key=lambda x: supervisor_counts[x])[0]
        supervisor_counts[sup] += 1
        supervisors_by_day[day] = sup

        # Worker selection
        available = [
            w for w in st.session_state.workers
            if day not in leave_requests.get(w, [])
        ]
        available.sort(key=lambda x: worker_counts[x])
        assigned = available[:WORKERS_PER_DAY]

        for w in assigned:
            worker_counts[w] += 1

        roster[day] = assigned

    # ---------------- EXCEL BUILD ----------------
    wb = Workbook()
    ws = wb.active
    ws.title = "ROSTER"

    thick = Border(
        left=Side(style="thick"),
        right=Side(style="thick"),
        top=Side(style="thick"),
        bottom=Side(style="thick")
    )

    center = Alignment(horizontal="center", vertical="center")
    bold = Font(bold=True)

    # Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_days + 1)
    ws["A1"] = f"ROYAL AIR MAROC ROSTER FOR {datetime(year, month, 1).strftime('%B %Y').upper()}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = center

    row = 3

    # DATE ROW
    ws["A" + str(row)] = "DATE"
    ws["A" + str(row)].font = bold
    for d in range(1, num_days + 1):
        ws.cell(row=row, column=d + 1, value=d)
    row += 1

    # DAY ROW
    ws["A" + str(row)] = "DAY"
    ws["A" + str(row)].font = bold
    for d in range(1, num_days + 1):
        day_letter = datetime(year, month, d).strftime("%a")[0]
        ws.cell(row=row, column=d + 1, value=day_letter)
    row += 1

    # SUPERVISOR ROW
    ws["A" + str(row)] = "SUPERVISOR"
    ws["A" + str(row)].font = bold
    for d in range(1, num_days + 1):
        ws.cell(row=row, column=d + 1, value=supervisors_by_day[d])
    row += 1

    # WORKERS
    for w in st.session_state.workers:
        ws["A" + str(row)] = w
        ws["A" + str(row)].font = bold

        for d in range(1, num_days + 1):
            cell = "X"
            if d in leave_requests.get(w, []):
                cell = "L"
            elif w in roster[d]:
                cell = "M"

            ws.cell(row=row, column=d + 1, value=cell)
        row += 1

    # ---------------- STYLING ----------------
    for r in ws.iter_rows(min_row=3, max_row=row - 1, min_col=1, max_col=num_days + 1):
        for c in r:
            c.border = thick
            c.alignment = center

    # Column widths
    ws.column_dimensions["A"].width = 20
    for i in range(2, num_days + 2):
        ws.column_dimensions[get_column_letter(i)].width = 4

    # Footer
    row += 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_days + 1)
    ws["A" + str(row)] = (
        "RESUMPTION TIME: M 2330HRS / A 1200HRS   "
        "KEYNOTE: X-OFF, M-MORNING, A-AFTERNOON, L-LEAVE"
    )
    ws["A" + str(row)].alignment = center

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_days + 1)
    ws["A" + str(row)] = "PREPARED BY: ONYEWUENYI"
    ws["A" + str(row)].alignment = center
    ws["A" + str(row)].font = bold
    file_name = f"ROYAL_AIR_MAROC_ROSTER_{month}_{year}.xlsx"
    wb.save(file_name)

    with open(file_name, "rb") as f:
        st.download_button(
            "📥 Download Official Roster (Excel)",
            f,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
