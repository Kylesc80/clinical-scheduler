import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# --- CONFIGURATION & CLINICAL ASSUMPTIONS ---
CLINICAL_ASSUMPTIONS = {
    "std_contact_min": 20.0,
    "overbook_contact_min": 30.0,
    "req_chart_min_per_pt": 6.0,
    "lunch_duration_min": 60.0
}

st.set_page_config(page_title="Hospital Optometry Capacity & Simulation Engine", layout="wide")

st.title("Hospital Optometry Capacity Planner & Market Dynamics Simulator")
st.markdown("""
This advanced operational dashboard models administrative capacities, late arrival thresholds, and features a 
12-Week System Dynamics Simulator to project how schedule saturation actively erodes long-term patient market demand via word-of-mouth feedback.
""")

# --- ENGINE: CORE TRACKING FUNCTIONS ---
def generate_session_slots(session_start: datetime, session_end: datetime, buffer_limit: int, grid: int) -> list:
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

def process_session_metrics(base_template: list, overbooks: int, is_am: bool, session_type: str, template_mins: float, no_show_pct: float) -> tuple:
    st_count, ic_count, oc_count = analyze_session(base_template, overbooks)
    
    pts_scheduled = st_count + ic_count + (oc_count * 2)
    pts_seen = pts_scheduled * (1.0 - (no_show_pct / 100.0))
    
    base_contact = (st_count * CLINICAL_ASSUMPTIONS["std_contact_min"]) + \
                   (ic_count * CLINICAL_ASSUMPTIONS["std_contact_min"]) + \
                   (oc_count * CLINICAL_ASSUMPTIONS["overbook_contact_min"])
    actual_contact = base_contact * (1.0 - (no_show_pct / 100.0))
              
    leftover = max(0, template_mins - actual_contact)
    deficit = max(0, (pts_seen * CLINICAL_ASSUMPTIONS["req_chart_min_per_pt"]) - leftover)
    
    lunch_lost, overtime = 0.0, 0.0
    if is_am:
        if session_type == "Full Day": lunch_lost = min(CLINICAL_ASSUMPTIONS["lunch_duration_min"], deficit)
        else: overtime = deficit
    else:
        overtime = deficit
        
    return pts_seen, pts_scheduled, actual_contact, leftover, lunch_lost, overtime

# --- SIDEBAR: SYSTEM TIMING & BENCHMARKS ---
st.sidebar.header("1. Session Times & Core Parameters")

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
    st.sidebar.error("Please use HH:MM 24-hour format.")
    st.stop()

grid_inc = st.sidebar.selectbox("System Grid Increment (mins)", [10, 15, 20, 30], index=2)
am_buffers_per_session = st.sidebar.slider("AM Catch-up Slots", 0, 5, 3)
pm_buffers_per_session = st.sidebar.slider("PM Catch-up Slots", 0, 5, 2)
no_show_rate = st.sidebar.slider("Clinic No-Show Rate (%)", 0, 40, 12)

# --- SIDEBAR: SIMULATION ENGINE PARAMETERS ---
st.sidebar.header("2. Market Simulation Tuning")
init_demand = st.sidebar.slider("Initial Weekly Demand (Requests)", 30, 120, 75)
market_elasticity = st.sidebar.slider("Market Sensitivity (Elasticity)", 0.01, 0.15, 0.06, step=0.01)

# --- SIDEBAR MODULE: FINANCIAL PARAMETERS WITH OPTICAL TOGGLE ---
st.sidebar.header("3. Financial Overlay Inputs")
has_optical = st.sidebar.toggle(
    "Location Has Optical Shop", 
    value=True, 
    help="Toggle off for satellite clinics, medical-only settings, or regional centers that do not fulfill hardware prescriptions on-site."
)

if has_optical:
    rev_per_encounter = st.sidebar.slider(
        "Global Revenue / Visit ($)", 
        min_value=100, max_value=450, value=225, step=25,
        help="Combined value of exam billings, professional fees, and total downstream retail optical material capture (frames, lenses, contact lenses)."
    )
else:
    rev_per_encounter = st.sidebar.slider(
        "Professional Fee Revenue / Visit ($)", 
        min_value=40, max_value=250, value=115, step=5,
        help="Professional clinical revenue and insurance reimbursement only. Excludes hardware product sales."
    )

# --- SIDEBAR: 7-DAY CALENDAR MATRIX ---
st.sidebar.header("4. Seven-Day Clinic Calendar")
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekly_config = {}

