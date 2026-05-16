import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Hospital Optometry Catch-up Planner", layout="wide")

st.title("Hospital Optometry Session Template Optimization & Risk Dashboard")
st.markdown("""
This simulator evaluates the impact of routing **10-minute overbooks directly into 40-minute Catch-up blocks**. 
This packs 30 minutes of contact time into the block, leaving a compressed 10-minute recovery remainder.
""")

# --- SIDEBAR: SCHEDULING PARAMETERS ---
st.sidebar.header("1. Clinic Session Timing")
start_time = st.sidebar.time_input("Clinic Start", value=datetime.strptime("08:00", "%H:%M"))
lunch_start_time = st.sidebar.time_input("Lunch Start", value=datetime.strptime("12:00", "%H:%M"))
lunch_min = st.sidebar.number_input("Lunch Duration (mins)", value=60, step=15)
end_time = st.sidebar.time_input("Clinic End", value=datetime.strptime("17:00", "%H:%M"))

st.sidebar.header("2. Template Grid & Buffers")
grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)
am_buffers = st.sidebar.slider("Morning Catch-up Slots (AM Buffers)", 0, 5, 3)
pm_buffers = st.sidebar.slider("Afternoon Catch-up Slots (PM Buffers)", 0, 5, 2)

st.sidebar.header("3. Overbook Allocation Controller")
if am_buffers > 0:
    am_overbooks = st.sidebar.slider(
        "AM Overbooks (Consumes Catch-up Space)", 
        0, int(am_buffers), 0,
        help="Converts a 40m catch-up block into 30m of contact time and a 10m remainder."
    )
else:
    am_overbooks = 0

if pm_buffers > 0:
    pm_overbooks = st.sidebar.slider(
        "PM Overbooks (Consumes Catch-up Space)", 
        0, int(pm_buffers), 0,
        help="Converts a 40m catch-up block into 30m of contact time and a 10m remainder."
    )
else:
    pm_overbooks = 0

total_overbooks = am_overbooks + pm_overbooks
total_configured_buffers = am_buffers + pm_buffers

# --- HELPER FUNCTION: SESSION GENERATOR ---
def generate_session_slots(session_start, session_end, buffer_limit, grid):
    session_data = []
    curr = session_start
    total_session_min = (session_end - session_start).total_seconds() / 60
    
    potential_slots = int(total_session_min // grid)
    if potential_slots <= 0:
        return []

    buffers_placed = 0
    spacing = max(1, potential_slots // (buffer_limit + 1)) if buffer_limit > 0 else 99
    
    for i in range(1, potential_slots + 1):
        is_buffer = (buffers_placed < buffer_limit and i % spacing == 0)
        duration = grid * 2 if is_buffer else grid
        
        if curr + timedelta(minutes=duration) > session_end + timedelta(minutes=1):
            break
            
        label = "🟠 Complex / Catch-up" if is_buffer else "🟢 Standard Exam"
        session_data.append({
            "Start Time": curr.strftime("%I:%M %p"),
            "Type": label,
            "Duration": duration  
        })
        curr += timedelta(minutes=duration)
        if is_buffer: buffers_placed += 1
            
    return session_data

# --- DATA PROCESSING ---
clinic_start_dt = datetime.combine(datetime.today(), start_time)
lunch_start_dt = datetime.combine(datetime.today(), lunch_start_time)
lunch_end_dt = lunch_start_dt + timedelta(minutes=lunch_min)
clinic_end_dt = datetime.combine(datetime.today(), end_time)

am_schedule = generate_session_slots(clinic_start_dt, lunch_start_dt, am_buffers, grid_inc)
pm_schedule = generate_session_slots(lunch_end_dt, clinic_end_dt, pm_buffers, grid_inc)

total_am_mins = sum([x['Duration'] for x in am_schedule])
total_pm_mins = sum([x['Duration'] for x in pm_schedule])
total_clinic_day_mins = total_am_mins + total_pm_mins

base_standards = sum(1 for x in (am_schedule + pm_schedule) if x["Type"] == "🟢 Standard Exam")
base_catchups = sum(1 for x in (am_schedule + pm_schedule) if x["Type"] == "🟠 Complex / Catch-up")

# --- GRID RENDERING LOGIC (ABSORBING OVERBOOKS INTO THE CATCH-UP SLOT) ---
def process_catchup_display(session_slots, overbooks_count):
    session_list = []
    overbooks_left = overbooks_count
    
    for item in session_slots:
        if item["Type"] == "🟠 Complex / Catch-up" and overbooks_left > 0:
            session_list.append({
                "Start Time": item["Start Time"],
                "Type": "🚨 Overbook (Complex Exam + 10m Overbook)",
                "Duration": "30 min Contact Time | 10 min Catch-up Remainder"
            })
            overbooks_left -= 1
        else:
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": item["Type"], 
                "Duration": f"{item['Duration']} min"
            })
    return session_list

am_display = process_catchup_display(am_schedule, am_overbooks)
pm_display = process_catchup_display(pm_schedule, pm_overbooks)
display_list = am_display + [{"Start Time": lunch_start_time.strftime("%I:%M %p"), "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"}] + pm_display

