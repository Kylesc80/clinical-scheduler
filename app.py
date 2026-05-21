import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# --- CONFIGURATION & CLINICAL ASSUMPTIONS ---
CLINICAL_ASSUMPTIONS = {
    "std_contact_min": 20.0,
    "overbook_contact_min": 30.0,
    "req_chart_min_per_pt": 6.0,
    "lunch_duration_min": 60.0
}

st.set_page_config(page_title="Hospital Optometry Capacity & Quality Planner", layout="wide")

st.title("Hospital Optometry Template Optimization & Quality Inference Engine")
st.markdown("""
This strategic planning dashboard models administrative capacities, **downstream clinical quality outcomes**, and **patient experience (Press Ganey/NPS) forecasts**. 
Configure your calendar to evaluate capacity limits, quality spoilage, and brand perception risks.
""")

# --- ENGINE: CORE TRACKING FUNCTIONS ---
def generate_session_slots(session_start: datetime, session_end: datetime, buffer_limit: int, grid: int) -> list:
    """Generates the baseline scheduling grid with clock times."""
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
            "Time": curr.strftime("%I:%M %p"), 
            "Type": label, 
            "Duration": f"{duration} min"
        })
        
        curr += timedelta(minutes=duration)
        if is_buffer: 
            buffers_placed += 1
            
    return session_data

def analyze_session(base_slots: list, overbooks_allotted: int) -> tuple:
    """Counts slot types and distributes overbooks into buffer slots."""
    standards, intact_complex, overbooked_complex = 0, 0, 0
    for slot in base_slots:
        if slot["Type"] == "🟢 Standard Exam": 
            standards += 1
        elif slot["Type"] == "🟠 Complex / Catch-up":
            if overbooks_allotted > 0:
                overbooked_complex += 1
                overbooks_allotted -= 1
            else: 
                intact_complex += 1
    return standards, intact_complex, overbooked_complex

def process_session_metrics(base_template: list, overbooks: int, is_am: bool, session_type: str, template_mins: float) -> tuple:
    """Calculates patient volume, contact time, and temporal liabilities for a single session."""
    st_count, ic_count, oc_count = analyze_session(base_template, overbooks)
    
    pts = st_count + ic_count + (oc_count * 2)
    contact = (st_count * CLINICAL_ASSUMPTIONS["std_contact_min"]) + \
              (ic_count * CLINICAL_ASSUMPTIONS["std_contact_min"]) + \
              (oc_count * CLINICAL_ASSUMPTIONS["overbook_contact_min"])
              
    leftover = max(0, template_mins - contact)
    deficit = max(0, (pts * CLINICAL_ASSUMPTIONS["req_chart_min_per_pt"]) - leftover)
    
    lunch_lost = 0.0
    overtime = 0.0
    
    if is_am:
        if session_type == "Full Day":
            lunch_lost = min(CLINICAL_ASSUMPTIONS["lunch_duration_min"], deficit)
        else:
            overtime = deficit
    else:
        overtime = deficit
        
    return pts, contact, leftover, lunch_lost, overtime

# --- SIDEBAR: SYSTEM TIMING & BENCHMARKS ---
st.sidebar.header("1. Session Times & Core Parameters")

# Dynamic Time Inputs
am_start_str = st.sidebar.text_input("AM Session Start (HH:MM 24h)", "08:00")
am_end_str = st.sidebar.text_input("AM Session End / Lunch (HH:MM 24h)", "12:00")
pm_start_str = st.sidebar.text_input("PM Session Start (HH:MM 24h)", "13:00")
pm_end_str = st.sidebar.text_input("PM Session End (HH:MM 24h)", "17:00")

try:
    start_time = datetime.strptime(am_start_str, "%H:%M")
    lunch_start_time = datetime.strptime(am_end_str, "%H:%M")
    lunch_end_time = datetime.strptime(pm_start_str, "%H:%M")
    end_time = datetime.strptime(pm_end_str, "%H:%M")