for day in days_of_week:
    with st.sidebar.expander(day, expanded=(day in days_of_week[:5])):
        session_type = st.radio(f"Layout ({day})", ["Full Day", "Morning Only", "Afternoon Only", "Day Off"], key=f"lay_{day}")
        am_ob, pm_ob = 0, 0
        if session_type in ["Full Day", "Morning Only"] and am_buffers_per_session > 0:
            am_ob = st.slider("AM Overbooks", 0, int(am_buffers_per_session), 3, key=f"am_ob_{day}")
        if session_type in ["Full Day", "Afternoon Only"] and pm_buffers_per_session > 0:
            pm_ob = st.slider("PM Overbooks", 0, int(pm_buffers_per_session), 2, key=f"pm_ob_{day}")
        weekly_config[day] = {"type": session_type, "am_overbooks": am_ob, "pm_overbooks": pm_ob}

# Base templates generated
am_base_template = generate_session_slots(start_time, lunch_start_time, am_buffers_per_session, grid_inc)
pm_base_template = generate_session_slots(lunch_end_time, end_time, pm_buffers_per_session, grid_inc)
am_template_mins = (lunch_start_time - start_time).total_seconds() / 60
pm_template_mins = (end_time - lunch_end_time).total_seconds() / 60

# --- RUN STATIONARY WEEKLY AGGREGATION LOOP ---
metrics = {"patients_seen": 0.0, "patients_sched": 0, "contact_mins": 0.0, "chart_mins": 0.0, "lunch_lost": 0.0, "overtime": 0.0, "sessions": 0.0, "poss_overbooks": 0, "act_overbooks": 0}

for day, config in weekly_config.items():
    if config["type"] == "Day Off": continue
    if config["type"] in ["Full Day", "Morning Only"]:
        metrics["sessions"] += 0.5; metrics["poss_overbooks"] += am_buffers_per_session; metrics["act_overbooks"] += config["am_overbooks"]
        pts_seen, pts_sched, contact, chart, lunch, over = process_session_metrics(am_base_template, config["am_overbooks"], True, config["type"], am_template_mins, no_show_rate)
        metrics["patients_seen"] += pts_seen; metrics["patients_sched"] += pts_sched; metrics["contact_mins"] += contact; metrics["chart_mins"] += chart; metrics["lunch_lost"] += lunch; metrics["overtime"] += over
    if config["type"] in ["Full Day", "Afternoon Only"]:
        metrics["sessions"] += 0.5; metrics["poss_overbooks"] += pm_buffers_per_session; metrics["act_overbooks"] += config["pm_overbooks"]
        pts_seen, pts_sched, contact, chart, lunch, over = process_session_metrics(pm_base_template, config["pm_overbooks"], False, config["type"], pm_template_mins, no_show_rate)
        metrics["patients_seen"] += pts_seen; metrics["patients_sched"] += pts_sched; metrics["contact_mins"] += contact; metrics["chart_mins"] += chart; metrics["lunch_lost"] += lunch; metrics["overtime"] += over

overbook_saturation = (metrics["act_overbooks"] / metrics["poss_overbooks"]) if metrics["poss_overbooks"] > 0 else 0
global_chart_space = (metrics["chart_mins"] / metrics["patients_seen"]) if metrics["patients_seen"] > 0 else 0

# Calculated Static Baseline NPS
if overbook_saturation <= 0.20: baseline_nps = 75
elif overbook_saturation <= 0.50: baseline_nps = 45
else: baseline_nps = 12

# --- Financial Degradation Simulation Engine ---
def run_financial_simulation(initial_d, weekly_cap, current_nps, elasticity, rev_per_pt, no_show_pct):
    history = []
    current_demand = initial_d
    neutral_nps = 50.0
    cumulative_loss = 0.0
    attendance_rate = 1.0 - (no_show_pct / 100.0)
    
    for week in range(1, 13):
        utilization = current_demand / weekly_cap if weekly_cap > 0 else 1.0
        week_nps = current_nps - (max(0.0, utilization - 0.85) * 60.0)
        week_nps = max(-100.0, min(100.0, week_nps))
        
        actual_seen = min(current_demand, weekly_cap) * attendance_rate
        baseline_seen = min(initial_d, weekly_cap) * attendance_rate
        
        weekly_loss = max(0.0, baseline_seen - actual_seen) * rev_per_pt
        cumulative_loss += weekly_loss
        
        nps_signal = (week_nps - neutral_nps) / 100.0
        demand_change = current_demand * (elasticity * nps_signal)
        next_demand = max(10, current_demand + demand_change)
        
        history.append({
            "Week": f"Wk {week}",
            "Market Demand": round(current_demand, 1),
            "Cumulative Revenue Lost ($)": round(cumulative_loss, 0),
            "Predicted NPS": round(week_nps, 1)
        })
        current_demand = next_demand
        
    return pd.DataFrame(history)

sim_df = run_financial_simulation(init_demand, metrics["patients_sched"], baseline_nps, market_elasticity, rev_per_encounter, no_show_rate)

