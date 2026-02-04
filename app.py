import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SwiftRoster Pro",
    layout="wide"
)

st.title("📅 SwiftRoster Pro – Official Roster & Payout Sheet")

# ---------------- CONSTANT RULES ----------------
WORKERS_PER_DAY = 8
TOTAL_SUPERVISORS = 3

# ---------------- SESSION STATE ----------------
if "workers" not in st.session_state:
    st.session_state.workers = [
        "ONYEWUJI", "NDIMELE", "BELLO", "FASEYE",
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
st.sidebar.header("2️⃣ Supervisor Management")

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
    "Year", min_value=2024, max_value=2035, value=2026
)

num_days = monthrange(year, month)[1]

# ---------------- LEAVE MANAGEMENT ----------------
st.sidebar.header("4️⃣ Leave / Blackout Dates")
st.sidebar.info(
    "Format (one per line):\n"
    "ONYEWUJI: 5, 6, 7\n"
    "SUPERVISOR A: 12"
)

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
if st.button("🚀 Generate Official Roster"):

    if len(st.session_state.workers) < WORKERS_PER_DAY:
        st.error("❌ Not enough workers to meet daily requirement.")
        st.stop()

    # ---- SHIFT COUNTS ----
    worker_shift_counts = {w: 0 for w in st.session_state.workers}
    supervisor_shift_counts = {s: 0 for s in st.session_state.supervisors}

    # ---- MASTER ROSTER GRID (SINGLE SOURCE OF TRUTH) ----
    roster_grid = {}

    roster_grid["DATE"] = [str(d) for d in range(1, num_days + 1)]
    roster_grid["DAY"] = [
        pd.to_datetime(f"{year}-{month:02d}-{d:02d}").strftime("%a")[0]
        for d in range(1, num_days + 1)
    ]
    roster_grid["SUPERVISOR"] = [""] * num_days

    for worker in st.session_state.workers:
        roster_grid[worker] = ["X"] * num_days

    # ---- DAILY ASSIGNMENT LOOP ----
    for day in range(1, num_days + 1):
        idx = day - 1

        # ----- SUPERVISOR SELECTION -----
        available_supervisors = [
            s for s in st.session_state.supervisors
            if day not in leave_requests.get(s, [])
        ]

        if available_supervisors:
            supervisor_today = min(
                available_supervisors,
                key=lambda x: supervisor_shift_counts[x]
            )
            supervisor_shift_counts[supervisor_today] += 1
        else:
            supervisor_today = "NO SUPERVISOR"

        roster_grid["SUPERVISOR"][idx] = supervisor_today

        # ----- WORKER SELECTION -----
        available_workers = [
            w for w in st.session_state.workers
            if day not in leave_requests.get(w, [])
        ]

        available_workers.sort(key=lambda x: worker_shift_counts[x])
        todays_workers = available_workers[:WORKERS_PER_DAY]

        for worker in st.session_state.workers:
            if day in leave_requests.get(worker, []):
                roster_grid[worker][idx] = "L"
            elif worker in todays_workers:
                roster_grid[worker][idx] = "M"
                worker_shift_counts[worker] += 1
            else:
                roster_grid[worker][idx] = "X"

    # ---- FINAL DATAFRAME (DISPLAY = EXPORT) ----
    master_df = pd.DataFrame.from_dict(
        roster_grid,
        orient="index"
    )

    master_df.insert(0, "NAME", master_df.index)
    master_df.reset_index(drop=True, inplace=True)

    # ---- CALCULATE WORKLOAD ----
    workload = {}
    for worker in st.session_state.workers:
        # Count how many "M" (working days) each worker has
        workload[worker] = sum(1 for val in roster_grid[worker] if val == "M")

    # Append workload row at the bottom of the dataframe
    workload_row = {"NAME": "WORKLOAD", "DATE": "", "DAY": "", "SUPERVISOR": ""}
    for worker in st.session_state.workers:
        workload_row[worker] = workload[worker]

    master_df = pd.concat([master_df, pd.DataFrame([workload_row])], ignore_index=True)

    # ---------------- DISPLAY ----------------
    st.subheader("📋 Official Roster (What You See = What You Download)")
    st.dataframe(master_df, use_container_width=True)

    # ---------------- DOWNLOAD ----------------
    st.download_button(
        "📥 Download CSV (Exact Layout)",
        master_df.to_csv(index=False),
        file_name="swiftroster_official.csv",
        mime="text/csv"
    )