# --- OUTPUT: SCHEDULE TEMPLATE ---
st.subheader("Simulated Grid Template (With Absorbed Catch-Up Overbooks)")
df_display = pd.DataFrame(display_list)
st.table(df_display)

# --- METRICS & BENCHMARKING ---
st.divider()
st.subheader("Operational & Productivity Analytics")

total_daily_encounters = base_standards + base_catchups + total_overbooks
intact_catchups = max(0, base_catchups - total_overbooks)

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Total Daily Volume", f"{total_daily_encounters} Patients", delta=f"+{total_overbooks} Overbooks" if total_overbooks > 0 else None)
    st.caption(f"Standard Exam Slots: {base_standards} | Intact Catch-up Blocks: {intact_catchups} | Shared Overbook Blocks: {total_overbooks}")
with m2:
    avg_space = total_clinic_day_mins / total_daily_encounters if total_daily_encounters > 0 else 0
    st.metric("Avg. Template Space / Pt", f"{avg_space:.1f} min")
    st.caption("Prorated timeline footprint per encounter file")
with m3:
    if total_daily_encounters >= 15.9:
        st.success("Elite Tier (90th Percentile)")
    elif total_daily_encounters >= 13.6:
        st.info("High Productivity (75th Percentile)")
    elif total_daily_encounters >= 11.4:
        st.warning("Median Tier (50th Percentile)")
    else:
        st.error("Below National Median")
    st.caption("SullivanCotter Benchmark Rank")

# --- PRESS GANEY & NPS CONTEXT ---
st.divider()
st.subheader("Patient Loyalty & Experience Forecasting")

# Since overbooks fit inside the 40m footprint, wait times swell more gently than standard stacking
if total_overbooks == 0:
    expected_wait_time = 7
else:
    expected_wait_time = min(90, 10 + (am_overbooks * 6) + (pm_overbooks * 9))

base_pg_ltr = 89.2
base_nps = 56.0

if expected_wait_time <= 15:
    pg_score = base_pg_ltr
    nps_score = base_nps
elif expected_wait_time <= 30:
    pg_score = base_pg_ltr - ((expected_wait_time - 15) * 0.8)
    nps_score = base_nps - ((expected_wait_time - 15) * 1.5)
else:
    pg_score = base_pg_ltr - 12 - ((expected_wait_time - 30) * 1.4)
    nps_score = base_nps - 22.5 - ((expected_wait_time - 30) * 3.2) 

pg_score = max(35.0, pg_score)
nps_score = max(-100.0, nps_score)

pg_col1, pg_col2, pg_col3 = st.columns(3)
with pg_col1:
    st.metric("Inferred Clinic Wait Time", f"{expected_wait_time} mins", delta=f"{expected_wait_time - 15} mins vs Baseline" if expected_wait_time != 15 else None, delta_color="inverse")
with pg_col2:
    st.metric("Press Ganey LTR Forecast", f"{pg_score:.1f}%")
with pg_col3:
    st.metric("Inferred Net Promoter Score (NPS)", f"{nps_score:.1f}")

# --- MATHEMATIONALLY PERFECT DOCUMENTATION ACCOUNTING ---
st.divider()
st.subheader("Quality Operations & Session Liabilities")

# Strict Geometry Breakdown:
# 1. Every Standard Exam has 20m grid space. (15m face-time + 5m built-in chart time)
# 2. Every Intact Catch-up block has 40m grid space. (15m face-time + 25m built-in chart time)
# 3. Every Overbooked Catch-up block has 40m grid space. (30m total face-time + 10m chart remainder)

total_chart_mins = (base_standards * 5.0) + (intact_catchups * 25.0) + (total_overbooks * 10.0)
true_chart_time_per_pt = total_chart_mins / total_daily_encounters if total_daily_encounters > 0 else 0

# Delays and overtime risk scale smoothly as catch-up buffers shrink down to 10 minutes
lunch_delay_risk = max(0, am_overbooks * 5)
pm_overtime_drift = max(0, (pm_overbooks * 8) + (max(0, expected_wait_time - 15) if pm_overbooks > 0 else 0))

q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if true_chart_time_per_pt >= 6.0:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Optimal Documentation Window")
    elif true_chart_time_per_pt >= 4.0:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Rushed Note Completion", delta_color="off")
    else:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Severe Charting Deficit (Audit Risk)", delta_color="inverse")
    st.caption("True remaining documentation room per patient file across the whole session day.")

with q_col2:
    if lunch_delay_risk == 0:
        st.success("Protected Lunch Interval")
    elif lunch_delay_risk <= 10:
        st.warning(f"⚡ Lunch Delay: ~{lunch_delay_risk} mins")
    else:
        st.error(f"🚨 Severe Lunch Compression: ~{lunch_delay_risk} mins")

with q_col3:
    if pm_overtime_drift <= 5:
        st.metric("End-of-Day Staff Overtime", "None (< 5m)", "Optimal Clinic Close")
    else:
        st.metric("End-of-Day Staff Overtime", f"+{int(pm_overtime_drift)} mins", "Staff Burnout Risk", delta_color="inverse")

# Export Option
csv = df_display.to_csv(index=False).encode('utf-8')
st.sidebar.markdown("---")
st.sidebar.download_button("📥 Export Simulation to CSV", csv, "hospital_optometry_catchup_sim.csv", "text/csv")
