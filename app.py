import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Hospital Optometry Dual Stress-Planner", layout="wide")

st.title("Hospital Optometry Session Template Optimization & Risk Dashboard")
st.markdown("""
This executive simulator evaluates the distinct operational impacts of **Morning vs. Afternoon overbooking** on clinic flow, 
mapping metrics directly to **SullivanCotter** throughput, **Press Ganey/NPS** satisfaction curves, and labor liabilities.
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

# --- UPDATED: SPLIT AM/PM OVERBOOK CONTROLLERS ---
st.sidebar.header("3. Overbook Simulation (By Session)")

if am_buffers > 0:
    am_overbooks = st.sidebar.slider(
        "AM Overbooked Slots", 
        0, int(am_buffers), 0,
        help="Converts morning catch-up blocks into double-booked slots (Post-ops / Urgent exams)."
    )
else:
    am_overbooks = 0
    st.sidebar.warning("⚠️ No AM catch-up slots configured.")

if pm_buffers > 0:
    pm_overbooks = st.sidebar.slider(
        "PM Overbooked Slots", 
        0, int(pm_buffers), 0,
        help="Converts afternoon catch-up blocks into double-booked slots (Post-ops / Urgent exams)."
    )
else:
    pm_overbooks = 0
    st.sidebar.warning("⚠️ No PM catch-up slots configured.")

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

# Process visual schedule layout with targeted overbooks injected
def process_session_display(session_slots, overbooks_left):
    session_list = []
    for item in session_slots:
        if item["Type"] == "🟠 Complex / Catch-up" and overbooks_left > 0:
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": "🚨 DOUBLE BOOKED (Catch-up + Post-Op/Problem Exam)", 
                "Duration": f"{item['Duration']} min (0m Net Buffer)"
            })
            overbooks_left -= 1
        else:
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": item["Type"], 
                "Duration": f"{item['Duration']} min"
            })
    return session_list

am_display = process_session_display(am_schedule, am_overbooks)
pm_display = process_session_display(pm_schedule, pm_overbooks)

display_list = am_display + [{"Start Time": lunch_start_time.strftime("%I:%M %p"), "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"}] + pm_display

# --- OUTPUT: SCHEDULE TEMPLATE ---
st.subheader("Simulated Grid Template (With Session-Specific Overbooks)")
df_display = pd.DataFrame(display_list)
st.table(df_display)

# --- METRICS & BENCHMARKING ---
st.divider()
st.subheader("📊 Operational & Productivity Analytics")

base_patient_slots = len(am_schedule) + len(pm_schedule)
total_daily_encounters = base_patient_slots + total_overbooks
effective_functional_buffers = max(0, total_configured_buffers - total_overbooks)

if base_patient_slots > 0:
    total_base_mins = sum([x['Duration'] for x in am_schedule + pm_schedule])
    avg_duration = total_base_mins / total_daily_encounters
else:
    avg_duration = 0

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(
        "Total Daily Volume", 
        f"{total_daily_encounters} Patients", 
        delta=f"+{total_overbooks} Overbooks" if total_overbooks > 0 else None
    )
    st.caption(f"Base Template: {base_patient_slots} | AM Overbooks: {am_overbooks} | PM Overbooks: {pm_overbooks}")
with m2:
    st.metric("Avg. Structural Space / Pt", f"{avg_duration:.1f} min")
    st.caption("Available appointment footprint compressed by overbook density")
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

# --- PRESS GANEY & NPS STRESS CONTEXT ---
st.divider()
st.subheader("📈 Patient Loyalty & Experience Forecasting")

# Recalculate operational wait time based on the REDUCED effective buffer ratio
effective_buffer_ratio = effective_functional_buffers / total_daily_encounters if total_daily_encounters > 0 else 0

if effective_buffer_ratio >= 0.35:
    expected_wait_time = 7  
elif effective_buffer_ratio >= 0.25:
    expected_wait_time = 14 
elif effective_buffer_ratio >= 0.15:
    expected_wait_time = 28 
else:
    # Adding weighting to show that PM overbooks accumulate worse wait times by end of day
    expected_wait_time = min(90, 28 + (am_overbooks * 10) + (pm_overbooks * 15)) 

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
    st.metric("Inferred Clinic Wait Time", f"{expected_wait_time} mins", 
              delta=f"{expected_wait_time - 15} mins vs Baseline" if expected_wait_time != 15 else None, 
              delta_color="inverse")
with pg_col2:
    st.metric("Press Ganey LTR Forecast", f"{pg_score:.1f}%")
    st.caption("Predicted 'Likelihood to Recommend' Top-Box %")
with pg_col3:
    st.metric("Inferred Net Promoter Score (NPS)", f"{nps_score:.1f}")
    st.caption("Brand Loyalty Index (-100 to +100)")

# --- CLINICAL QUALITY & ENTERPRISE RISK INFERENCES ---
st.divider()
st.subheader("🛡️ Quality Operations & Session Liabilities")

remaining_buffer_mins = (effective_functional_buffers * (grid_inc * 2))
allocated_chart_time_per_pt = remaining_buffer_mins / total_daily_encounters if total_daily_encounters > 0 else 0

empathy_score = "High" if avg_duration >= 23.0 else ("Moderate" if avg_duration >= 18.0 else "Compromised")

# Inferences driven by session specifics: AM overbooks impact lunch latency, PM overbooks force staff overtime
lunch_delay_risk = max(0, am_overbooks * 12)
pm_overtime_drift = max(0, (pm_overbooks * 18) + (max(0, expected_wait_time - 15) if pm_overbooks > 0 else 0))

q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if allocated_chart_time_per_pt >= 8.0:
        st.metric("Documentation Buffer space", f"{allocated_chart_time_per_pt:.1f} min/pt", "Low Compliance Risk")
    elif allocated_chart_time_per_pt >= 4.0:
        st.metric("Documentation Buffer space", f"{allocated_chart_time_per_pt:.1f} min/pt", "Elevated Charting Deficit", delta_color="off")
    else:
        st.metric("Documentation Buffer space", f"{allocated_chart_time_per_pt:.1f} min/pt", "High Compliance/Audit Risk", delta_color="inverse")
    st.caption("Net unallocated chart recovery room per patient file.")

with q_col2:
    if lunch_delay_risk == 0:
        st.success("Protected Lunch Interval")
    elif lunch_delay_risk <= 15:
        st.warning(f"⚡ Lunch Delay: ~{lunch_delay_risk} mins")
    else:
        st.error(f"🚨 Severe Lunch Compression: ~{lunch_delay_risk} mins")
    st.caption("Inferred morning template slip eating into provider/staff break window.")

with q_col3:
    if pm_overtime_drift <= 5:
        st.metric("End-of-Day Staff Overtime", "None (< 5m)", "Optimal Clinic Close")
    else:
        st.metric("End-of-Day Staff Overtime", f"+{int(pm_overtime_drift)} mins", "Staff Burnout Risk", delta_color="inverse")
    st.caption("Estimated afternoon clinical drift forcing unbudgeted hourly staff labor.")

# Export Option
csv = df_display.to_csv(index=False).encode('utf-8')
st.sidebar.markdown("---")
st.sidebar.download_button("📥 Export Current Simulation to CSV", csv, "hospital_optometry_session_sim.csv", "text/csv")