except ValueError:
    st.sidebar.error("Please use HH:MM 24-hour format (e.g., 13:00).")
    st.stop()

grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)
am_buffers_per_session = st.sidebar.slider("AM Catch-up Slots (per session)", 0, 5, 3)
pm_buffers_per_session = st.sidebar.slider("PM Catch-up Slots (per session)", 0, 5, 2)

# Base templates generated for display and math
am_base_template = generate_session_slots(start_time, lunch_start_time, am_buffers_per_session, grid_inc)
pm_base_template = generate_session_slots(lunch_end_time, end_time, pm_buffers_per_session, grid_inc)

am_template_mins = (lunch_start_time - start_time).total_seconds() / 60
pm_template_mins = (end_time - lunch_end_time).total_seconds() / 60

# --- SIDEBAR: 7-DAY CALENDAR MATRIX ---
st.sidebar.header("2. Seven-Day Clinic Calendar")
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekly_config = {}

for day in days_of_week:
    with st.sidebar.expander(f"📆 {day}", expanded=(day in days_of_week[:5])):
        session_type = st.radio(
            f"Session Layout ({day})",
            ["Full Day", "Morning Only", "Afternoon Only", "Day Off"],
            index=0 if day in days_of_week[:5] else 3,
            key=f"layout_{day}"
        )
        
        am_ob, pm_ob = 0, 0
        if session_type in ["Full Day", "Morning Only"] and am_buffers_per_session > 0:
            am_ob = st.slider("AM Overbooks Inserted", 0, int(am_buffers_per_session), 0, key=f"am_ob_{day}")
        if session_type in ["Full Day", "Afternoon Only"] and pm_buffers_per_session > 0:
            pm_ob = st.slider("PM Overbooks Inserted", 0, int(pm_buffers_per_session), 0, key=f"pm_ob_{day}")
            
        weekly_config[day] = {"type": session_type, "am_overbooks": am_ob, "pm_overbooks": pm_ob}

# --- MAIN UI: BASELINE SCHEDULE TEMPLATES ---
st.subheader("Baseline Daily Schedule Template Grids")
st.markdown("This represents your structural capacity *before* dynamic overbooks are injected. Complex/Catch-up slots act as shock absorbers.")
col_t1, col_t2 = st.columns(2)
with col_t1:
    st.markdown("**AM Session Template**")
    st.dataframe(pd.DataFrame(am_base_template), use_container_width=True, hide_index=True)
with col_t2:
    st.markdown("**PM Session Template**")
    st.dataframe(pd.DataFrame(pm_base_template), use_container_width=True, hide_index=True)

# --- WEEKLY AGGREGATION LOOP ---
weekly_summary_data = []
metrics = {
    "patients": 0, "contact_mins": 0, "chart_mins": 0, 
    "lunch_lost": 0, "overtime": 0, "sessions": 0, 
    "poss_overbooks": 0, "act_overbooks": 0
}

