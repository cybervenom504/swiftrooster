import streamlit as st
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Supervisor & Worker Assignment",
    layout="wide"
)

st.title("🧑‍✈️ Supervisor & Worker Assignment Manager")

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
        "SUPERVISOR A": [],
        "SUPERVISOR B": [],
        "SUPERVISOR C": []
    }

# ---------------- SIDEBAR ----------------
st.sidebar.header("👷 Worker Management")

new_worker = st.sidebar.text_input("Add Worker")
if st.sidebar.button("➕ Add Worker"):
    if new_worker:
        name = new_worker.strip().upper()
        if name not in st.session_state.workers:
            st.session_state.workers.append(name)

st.sidebar.subheader("Current Workers")
for w in st.session_state.workers:
    st.sidebar.write("•", w)

st.sidebar.divider()

st.sidebar.header("🧑‍✈️ Supervisor Management (3 Total)")

for i in range(3):
    sup_name = st.sidebar.text_input(
        f"Supervisor {i+1}",
        st.session_state.supervisors[i],
        key=f"sup_name_{i}"
    ).upper()

    old_name = st.session_state.supervisors[i]
    st.session_state.supervisors[i] = sup_name

    # Preserve assignments if name changes
    if old_name != sup_name:
        st.session_state.supervisor_assignments[sup_name] = (
            st.session_state.supervisor_assignments.pop(old_name, [])
        )

    assigned_workers = st.sidebar.multiselect(
        f"{sup_name} → Assign up to 8 workers",
        st.session_state.workers,
        default=st.session_state.supervisor_assignments.get(sup_name, []),
        key=f"sup_assign_{i}"
    )

    if len(assigned_workers) > 8:
        st.sidebar.warning("⚠️ Maximum is 8 workers per supervisor")

    st.session_state.supervisor_assignments[sup_name] = assigned_workers

# ---------------- MAIN DISPLAY ----------------
st.subheader("📋 Supervisor → Worker Assignments")

assignment_data = []
for sup in st.session_state.supervisors:
    workers = st.session_state.supervisor_assignments.get(sup, [])
    assignment_data.append({
        "Supervisor": sup,
        "Assigned Workers": ", ".join(workers),
        "Worker Count": len(workers)
    })

df_assignments = pd.DataFrame(assignment_data)
st.dataframe(df_assignments, use_container_width=True)

# ---------------- VALIDATION SUMMARY ----------------
st.subheader("✅ Validation Summary")

for sup, workers in st.session_state.supervisor_assignments.items():
    if len(workers) == 8:
        st.success(f"{sup} has exactly 8 workers assigned.")
    elif len(workers) < 8:
        st.warning(f"{sup} has {len(workers)} / 8 workers.")
    else:
        st.error(f"{sup} exceeds 8 workers!")

# ---------------- EXPORT ----------------
st.subheader("📥 Export")

st.download_button(
    "Download Supervisor Assignments (CSV)",
    df_assignments.to_csv(index=False),
    file_name="supervisor_worker_assignments.csv",
    mime="text/csv"
)
