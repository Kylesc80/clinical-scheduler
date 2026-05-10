import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Clinical Scheduler", layout="wide")

st.title("🏥 Clinical Schedule Optimizer")
st.markdown("""
This tool generates an optimized grid-based schedule for hospital-based optometry, 
balancing clinical flow with **SullivanCotter** productivity benchmarks.
""")

# --- SIDEBAR: SCHEDULING PARAMETERS ---
st.sidebar.header("1. Session Timing")
start_time = st.sidebar.time_input("Clinic Start", value=datetime.strptime("08:00", "%H:%M"))
lunch_start_time = st.sidebar.time_input("Lunch Start", value=datetime.strptime("12:00", "%H:%M"))
lunch_min = st.sidebar.number_input("Lunch Duration (mins)", value=60, step=15)
end_time = st.sidebar.time_input("Clinic End", value=datetime.strptime("17:00", "%H:%M"))

st.sidebar.header("2. Grid & Buffers")
grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)
st.sidebar.info("Buffers are 2x your grid length for complex cases or charting.")
am_buffers = st.sidebar.slider("Morning Buffers", 0, 5, 3)
pm_buffers = st.sidebar.slider("Afternoon Buffers", 0, 5, 2)

# --- HELPER FUNCTION: SESSION GENERATOR ---
def generate_session_slots(session_start, session_end, buffer_limit, grid):
    session_data = []
    curr = session_start
    total_session_min = (session_end - session_start).total_seconds() / 60
    
    # Estimate total slots available in this window
    potential_slots = int(total_session_min // grid)
    
    if potential_slots <= 0:
        return []

    # Distribute buffers evenly
    buffers_placed = 0
    spacing = max(1, potential_slots // (buffer_limit + 1)) if buffer_limit > 0 else 99
    
    for i in range(1, potential_slots + 1):
        is_buffer = (buffers_placed < buffer_limit and i % spacing == 0)
        duration = grid * 2 if is_buffer else grid
        
        # Check if this slot fits within the session time
        if curr + timedelta(minutes=duration) > session_end + timedelta(minutes=1):
            break
            
        label = "🟠 Complex / Catch-up" if is_buffer else "🟢 Standard Exam"
        session_data.append({
            "Start Time": curr.strftime("%I:%M %p"),
            "Type": label,
            "Duration": duration  # Keep as int for math, format for display later
        })
        curr += timedelta(minutes=duration)
        if is_buffer: buffers_placed += 1
            
    return session_data

# --- DATA PROCESSING ---
clinic_start_dt = datetime.combine(datetime.today(), start_time)
lunch_start_dt = datetime.combine(datetime.today(), lunch_start_time)
lunch_end_dt = lunch_start_dt + timedelta(minutes=lunch_min)
clinic_end_dt = datetime.combine(datetime.today(), end_time)

# Generate morning and afternoon sessions
am_schedule = generate_session_slots(clinic_start_dt, lunch_start_dt, am_buffers, grid_inc)
pm_schedule = generate_session_slots(lunch_end_dt, clinic_end_dt, pm_buffers, grid_inc)

# Format for display
display_list = []
for item in am_schedule:
    display_list.append({"Start Time": item["Start Time"], "Type": item["Type"], "Duration": f"{item['Duration']} min"})

display_list.append({"Start Time": lunch_start_time.strftime("%I:%M %p"), "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"})

for item in pm_schedule:
    display_list.append({"Start Time": item["Start Time"], "Type": item["Type"], "Duration": f"{item['Duration']} min"})

# --- OUTPUT SECTION ---
st.subheader("Optimized Schedule Template")
df_display = pd.DataFrame(display_list)
st.table(df_display)

# --- METRICS & BENCHMARKING ---
st.divider()
patient_slots = am_schedule + pm_schedule
daily_pts = len(patient_slots)

if daily_pts > 0:
    total_clinical_mins = sum([x['Duration'] for x in patient_slots])
    avg_duration = total_clinical_mins / daily_pts
else:
    avg_duration = 0

m1, m2, m3 = st.columns(3)

with m1:
    st.metric("Daily Patient Volume", f"{daily_pts} Patients")
    st.caption("Total scheduled encounters")

with m2:
    st.metric("Avg. Appt Duration", f"{avg_duration:.1f} min")
    st.caption(f"Based on {grid_inc}m grid + buffers")

with m3:
    if daily_pts >= 15.9:
        st.success("Elite (90th+ %)")
    elif daily_pts >= 13.6:
        st.info("High Prod. (75th %)")
    elif daily_pts >= 11.4:
        st.warning("Median (50th %)")
    else:
        st.error("Below Median")
    st.caption("SullivanCotter Ranking")

st.info("**SullivanCotter Benchmarks (Hospital Optometry):** Median: 11.4 | 75th: 13.6 | 90th: 15.9")

# Export Option
csv = df_display.to_csv(index=False).encode('utf-8')
st.download_button("Download Schedule (CSV)", csv, "clinical_schedule.csv", "text/csv")
