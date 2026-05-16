import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Hospital Optometry Rigidity Stress-Planner", layout="wide")

st.title("Hospital Optometry Template Optimization & Risk Dashboard")
st.markdown("""
This simulator models template stress under strict operational constraints: 
* **Standard Exams / Complex Exams** require **20 minutes** of uninterrupted face-to-face contact time.
* An intact **Complex Block** (40m duration) yields a **20-minute charting remainder**.
* An **Overbooked Complex Block** injects a **10-minute focused exam**, yielding a **10-minute charting remainder**.
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

st.sidebar.header("3. 10-Min Overbook Simulation")
if am_buffers > 0:
    am_overbooks = st.sidebar.slider("AM 10-Min Overbooks", 0, int(am_buffers), 0)
else:
    am_overbooks = 0

if pm_buffers > 0:
    pm_overbooks = st.sidebar.slider("PM 10-Min Overbooks", 0, int(pm_buffers), 0)
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

am_base_slots = generate_session_slots(clinic_start_dt, lunch_start_dt, am_buffers, grid_inc)
pm_base_slots = generate_session_slots(lunch_end_dt, clinic_end_dt, pm_buffers, grid_inc)

total_am_mins = sum([x['Duration'] for x in am_base_slots])
total_pm_mins = sum([x['Duration'] for x in pm_base_slots])
total_clinic_day_mins = total_am_mins + total_pm_mins

# --- PARSE ENCOUNTERS EXPLICITLY TO FIX DENOMINATORS ---
def analyze_session(base_slots, overbooks_allotted):
    standards = 0
    intact_complex = 0
    overbooked_complex = 0
    overbook_patients = 0
    
    for slot in base_slots:
        if slot["Type"] == "🟢 Standard Exam":
            standards += 1
        elif slot["Type"] == "🟠 Complex / Catch-up":
            if overbooks_allotted > 0:
                overbooked_complex += 1
                overbook_patients += 1
                overbooks_allotted -= 1
            else:
                intact_complex += 1
                
    return standards, intact_complex, overbooked_complex, overbook_patients

am_standards, am_intact_comp, am_ob_comp, am_ob_pts = analyze_session(am_base_slots, am_overbooks)
pm_standards, pm_intact_comp, pm_ob_comp, pm_ob_pts = analyze_session(pm_base_slots, pm_overbooks)

# Absolute patient counts across the entire day
grand_total_standard = am_standards + pm_standards
grand_total_intact_complex = am_intact_comp + pm_intact_comp
grand_total_overbooked_complex = am_ob_comp + pm_ob_comp  # These contain 2 patients each

total_daily_encounters = grand_total_standard + grand_total_intact_complex + (grand_total_overbooked_complex * 2)
effective_functional_buffers = grand_total_intact_complex

# Visual Display Mapping
def process_session_display(session_slots, overbooks_left):
    session_list = []
    for item in session_slots:
        if item["Type"] == "🟠 Complex / Catch-up" and overbooks_left > 0:
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": "🚨 OVERBOOKED BLOCK (Complex Exam + 10m Injected Overbook)", 
                "Duration": "30m Contact Time Total (10m Remainder left for charting)"
            })
            overbooks_left -= 1
        elif item["Type"] == "🟠 Complex / Catch-up":
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": "🟠 Intact Complex / Catch-up Block", 
                "Duration": "20m Contact Time Total (20m Remainder left for charting)"
            })
        else:
            session_list.append({
                "Start Time": item["Start Time"], 
                "Type": item["Type"], 
                "Duration": f"{item['Duration']} min"
            })
    return session_list

am_display = process_session_display(am_base_slots, am_overbooks)
pm_display = process_session_display(pm_base_slots, pm_overbooks)
display_list = am_display + [{"Start Time": lunch_start_time.strftime("%I:%M %p"), "Type": "🍴 LUNCH BREAK", "Duration": f"{lunch_min} min"}] + pm_display

# --- OUTPUT: SCHEDULE TEMPLATE ---
st.subheader("Simulated Grid Template (Strict Contact Footprint Model)")
df_display = pd.DataFrame(display_list)
st.table(df_display)

# --- METRICS & BENCHMARKING ---
st.divider()
st.subheader("Operational & Productivity Analytics")

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Total Daily Volume", f"{total_daily_encounters} Patients", delta=f"+{total_overbooks} Overbooks" if total_overbooks > 0 else None)
    st.caption(f"Standard: {grand_total_standard} | Intact Complex: {grand_total_intact_complex} | Overbooked Complex Blocks: {grand_total_overbooked_complex}")
with m2:
    # Rigid contact constraint totals calculated explicitly
    total_face_to_face_mins = (grand_total_standard * 20.0) + (grand_total_intact_complex * 20.0) + (grand_total_overbooked_complex * 30.0)
    st.metric("Total Contact Time", f"{total_face_to_face_mins:.0f} mins")
    st.caption("Pure face-to-face physician contact requirement")
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
st.subheader("Patient Loyalty & Experience Forecasting")

effective_buffer_ratio = effective_functional_buffers / total_daily_encounters if total_daily_encounters > 0 else 0
if effective_buffer_ratio >= 0.35:
    expected_wait_time = 7  
elif effective_buffer_ratio >= 0.25:
    expected_wait_time = 14 
elif effective_buffer_ratio >= 0.15:
    expected_wait_time = 28 
else:
    expected_wait_time = min(90, 28 + (am_overbooks * 8) + (pm_overbooks * 14)) 

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

# --- QUALITY, CHARTING, AND LUNCH MATH ---
st.divider()
st.subheader("🛡️ Quality Operations & Session Liabilities")

# Calculating AM Session Specifics
am_contact_required = (am_standards * 20.0) + (am_intact_comp * 20.0) + (am_ob_comp * 30.0)
am_leftover_mins = max(0, total_am_mins - am_contact_required)
am_patients_total = am_standards + am_intact_comp + (am_ob_comp * 2)

# Benchmark: A safe charting speed requires 6 minutes of paperwork/documentation per encounter
target_chart_time_needed_am = am_patients_total * 6.0
am_charting_deficit = max(0, target_chart_time_needed_am - am_leftover_mins)

# Operational Inference: Charting deficit eats lunch
lunch_compression = min(lunch_min, am_charting_deficit)
net_rest_lunch = max(0, lunch_min - lunch_compression)

# Calculating PM Session Specifics
pm_contact_required = (pm_standards * 20.0) + (pm_intact_comp * 20.0) + (pm_ob_comp * 30.0)
pm_leftover_mins = max(0, total_pm_mins - pm_contact_required)
pm_patients_total = pm_standards + pm_intact_comp + (pm_ob_comp * 2)

target_chart_time_needed_pm = pm_patients_total * 6.0
pm_charting_deficit = max(0, target_chart_time_needed_pm - pm_leftover_mins)

# Operational Inference: PM charting deficit forces end-of-day overtime
pm_overtime_drift = pm_charting_deficit

# Global Net Chart Space Calculation
total_leftover_chart_mins = am_leftover_mins + pm_leftover_mins
true_chart_time_per_pt = total_leftover_chart_mins / total_daily_encounters if total_daily_encounters > 0 else 0

q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if true_chart_time_per_pt >= 6.0:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Optimal Structure")
    elif true_chart_time_per_pt >= 3.0:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Rushed Documentation Pace", delta_color="off")
    else:
        st.metric("Net Charting Space / Pt", f"{true_chart_time_per_pt:.1f} min", "Severe Backlog Risk", delta_color="inverse")
    st.caption("Available documentation minutes left over outside of face-to-face constraints.")

with q_col2:
    if lunch_compression == 0:
        st.success(f"Full Lunch Protected ({net_rest_lunch:.0f} mins remaining)")
    elif net_rest_lunch >= 30:
        st.warning(f"⚡ Lunch Compressed (Charity Charting: {lunch_compression:.0f}m | Rest: {net_rest_lunch:.0f}m)")
    else:
        st.error(f"🚨 Lunch Lost (Rest: {net_rest_lunch:.0f}m | Forced Charting: {lunch_compression:.0f}m)")
    st.caption("Minutes of the lunch window absorbed by morning documentation requirements.")

with q_col3:
    if pm_overtime_drift <= 5:
        st.metric("End-of-Day Overtime Drift", "None (< 5m)", "Optimal Session Close")
    else:
        st.metric("End-of-Day Overtime Drift", f"+{int(pm_overtime_drift)} mins", "Staff & Provider Burnout", delta_color="inverse")
    st.caption("Estimated clinic delay forced by unallocated afternoon documentation backlogs.")

# Export Option
csv = df_display.to_csv(index=False).encode('utf-8')
st.sidebar.markdown("---")
st.sidebar.download_button("📥 Export Audited Simulation to CSV", csv, "hospital_optometry_audited_sim.csv", "text/csv")
