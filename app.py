import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Hospital Optometry Enterprise Planner", layout="wide")

st.title("🏥 Hospital Optometry Template Optimizer & Enterprise Risk Dashboard")
st.markdown("""
This advanced executive dashboard maps hospital optometry template dynamics directly to 
**SullivanCotter** productivity, **Press Ganey/NPS** satisfaction metrics, and **Clinical Quality/Burnout** risk indices.
""")

# --- SIDEBAR: SCHEDULING PARAMETERS ---
st.sidebar.header("1. Clinic Session Timing")
start_time = st.sidebar.time_input("Clinic Start", value=datetime.strptime("08:00", "%H:%M"))
lunch_start_time = st.sidebar.time_input("Lunch Start", value=datetime.strptime("12:00", "%H:%M"))
lunch_min = st.sidebar.number_input("Lunch Duration (mins)", value=60, step=15)
end_time = st.sidebar.time_input("Clinic End", value=datetime.strptime("17:00", "%H:%M"))

st.sidebar.header("2. Template Grid & Buffers")
grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)
st.sidebar.info("Buffers are 2x your grid length, strategically placed to absorb testing/dilation delays and charting.")
am_buffers = st.sidebar.slider("Morning Buffers", 0, 5, 3)
pm_buffers = st.sidebar.slider("Afternoon Buffers", 0, 5, 2)

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

display_list = []
for item in am_schedule:
    display_list.append({"Start Time": item["Start Time"], "Type": item["Type"], "Duration": f"{item['Duration']} min"})
display_list.append({"Start Time": lunch_start_time.strftime("%I:%M %p"), "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"})
for item in pm_schedule:
    display_list.append({"Start Time": item["Start Time"], "Type": item["Type"], "Duration": f"{item['Duration']} min"})

# --- OUTPUT: SCHEDULE TEMPLATE ---
st.subheader("Optimized Schedule Template")
df_display = pd.DataFrame(display_list)
st.table(df_display)

# --- METRICS & BENCHMARKING ---
st.divider()
st.subheader("📊 Operational & Productivity Analytics")

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
    st.caption("Total scheduled encounters/day")
with m2:
    st.metric("Avg. Appt Duration", f"{avg_duration:.1f} min")
    st.caption(f"Template allocation space per patient")
with m3:
    if daily_pts >= 15.9:
        st.success("Elite Tier (90th Percentile)")
    elif daily_pts >= 13.6:
        st.info("High Productivity (75th Percentile)")
    elif daily_pts >= 11.4:
        st.warning("Median Tier (50th Percentile)")
    else:
        st.error("Below National Median")
    st.caption("SullivanCotter Benchmark Rank")

st.caption("**SullivanCotter Reference Framework (Hospital-Based Optometry):** Median: 11.4 | 75th: 13.6 | 90th: 15.9 encounters per day.")

# --- DUAL EXPERIENCE FORECASTING LOGIC ---
st.divider()
st.subheader("📈 Integrated Patient Loyalty & Experience Forecasting")

buffer_ratio = (am_buffers + pm_buffers) / daily_pts if daily_pts > 0 else 0

if buffer_ratio >= 0.35:
    expected_wait_time = 7  
elif buffer_ratio >= 0.25:
    expected_wait_time = 14 
elif buffer_ratio >= 0.15:
    expected_wait_time = 28 
else:
    expected_wait_time = 62 

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
              delta=f"{expected_wait_time - 15} mins vs Baseline Threshold", delta_color="inverse")
with pg_col2:
    st.metric("Press Ganey LTR Forecast", f"{pg_score:.1f}%")
    st.caption("Predicted 'Likelihood to Recommend' Top-Box %")
with pg_col3:
    st.metric("Inferred Net Promoter Score (NPS)", f"{nps_score:.1f}")
    st.caption("Brand Loyalty Index (-100 to +100)")

# --- NEW SECTION: CLINICAL QUALITY & RISK INFERENCES ---
st.divider()
st.subheader("🛡️ Clinical Quality & Provider Burnout Risk Assessment")
st.markdown("These metrics analyze the structural 'breathing room' required to maintain coding compliance and staff retention.")

# 1. Documentation Deficit Calculation
total_buffer_mins = ((am_buffers + pm_buffers) * (grid_inc * 2))
allocated_chart_time_per_pt = total_buffer_mins / daily_pts if daily_pts > 0 else 0

# 2. Perceived Empathy/Time Score Impact
empathy_score = "High" if avg_duration >= 23.0 else ("Moderate" if avg_duration >= 18.0 else "Compromised")

# 3. Staff Overtime Drift
overtime_drift_mins = max(0, expected_wait_time - 10)

q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if allocated_chart_time_per_pt >= 8.0:
        st.metric("Documentation Buffering", f"{allocated_chart_time_per_pt:.1f} min/pt", "Low Compliance Risk")
    elif allocated_chart_time_per_pt >= 4.0:
        st.metric("Documentation Buffering", f"{allocated_chart_time_per_pt:.1f} min/pt", "Elevated Charting Deficit", delta_color="off")
    else:
        st.metric("Documentation Buffering", f"{allocated_chart_time_per_pt:.1f} min/pt", "High Audit/Coding Risk", delta_color="inverse")
    st.caption("Target: ≥ 6 mins of template recovery time per patient to finish notes in-session.")

with q_col2:
    if empathy_score == "High":
        st.success("✨ Patient-Centric Pace (High Empathy)")
    elif empathy_score == "Moderate":
        st.warning("⚡ Standard Pace (Rushed Documentation)")
    else:
        st.error("🚨 Factory-Model Pace (Severe Burnout Risk)")
    st.caption("Inferred Press Ganey 'Time Spent with Provider' rating tier.")

with q_col3:
    if overtime_drift_mins <= 5:
        st.metric("Predicted Clinic Overtime Drift", "None (< 5m)", "Optimal Clinic Close")
    else:
        st.metric("Predicted Clinic Overtime Drift", f"+{overtime_drift_mins} mins", "Staff Burnout Risk", delta_color="inverse")
    st.caption("Estimated daily unbudgeted time clinic will run past close due to bottleneck math.")

# Export Option
csv = df_display.to_csv(index=False).encode('utf-8')
st.sidebar.markdown("---")
st.sidebar.download_button("📥 Export Template to CSV", csv, "hospital_optometry_comprehensive.csv", "text/csv")
