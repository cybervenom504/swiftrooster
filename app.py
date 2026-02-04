import streamlit as st
import pandas as pd
from datetime import datetime
from calendar import monthrange
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# ---------------- CONFIG ----------------
st.set_page_config(page_title="SwiftRoster Pro", layout="wide")
st.title("📅 SwiftRoster Pro")

# ---------------- MONTH SWITCHING ----------------
c1, c2 = st.columns(2)

with c1:
    year = st.selectbox("Year", list(range(2024, 2031)), index=1)

with c2:
    month = st.selectbox(
        "Month",
        list(range(1, 13)),
        format_func=lambda m: datetime(2024, m, 1).strftime("%B")
    )

TOTAL_DAYS = monthrange(year, month)[1]
DAYS = list(range(1, TOTAL_DAYS + 1))

# ---------------- DATA ----------------
workers = [
    "ONYEWUNYI", "NDIMELE", "BELLO", "FASEYE",
    "IWUNZE", "OZUA", "JAMES", "OLABANJI"
]

supervisors = {
    "SUPERVISOR A": ["BELLO", "OLABANJI"],
    "SUPERVISOR B": ["OZUA", "JAMES"],
    "SUPERVISOR C": ["NDIMELE", "FASEYE"]
}

# ---------------- STATE ----------------
st.session_state.setdefault("off_days", {})
st.session_state.setdefault("leave_days", {})
st.session_state.setdefault("roster_locked", False)
st.session_state.setdefault("generated_roster", None)
st.session_state.setdefault("workload", {})

# ---------------- SIDEBAR : LEAVE PANEL ----------------
st.sidebar.header("🏖 LEAVE PANEL")
for w in workers:
    st.session_state.leave_days[w] = st.sidebar.multiselect(
        f"{w} – LEAVE",
        DAYS,
        st.session_state.leave_days.get(w, []),
        disabled=st.session_state.roster_locked
    )

st.sidebar.divider()

# ---------------- SIDEBAR : OFF PANEL ----------------
st.sidebar.header("📆 OFF PANEL")
for sup, ws in supervisors.items():
    st.sidebar.subheader(sup)
    for w in ws:
        st.session_state.off_days[w] = st.sidebar.multiselect(
            f"{w} – OFF",
            DAYS,
            st.session_state.off_days.get(w, []),
            disabled=st.session_state.roster_locked
        )

# ---------------- SUPERVISOR CHART ----------------
st.subheader("🧑‍✈️ Supervisor – Worker Assignment")

rows = []
for sup, ws in supervisors.items():
    for w in ws:
        rows.append({"Supervisor": sup, "Worker": w})

st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ---------------- ACTIVE WORKERS ----------------
active_workers = sorted({w for ws in supervisors.values() for w in ws})

# ---------------- SETTINGS ----------------
max_workers_limit = min(10, len(active_workers))
workers_per_day = st.slider(
    "Workers per day (Max 10)",
    1,
    max_workers_limit,
    min(3, max_workers_limit)
)

required_work_days = st.slider(
    "Required work days",
    1,
    TOTAL_DAYS,
    min(18, TOTAL_DAYS)
)

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Duty Roster"):

    roster = pd.DataFrame("", index=active_workers, columns=DAYS)
    duty = {w: 0 for w in active_workers}

    # Apply LEAVE
    for w, days in st.session_state.leave_days.items():
        for d in days:
            if w in roster.index:
                roster.loc[w, d] = "L"

    # Apply OFF (overrides leave)
    for w, days in st.session_state.off_days.items():
        for d in days:
            if w in roster.index:
                roster.loc[w, d] = "OFF"

    # Assign DUTY
    for d in DAYS:
        available = [
            w for w in active_workers
            if roster.loc[w, d] == ""
            and duty[w] < required_work_days
        ]
        available.sort(key=lambda x: duty[x])

        for w in available[:workers_per_day]:
            roster.loc[w, d] = "M"
            duty[w] += 1

    st.session_state.generated_roster = roster
    st.session_state.workload = duty
    st.session_state.roster_locked = True

# ---------------- UNLOCK ----------------
if st.session_state.roster_locked:
    if st.button("🔓 Unlock Roster"):
        st.session_state.roster_locked = False
        st.session_state.generated_roster = None
        st.session_state.workload = {}

# ---------------- DISPLAY & EXPORT ----------------
if st.session_state.generated_roster is not None:
    roster = st.session_state.generated_roster

    def cell(v):
        if v == "M": color = "#9be7a1"
        elif v == "OFF": color = "#f9e79f"
        elif v == "L": color = "#f5b7b1"
        else: color = "#eee"
        return f"<td style='text-align:center;background:{color}'>{v}</td>"

    html = """
    <style>
    .wrap{overflow-x:auto}
    table{border-collapse:collapse;min-width:900px}
    th,td{border:1px solid #999;padding:6px}
    th:first-child,td:first-child{
        position:sticky;left:0;background:#111;color:white
    }
    </style>
    <div class='wrap'><table>
    <tr><th>Worker</th>""" + "".join(f"<th>{d}</th>" for d in DAYS) + "</tr>"

    for w in roster.index:
        html += f"<tr><td>{w}</td>" + "".join(cell(roster.loc[w, d]) for d in DAYS) + "</tr>"

    html += "</table></div>"

    st.subheader("📋 Duty Roster")
    st.markdown(html, unsafe_allow_html=True)

    # ---------------- WORKLOAD CHART ----------------
    st.subheader("📊 Workload (Days Worked per Worker)")
    workload_df = pd.DataFrame.from_dict(
        st.session_state.workload,
        orient="index",
        columns=["Days Worked"]
    )
    st.bar_chart(workload_df)

    # ---------------- EXCEL EXPORT ----------------
    excel_buffer = BytesIO()
    roster.reset_index().rename(columns={"index": "Worker"}).to_excel(
        excel_buffer, index=False
    )
    st.download_button(
        "📥 Download Excel",
        excel_buffer.getvalue(),
        file_name=f"roster_{year}_{month}.xlsx"
    )

    # ---------------- PDF EXPORT ----------------
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
    table = Table([["Worker"] + DAYS] + roster.reset_index().values.tolist())
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 7)
    ]))
    doc.build([table])

    st.download_button(
        "📄 Download PDF",
        pdf_buffer.getvalue(),
        file_name=f"roster_{year}_{month}.pdf"
    )
