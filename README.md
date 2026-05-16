# 🏥 Hospital Optometry Template Optimizer & Enterprise Risk Dashboard

An advanced clinical operations and health system strategy tool. This interactive application maps outpatient template design parameters directly to national productivity benchmarks (**SullivanCotter**), patient loyalty forecasting (**Press Ganey LTR & Net Promoter Score**), and clinical compliance/burnout risk indices.

## 🚀 Strategic Overview
In high-volume hospital-based medical groups, scheduling templates are often designed in isolation, focusing exclusively on raw volume targets. This dashboard bridges the gap between clinical operations, finance, and quality by showing the downstream ecosystem effects of template modifications in real time.

It evaluates every scheduling matrix across the three pillars of healthcare leadership:
1. **Financial Throughput & Access:** Benchmarked against objective national productivity data.
2. **Consumer Loyalty:** Modeling patient satisfaction decay relative to compounding operational delays.
3. **Workforce & Compliance Protection:** Inferring documentation capacity and staff overtime liabilities.

---

## 📊 Core Logics & Mathematical Frameworks

### 1. Productivity Benchmarking (SullivanCotter)
The application categorizes daily patient throughput using the annualized national survey data compiled for **Hospital-Based General Optometry** (divorced from global surgical ophthalmology co-management windows). Assuming a standard 220-day clinical year, the application maps volume as follows:
*   **Below Median:** < 11.4 encounters/day
*   **Median Tier (50th Percentile):** 11.4 to 13.5 encounters/day — *The baseline target for stable institutional access.*
*   **High Productivity (75th Percentile):** 13.6 to 15.8 encounters/day
*   **Elite Tier (90th Percentile):** ≥ 15.9 encounters/day

### 2. Patient Loyalty & Experience Decay Curves
Patient satisfaction is highly sensitive to unmitigated waiting room and exam room delays. The dashboard utilizes an operational decay formula to calculate Press Ganey **Likelihood to Recommend (LTR)** Top-Box percentages and inferred **Net Promoter Scores (NPS)**.

*   **The 15-Minute Threshold:** Up to 15 minutes of cumulative wait time is absorbed as an industry baseline, carrying a 0% penalty.
*   **Linear Decay Zone (16–30 Mins):** Delays begin a linear drag on consumer metrics. Press Ganey LTR decays at **-0.8% per minute**; NPS decays at **-1.5 points per minute**.
*   **Exponential Breaking Point (>30 Mins):** Bottlenecks compounding beyond 30 minutes trigger structural dissatisfaction. Patients become highly sensitive to perceived rushing, driving up "Detractor" classifications on the NPS scale. Press Ganey LTR drops by a flat 12% baseline before decaying at **-1.4% per minute**, while NPS drops by a flat 22.5 baseline before decaying at **-3.2 points per minute**.

### 3. Clinical Quality & Risk Inferences
*   **Documentation Buffering:** Safely capturing comprehensive EHR documentation, complex coding validation, and e-prescribing requires an estimated **6 to 8 minutes** of recovery time per encounter. The app calculates:
    $$\text{Buffer Time per Patient} = \frac{\text{Total Dedicated Buffer Minutes}}{\text{Daily Patient Encounters}}$$
    Ratios falling below 4.0 minutes per patient flag an elevated risk of chart backlogs, billing latency, and late-night documentation drift.
*   **Staff Overtime Drift:** Compounding wait times mathematically prevent the clinic session from closing at the posted time. The app projects hourly support staff overtime liabilities based on systemic bottleneck run times past the official session block.

---

## 📚 Data Sources & Academic Citations

*   **Ambulatory Wait-Time Mechanics:** 
    *   *Bleustein C, Bost DB, et al.* "Wait Times, Patient Satisfaction Scores, and the Perception of Care." *American Journal of Managed Care (AJMC)*. This seminal study correlates multi-increment wait time brackets with sharp drops in patient trust, staff courtesy ratings, and overall likelihood to refer.
    *   *Rane, et al.* "Effect of total wait time on Press Ganey Outpatient Medical Practice Survey." *Journal of Hand Surgery*. Demonstrates via hierarchical regression that each minute of clinical delay drops the objective odds of achieving a top-box score by 5% ($\text{OR } 0.95$).
*   **Institutional Productivity Data:**
    *   *SullivanCotter Physician and APP Compensation and Productivity Surveys*. Industry-standard national datasets mapping annualized ambulatory medical group encounters specifically for hospital-employed specialized providers.
*   **Healthcare Brand Loyalty:**
    *   *CustomerGauge & TeleVox Healthcare Experience Benchmark Reports*. Establishes the volatile relationship between outpatient wait thresholds and Net Promoter Score classification boundaries ($\% \text{ Promoters} - \% \text{ Detractors}$).

---

## ⚙️ Deployment & Setup
The accompanying application is built using Python 3 and Streamlit.

### File Architecture
*   `app.py`: The core application code executing the scheduling loops, analytics logic, and UI blocks.
*   `requirements.txt`: Defines the explicit framework dependencies required by the web server environment.

### Local Installation
1. Clone this repository to your local machine.
2. Install the lightweight dependencies:
   ```bash
   pip install -r requirements.txt
