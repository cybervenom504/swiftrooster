import streamlit as st
import pandas as pd
from calendar import monthrange
from datetime import datetime

st.set_page_config(page_title="SwiftRoster Pro: Leave Management", layout="wide")
st.title("📅 SwiftRoster: Fair Logic + Leave Requests")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("1. Core Settings")
staff_input = st.sidebar.text_area("Staff Names (comma separated)", 
                                   "Alice, Bob, Charlie, Diana, Edward, Fiona, George, Hannah")
target_per_day = st.sidebar.number_input("Staff Required Per Day", min_value=1, value=3)

st.sidebar.header("2. Date Selection")
month = st.sidebar.selectbox("Month", list(range(1, 13)), index=datetime.now().month - 1)
year = st.sidebar.number_input("Year", min_value=2024, max_value=2030, value=2026)

# --- LEAVE MANAGEMENT ---
st.sidebar.header("3. Blackout Dates (Optional)")
st.sidebar.info("Format: Name: Day (e.g., Alice: 5, Bob: 12)")
leave_input = st.sidebar.text_area("Enter Leave Requests")

# Process Inputs
staff_list = [s.strip() for s in staff_input.split(",") if s.strip()]
leave_requests = {}
if leave_input:
    for entry in leave_input.split(","):
        if ":" in entry:
            name, day = entry.split(":")
            name = name.strip()
            day = int(day.strip())
            if name not in leave_requests:
                leave_requests[name] = []
            leave_requests[name].append(day)

# --- ROSTER LOGIC ---
if st.button("Generate Roster with Leave Logic"):
    if len(staff_list) < target_per_day:
        st.error(f"Not enough staff to cover the {target_per_day} person requirement.")
    else:
        num_days = monthrange(year, month)[1]
        shift_counts = {name: 0 for name in staff_list}
        roster_data = []

        for day in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            
            # Filter out staff who are on leave today
            available_today = [
                name for name in staff_list 
                if day not in leave_requests.get(name, [])
            ]
            
            if len(available_today) < target_per_day:
                st.warning(f"⚠️ Short staffed on {date_str}! Only {len(available_today)} available.")
                todays_shift = available_today
            else:
                # Sort only the AVAILABLE staff by their current shift counts
                available_today.sort(key=lambda x: shift_counts[x])
                todays_shift = available_today[:target_per_day]
            
            # Update counts
            for person in todays_shift:
                shift_counts[person] += 1
                
            roster_data.append({
                "Date": date_str,
                "Day": pd.to_datetime(date_str).day_name(),
                "Staff Assigned": ", ".join(todays_shift)
            })

        # --- RESULTS ---
        df = pd.DataFrame(roster_data)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("### Final Schedule")
            st.dataframe(df, use_container_width=True)
        
        with col2:
            st.write("### Workload Balance")
            stats_df = pd.DataFrame(shift_counts.items(), columns=["Staff", "Shifts"]).set_index("Staff")
            st.bar_chart(stats_df)

        st.download_button("📥 Download Excel/CSV", df.to_csv(index=False), "roster.csv")
