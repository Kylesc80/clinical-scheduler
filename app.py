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
init_demand