for day, config in weekly_config.items():
    if config["type"] == "Day Off":
        weekly_summary_data.append({
            "Day": day, "Status": "❌ Day Off", "Patients": 0, 
            "Net Chart Space/Pt": "0.0m", "Lunch Liability": "Protected", "EOD Overtime": "0m"
        })
        continue
        
    d_pts = d_contact = d_chart = d_lunch = d_overtime = 0
    
    if config["type"] in ["Full Day", "Morning Only"]:
        metrics["sessions"] += 0.5
        metrics["poss_overbooks"] += am_buffers_per_session
        metrics["act_overbooks"] += config["am_overbooks"]
        pts, contact, chart, lunch, over = process_session_metrics(am_base_template, config["am_overbooks"], True, config["type"], am_template_mins)
        d_pts += pts; d_contact += contact; d_chart += chart; d_lunch += lunch; d_overtime += over

    if config["type"] in ["Full Day", "Afternoon Only"]:
        metrics["sessions"] += 0.5
        metrics["poss_overbooks"] += pm_buffers_per_session
        metrics["act_overbooks"] += config["pm_overbooks"]
        pts, contact, chart, lunch, over = process_session_metrics(pm_base_template, config["pm_overbooks"], False, config["type"], pm_template_mins)
        d_pts += pts; d_contact += contact; d_chart += chart; d_overtime += over

    avg_chart_space = (d_chart / d_pts) if d_pts > 0 else 0
    weekly_summary_data.append({
        "Day": day, "Status": f"⏱️ {config['type']}", "Patients": d_pts, 
        "Net Chart Space/Pt": f"{avg_chart_space:.1f} min", 
        "Lunch Liability": f"🚨 Lost {int(d_lunch)}m" if d_lunch > 0 else "🍱 Protected",
        "EOD Overtime": f"+{int(d_overtime)} mins" if d_overtime > 0 else "None"
    })
    
    metrics["patients"] += d_pts; metrics["contact_mins"] += d_contact
    metrics["chart_mins"] += d_chart; metrics["lunch_lost"] += d_lunch; metrics["overtime"] += d_overtime

implied_fte = metrics["sessions"] / 5.0

# --- OUTPUT: 7-DAY MATRIX & BENCHMARKS ---
st.divider()
st.subheader(f"Integrated Weekly Schedule Blueprint ({implied_fte:.2f} FTE)")
st.table(pd.DataFrame(weekly_summary_data))

st.subheader("Weekly Aggregated Analytics & Benchmark Matching")
m1, m2, m3 = st.columns(3)
m1.metric("Total Weekly Patient Volume", f"{metrics['patients']} Patients")
m2.metric("Weekly Face-to-Face Contact", f"{int(metrics['contact_mins'])} mins", f"Eqv. {metrics['contact_mins']/60:.1f} hrs")

estimated_annual_volume = metrics["patients"] * 48.0
fte_adjusted_volume = (estimated_annual_volume / implied_fte) if implied_fte > 0 else 0
if fte_adjusted_volume >= 3350: status, desc = "Elite Tier (90th Pctl)", "Top national clinical productivity."
elif fte_adjusted_volume >= 2850: status, desc = "High Productivity (75th)", "Strong volume performance profile."
elif fte_adjusted_volume >= 2400: status, desc = "Median Tier (50th Pctl)", "Aligned directly with national median."
else: status, desc = "Below National Median", "Volume falls behind mid-market baselines."
m3.metric("SullivanCotter Productivity", status, f"{int(fte_adjusted_volume):,} visits/yr")

# --- INFERENCES: CLINICAL QUALITY ---
global_chart_space = (metrics["chart_mins"] / metrics["patients"]) if metrics["patients"] > 0 else 0
overbook_saturation = (metrics["act_overbooks"] / metrics["poss_overbooks"]) if metrics["poss_overbooks"] > 0 else 0

st.divider()
st.subheader("Clinical Quality & Downstream Outcomes Inference")
q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if global_chart_space >= 6.0: stat, col, txt = "Baseline (Low)", "success", "Adequate exam cycle permits holistic diagnosis."
    elif global_chart_space >= 3.0: stat, col, txt = "Elevated (+14% Risk)", "warning", "Squeezing complex cases increases secondary complaint deferral."
    else: stat, col, txt = "Critical (+29% Risk)", "danger", "High probability of unresolved complaints causing spillover demand."
    st.markdown(f"### Repeat Visit Propensity\n**Status:** :{col}[{stat}]")
    st.info(txt)

with q_col2:
    if overbook_saturation <= 0.15: stat, col, txt = "Optimized", "success", "Ample buffers secure timely pathology tracking."
    elif overbook_saturation <= 0.50: stat, col, txt = "Compromised Continuity", "warning", "Rigid schedule pushes high-risk tracking past clinical targets."
    else: stat, col, txt = "Severe Continuity Spoilage", "danger", "Immediate access for active medical issues blocked."
    st.markdown(f"### Priority Follow-Up Spoilage\n**Status:** :{col}[{stat}]")
    st.info(txt)

