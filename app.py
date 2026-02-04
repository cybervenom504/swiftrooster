import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SwiftRoster Pro",
    layout="wide"
)

st.title("📅 SwiftRoster Pro – Workers & Supervisor Roster")

# ---------------- CONSTANT RULES ----------------
WORKERS_PER_DAY = 8
SUPERVISORS_PER_DAY = 1
TOTAL_SUPERVISORS = 3

# ---------------- SESSION STATE ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "Alice", "Bob", "Charlie", "Diana",
        "Edward", "Fiona", "George", "Hannah",
        "Ian", "Julia"
    ]

if "supervisors" not in st.session_state:
    st.session_state.supervisors = [
        "Supervisor A", "Supervisor B", "Supervisor C"
    ]

# ---------------- SIDEBAR ----------------
st.sidebar.header("1️⃣ Worker Management")

new_worker = st.sidebar.text_input("Add Worker")
if st.sidebar.button("➕ Add Worker"):
    if new_worker and new_worker not in st.session_state.workers:
        st.session_state.workers.append(new_worker)

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

# ---------------- SUPERVISORS ----------------
st.sidebar.header("2️⃣ Supervisor Management (3 Total)")
for i in range(TOTAL_SUPERVISORS):
    st.session_state.supervisors[i] = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        key=f"sup_{i}"
    )

# ---------------- DATE SETTINGS ----------------
st.sidebar.header("3️⃣ Date Selection")
month = st.sidebar.selectbox(
    "Month", list(range(1, 13)), index=datetime.now().month - 1
)
year = st.sidebar.number_input(
    "Year", min_value=2024, max_value=2030, value=2026
)

num_days = monthrange(year, month)[1]

# ---------------- LEAVE MANAGEMENT ----------------
st.sidebar.header("4️⃣ Leave / Blackout Dates")
st.sidebar.info("Format (one per line):\nAlice: 5, 6, 7")

leave_input = st.sidebar.text_area("Enter Leave Requests")

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
            leave_requests[name.strip()] = day_list

# ---------------- GENERATE ROSTER ----------------
if st.button("🚀 Generate Roster"):
    if len(st.session_state.workers) < WORKERS_PER_DAY:
        st.error("❌ Not enough workers to meet daily requirement.")
        st.stop()

    worker_shift_counts = {w: 0 for w in st.session_state.workers}
    supervisor_shift_counts = {s: 0 for s in st.session_state.supervisors}

    roster_data = []

    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"

        # -------- SUPERVISOR SELECTION --------
        available_supervisors = [
            s for s in st.session_state.supervisors
            if day not in leave_requests.get(s, [])
        ]

        available_supervisors.sort(
            key=lambda x: supervisor_shift_counts[x]
        )

        supervisor_today = available_supervisors[0]
        supervisor_shift_counts[supervisor_today] += 1

        # -------- WORKER SELECTION --------
        available_workers = [
            w for w in st.session_state.workers
            if day not in leave_requests.get(w, [])
        ]

        if len(available_workers) < WORKERS_PER_DAY:
            todays_workers = available_workers
            status = "⚠️ Short Staffed"
        else:
            available_workers.sort(
                key=lambda x: worker_shift_counts[x]
            )
            todays_workers = available_workers[:WORKERS_PER_DAY]
            status = "OK"

        for w in todays_workers:
            worker_shift_counts[w] += 1

        roster_data.append({
            "Date": date_str,
            "Day": pd.to_datetime(date_str).day_name(),
            "Supervisor": supervisor_today,
            "Workers Assigned": ", ".join(todays_workers),
            "Worker Count": len(todays_workers),
            "Status": status
        })

    # ---------------- RESULTS ----------------
    df = pd.DataFrame(roster_data)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📋 Final Schedule")
        st.dataframe(df, use_container_width=True)

    with col2:
        st.subheader("📊 Worker Workload Balance")
        stats_df = (
            pd.DataFrame(worker_shift_counts.items(), columns=["Worker", "Shifts"])
            .set_index("Worker")
            .sort_values("Shifts", ascending=False)
        )
        st.bar_chart(stats_df)

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False),
        file_name="swiftroster.csv",
        mime="text/csv"
    )