# --- DISPLAY SIMULATION & FINANCIAL METRICS ---
st.divider()
site_profile_label = "Retail-Integrated Clinic Profile" if has_optical else "Professional/Clinical-Only Profile"
st.subheader(f"12-Week Financial Overlay & Brand Spoilage Projections ({site_profile_label})")
st.markdown("""
This data charts the economic balancing loop. If the clinic run rate causes systemic satisfaction drops, the resulting local 
brand friction results in measurable, lost revenue over the fiscal quarter.
""")

f_col1, f_col2, f_col3 = st.columns(3)
start_d = sim_df.iloc[0]["Market Demand"]
end_d = sim_df.iloc[-1]["Market Demand"]
demand_delta = ((end_d - start_d) / start_d) * 100
total_cash_bled = sim_df.iloc[-1]["Cumulative Revenue Lost ($)"]

with f_col1:
    st.metric("Quarterly Demand Shift", f"{int(start_d)} → {int(end_d)} Weekly Requests", f"{demand_delta:.1f}% Change", delta_color="inverse" if demand_delta < 0 else "normal")
with f_col2:
    st.metric("Total Spoilage Cash Loss", f"${total_cash_bled:,.0f}", delta="Net Capital Leaked" if total_cash_bled > 0 else "Protected Revenue", delta_color="inverse" if total_cash_bled > 0 else "normal")
with f_col3:
    st.metric("Stabilized System NPS", f"{sim_df.iloc[-1]['Predicted NPS']:.0f}")

# Render Two Split Data Charts side-by-side for clear executive analysis
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Local Market Demand Curve (Requests/Week)**")
    st.line_chart(sim_df.set_index("Week")[["Market Demand"]], color="#FF4B4B")
with c2:
    st.markdown("**Cumulative Financial Leaking due to Patient Attrition ($)**")
    st.line_chart(sim_df.set_index("Week")[["Cumulative Revenue Lost ($)"]], color="#00CC96")

if total_cash_bled > 0:
    revenue_context = "retail pipeline bleed and downstream hardware attrition" if has_optical else "clinical volume drop and raw insurance reimbursement losses"
    st.error(f"🚨 **Financial Scarcity Warning:** Over-indexing on overbooks decreases gridlock delays today but costs this location **${total_cash_bled:,.0f}** in aggregate quarterly revenue due to {revenue_context}.")
else:
    st.success("✅ **Revenue Preservation Secured:** Patient satisfaction boundaries remain structurally sound. The practice preserves its referral pipelines and risks zero reputational revenue attrition.")

# --- MODULE: LATE ARRIVAL DECISION SUPPORT ---
st.divider()
st.subheader("Front-Desk Decision Support: Late Arrival Tolerances")

def calculate_late_tolerance(base_template, overbooks, mins_total, no_show_pct):
    st_c, ic_c, oc_c = analyze_session(base_template, overbooks)
    pts_sched = st_c + ic_c + (oc_c * 2)
    pts_seen = pts_sched * (1.0 - (no_show_pct / 100.0))
    contact = ((st_c + ic_c) * CLINICAL_ASSUMPTIONS["std_contact_min"]) + (oc_c * CLINICAL_ASSUMPTIONS["overbook_contact_min"])
    actual_contact = contact * (1.0 - (no_show_pct / 100.0))
    intact_buffers = ic_c
    slack = mins_total - (actual_contact + (pts_seen * CLINICAL_ASSUMPTIONS["req_chart_min_per_pt"]))
    permissible_mins = max(0.0, (grid_inc * 0.5) + (slack / max(1.0, pts_seen)) + (intact_buffers * 3.0))
    possible_buffers = len([x for x in base_template if x["Type"] == "🟠 Complex / Catch-up"])
    ob_sat = overbooks / possible_buffers if possible_buffers > 0 else 1.0
    if ob_sat >= 0.6: permissible_mins *= 0.4  
    elif ob_sat >= 0.3: permissible_mins *= 0.7
    return min(20, int(permissible_mins))

am_late_limit = calculate_late_tolerance(am_base_template, weekly_config["Monday"]["am_overbooks"], am_template_mins, no_show_rate)
pm_late_limit = calculate_late_tolerance(pm_base_template, weekly_config["Monday"]["pm_overbooks"], pm_template_mins, no_show_rate)

lat1, lat2 = st.columns(2)
with lat1:
    st.markdown("### Morning Session Allowance")
    if am_late_limit >= 12: st.success(f"**Permissible Grace Period: {am_late_limit} Minutes**")
    elif am_late_limit >= 7: st.warning(f"**Permissible Grace Period: {am_late_limit} Minutes**")
    else: st.error(f"**Permissible Grace Period: {am_late_limit} Minutes**")
with lat2:
    st.markdown("### Afternoon Session Allowance")
    if pm_late_limit >= 12: st.success(f"**Permissible Grace Period: {pm_late_limit} Minutes**")
    elif pm_late_limit >= 7: st.warning(f"**Permissible Grace Period: {pm_late_limit} Minutes**")
    else: st.error(f"**Permissible Grace Period: {pm_late_limit} Minutes**")
