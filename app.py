import streamlit as st
import pandas as pd
import calendar
from datetime import date
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

# -------------------------------------------------
# SESSION STATE DEFAULTS
# -------------------------------------------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "JAMES", "IDOWU", "BELLO", "SANI"
    ]

if "supervisors" not in st.session_state:
    st.session_state.supervisors = [
        "ONYEWUENYI", "OLABANJI"
    ]

if "worker_off_days" not in st.session_state:
    st.session_state.worker_off_days = {}

if "supervisor_off_days" not in st.session_state:
    st.session_state.supervisor_off_days = {}

if "assignments" not in st.session_state:
    # Example grouping
    st.session_state.assignments = {
        "ONYEWUENYI": ["JAMES", "IDOWU"],
        "OLABANJI": ["BELLO", "SANI"]
    }

if "roster" not in st.session_state:
    st.session_state.roster = pd.DataFrame()

# -------------------------------------------------
# 🔐 ADMIN PIN LOCK
# -------------------------------------------------
ADMIN_PIN = "1234"

st.sidebar.title("🔐 Admin Access")

pin_input = st.sidebar.text_input(
    "Enter Admin PIN",
    type="password"
)

admin_unlocked = pin_input == ADMIN_PIN

if admin_unlocked:
    st.sidebar.success("Admin Unlocked")
else:
    st.sidebar.warning("Admin Locked")

# -------------------------------------------------
# 📅 CALENDAR SETTINGS
# -------------------------------------------------
st.sidebar.title("📅 Calendar Settings")

year = st.sidebar.number_input(
    "Year", 2024, 2100, date.today().year
)

month = st.sidebar.selectbox(
    "Month",
    list(range(1, 13)),
    format_func=lambda x: calendar.month_name[x]
)

days_in_month = calendar.monthrange(year, month)[1]
days = list(range(1, days_in_month + 1))

# -------------------------------------------------
# 👨🏽‍💼 SUPERVISOR MANAGER (ADMIN ONLY)
# -------------------------------------------------
if admin_unlocked:

    st.sidebar.title("Supervisor Manager")

    new_sup = st.sidebar.text_input(
        "Add Supervisor"
    )

    if st.sidebar.button("Add Supervisor"):
        if new_sup:
            st.session_state.supervisors.append(
                new_sup.upper()
            )

    remove_sup = st.sidebar.selectbox(
        "Remove Supervisor",
        [""] + st.session_state.supervisors
    )

    if st.sidebar.button("Remove Supervisor"):
        if remove_sup:
            st.session_state.supervisors.remove(
                remove_sup
            )

# -------------------------------------------------
# 🧑🏽 WORKER OFF DAYS
# -------------------------------------------------
st.sidebar.title("Worker Days Off")

for w in st.session_state.workers:

    off = st.sidebar.multiselect(
        f"{w} Off Days",
        days,
        key=f"off_{w}"
    )

    st.session_state.worker_off_days[w] = off

# -------------------------------------------------
# 👨🏽‍💼 SUPERVISOR OFF DAYS
# -------------------------------------------------
st.sidebar.title("Supervisor Days Off")

for s in st.session_state.supervisors:

    off = st.sidebar.multiselect(
        f"{s} Off Days",
        days,
        key=f"sup_off_{s}"
    )

    st.session_state.supervisor_off_days[s] = off

# -------------------------------------------------
# ⚙️ GENERATE ROSTER
# -------------------------------------------------
if st.sidebar.button("Generate Roster"):

    roster = pd.DataFrame(
        index=(
            st.session_state.supervisors +
            st.session_state.workers
        ),
        columns=days
    )

    # Supervisors duty
    for d in days:

        available = [
            s for s in st.session_state.supervisors
            if d not in
            st.session_state.supervisor_off_days.get(s, [])
        ]

        duty_sups = available[:2]

        for s in st.session_state.supervisors:

            if s in duty_sups:
                roster.loc[s, d] = "SUP"
            else:
                roster.loc[s, d] = "OFF"

    # Workers duty
    shifts = ["M", "O"]

    for i, w in enumerate(st.session_state.workers):

        for d in days:

            if d in \
               st.session_state.worker_off_days.get(w, []):

                roster.loc[w, d] = "OFF"

            else:

                roster.loc[w, d] = shifts[(i + d) % 2]

    st.session_state.roster = roster

# -------------------------------------------------
# 📋 CALENDAR DISPLAY (GROUPED)
# -------------------------------------------------
st.title("Monthly Duty Roster")

if not st.session_state.roster.empty:

    cal = calendar.monthcalendar(year, month)

    for week in cal:

        cols = st.columns(7)

        for i, day_num in enumerate(week):

            if day_num == 0:
                cols[i].write("")
                continue

            with cols[i]:

                st.markdown(f"### {day_num}")

                # Supervisors first
                for sup in \
                    st.session_state.supervisors:

                    duty = \
                        st.session_state.roster.loc[
                            sup, day_num
                        ]

                    st.write(
                        f"👨🏽‍💼 {sup} — {duty}"
                    )

                    # Workers under supervisor
                    workers = \
                        st.session_state.assignments.get(
                            sup, []
                        )

                    for w in workers:

                        duty = \
                            st.session_state.roster.loc[
                                w, day_num
                            ]

                        st.write(
                            f"   ↳ 🧑🏽 {w} — {duty}"
                        )

# -------------------------------------------------
# 📤 CSV EXPORT
# -------------------------------------------------
if not st.session_state.roster.empty:

    csv = st.session_state.roster.to_csv()

    st.download_button(
        "Download CSV",
        csv,
        "roster.csv"
    )

# -------------------------------------------------
# 🧾 PDF EXPORT (GROUPED)
# -------------------------------------------------
def generate_pdf():

    file_path = "roster.pdf"

    doc = SimpleDocTemplate(file_path)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph(
            "Monthly Duty Roster",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 12))

    data = [["Name"] + days]

    for sup in st.session_state.supervisors:

        data.append([f"SUPERVISOR: {sup}"] + [""]*len(days))

        for w in \
            st.session_state.assignments.get(sup, []):

            row = [w] + list(
                st.session_state.roster.loc[w]
            )

            data.append(row)

    table = Table(data)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("SPAN", (0,1), (-1,1)),
    ]))

    elements.append(table)
    doc.build(elements)

    return file_path

if not st.session_state.roster.empty:

    if st.button("Export PDF"):

        pdf_path = generate_pdf()

        with open(pdf_path, "rb") as f:

            st.download_button(
                "Download PDF",
                f,
                "roster.pdf"
            )