with q_col3:
    if global_chart_space >= 5.5: stat, col, txt = "Safe Boundary", "success", "Sufficient space lowers errors in lab reviews/tracking."
    elif global_chart_space >= 3.0: stat, col, txt = "Moderate Fatigue", "warning", "Forced documentation gaps increase distractions."
    else: stat, col, txt = "High-Risk Diagnostic Fatigue", "danger", "Late-day EHR batching correlates with increased diagnostic errors."
    st.markdown(f"### EHR Diagnostic Error Risk\n**Status:** :{col}[{stat}]")
    st.info(txt)

# --- INFERENCES: PATIENT EXPERIENCE (Press Ganey & NPS) ---
st.divider()
st.subheader("Patient Experience & Brand Perception (Press Ganey & NPS)")
st.markdown("Wait times and perceived provider rushing are the dominant drivers of ambulatory patient satisfaction scores.")

p_col1, p_col2 = st.columns(2)
with p_col1:
    st.markdown("### Press Ganey: 'Time Spent with Provider'")
    if global_chart_space >= 5.5 and overbook_saturation <= 0.25:
        st.success("**Forecast: Top Decile (90th+ Percentile)**\n\nHigh probability of 5/5 scores. Unrushed template allows for conversational space and comprehensive clinical explanations.")
    elif global_chart_space >= 3.0:
        st.warning("**Forecast: Median Tier (40th - 60th Percentile)**\n\nProvider must actively manage the clock. Patients may perceive interactions as transactional rather than relational.")
    else:
        st.error("**Forecast: Bottom Quartile Risk (< 25th Percentile)**\n\nSevere charting deficits force the provider to truncate visits. High risk of 'rushed' or 'didn't listen' comments in free-text surveys.")

with p_col2:
    st.markdown("###Net Promoter Score (NPS): 'Likelihood to Recommend'")
    if overbook_saturation <= 0.20:
        st.success("**Forecast: Promoter Heavy (NPS 65 - 80+)**\n\nOn-time starts and minimal lobby waits drive strong word-of-mouth recommendations.")
    elif overbook_saturation <= 0.60:
        st.warning("**Forecast: Passive Zone (NPS 30 - 50)**\n\nLobby waits fluctuate. Patients are satisfied clinically but unlikely to actively advocate for the practice due to friction in access or wait times.")
    else:
        st.error("**Forecast: Detractor Risk (NPS < 20)**\n\nChronic overbooking causes compounding delays by mid-morning and mid-afternoon. Excessive wait times heavily penalize overall likelihood to recommend.")

# --- ADMINISTRATIVE LIABILITIES ---
st.divider()
st.subheader("Core Operational Liabilities Summary")
o1, o2, o3 = st.columns(3)
with o1:
    if global_chart_space >= 6.0: st.metric("Net Weekly Charting Space", f"{global_chart_space:.1f} min/pt", "Sustainable")
    elif global_chart_space >= 3.0: st.metric("Net Weekly Charting Space", f"{global_chart_space:.1f} min/pt", "Burnout Warning", delta_color="off")
    else: st.metric("Net Weekly Charting Space", f"{global_chart_space:.1f} min/pt", "Compliance Hazard", delta_color="inverse")
with o2:
    if metrics["lunch_lost"] == 0: st.success("Lunch Breaks Entirely Intact")
    else: st.error(f"Absorbed {int(metrics['lunch_lost'])} mins of rest time")
with o3:
    if metrics["overtime"] == 0: st.metric("Weekly Overtime Drift", "0 mins", "Clean Clinic Operations")
    else: st.metric("Weekly Overtime Drift", f"+{int(metrics['overtime'])} mins", "Staff & Provider Burnout", delta_color="inverse")
