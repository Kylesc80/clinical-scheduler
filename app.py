import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Config
st.set_page_config(page_title="Clinical Scheduler", layout="centered")

st.title("🏥 Clinical Schedule Optimizer")
st.markdown("""
This tool generates an optimized grid-based schedule for hospital optometry, 
aligning productivity with **SullivanCotter** benchmarks.
""")

# --- SIDEBAR: SCHEDULING PARAMETERS ---
st.sidebar.header("1. Time & Grid")
start_time = st.sidebar.time_input("Start Time", value=datetime.strptime("08:00", "%H:%M"))
end_time = st.sidebar.time_input("End Time", value=datetime.strptime("17:00", "%H:%M"))
lunch_min = st.sidebar.number_input("Lunch Duration (mins)", value=60, step=15)
grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)

st.sidebar.header("2. Buffer/Complex Slots")
st.sidebar.info("These slots are 2x your base grid length for charting or complex cases.")
am_buffers = st.sidebar.slider("Morning Buffers", 0, 5, 3)
pm_buffers = st.sidebar.slider("Afternoon Buffers", 0, 5, 2)

# --- CALCULATIONS ---
start_dt = datetime.combine(datetime.today(), start_time)
end_dt = datetime.combine(datetime.today(), end_time)
total_day_min = (end_dt - start_dt).total_seconds() / 60
available_clinical_min = total_day_min - lunch_min

# Calculate number of base slots available
total_potential_slots = int(available_clinical_min // grid_inc)

# --- TEMPLATE GENERATOR ---
schedule_data = []
curr = start_dt

def build_session(slot_count, buffer_limit):
    global curr
    buffers_placed = 0
    # Distribute buffers evenly across the session slots
    spacing = max(1, slot_count // (buffer_limit + 1)) if buffer_limit > 0 else 99
    
    for i in range(1, slot_count + 1):
        is_buffer = False
        if buffers_placed < buffer_limit and i % spacing == 0:
            is_buffer = True
            buffers_placed += 1
            
        duration = grid_inc * 2 if is_buffer else grid_inc
        label = "🟢 Standard Exam" if not is_buffer else "🟠 Complex / Catch-up"
        
        # Prevent overflowing past end time
        if curr + timedelta(minutes=duration) > end_dt + timedelta(minutes=1):
            break
            
        schedule_data.append({
            "Start Time": curr.strftime("%I:%M %p"),
            "Type": label,
            "Duration": f"{duration} min"
        })
        curr += timedelta(minutes=duration)

# Divide slots roughly in half for AM/PM
am_slots_est = total_potential_slots // 2

st.subheader("Interactive Schedule Template")

# AM Session
build_session(am_slots_est, am_buffers)

# Lunch
schedule_data.append({"Start Time": "---", "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"})
curr += timedelta(minutes=lunch_min)

# PM Session
pm_slots_est = total_potential_slots - am_slots_est
build_session(pm_slots_est, pm_buffers)

# Display Table
df = pd.DataFrame(schedule_data)
st.table(df)

# --- BENCHMARKING ---
st.divider()
daily_pts = len([x for x in schedule_data if "Exam" in x['Type'] or "Complex" in x['Type']])

col1, col2 = st.columns(2)
with col1:
    st.metric("Daily Patient Volume", f"{daily_pts} Patients")

with col2:
    if daily_pts >= 15.9:
        st.success("Elite Tier (90th+ %)")
    elif daily_pts >= 13.6:
        st.info("High Productivity (75th %)")
    elif daily_pts >= 11.4:
        st.warning("Median (50th %)")
    else:
        st.error("Below Median")

st.caption("SullivanCotter Benchmarks: Median=11.4 | 75th=13.6 | 90th=15.9 (Encounters/Day)")
