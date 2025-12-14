# Data Center DR Analysis Project

This repository contains the full analysis pipeline for Data Center Demand Response (DR) potential, economic feasibility, and long-term investment strategy.

## Directory Structure

### `src/` (Source Code)
*   **01_Preprocessing**: Scripts for cleaning weather, SMP, and power source data.
*   **02_Load_Analysis**: Load decomposition (IT/Cooling) and basic statistical analysis.
*   **03_DR_Modelling**: DR simulation, events generation (1-hour standardized), and rated load estimation.
*   **04_Economic_Analysis**: Revenue calculation (Capacity + Energy), monthly detail analysis.
*   **05_Reliability**: RRMSE, Shortfall probability analysis.
*   **06_LongTerm_Strategy**: 30-year DCF, Sensitivity Analysis (Tornado), 50MW Scale-up.

### `data/` (Data Files)
*   **01_Raw**: Original raw data files (Weather, EPSIS, SMP).
*   **02_Intermediate**: Preprocessed and decomposed data sets.
*   **03_Final**: Final results including Revenue Tables, DR Events, DCF Projections, and Sensitivity Results.

### `figures/` (Visualization)
*   **01_Load_Profile**: Seasonal profiles, load decomposition plots.
*   **02_DR_Potential**: DR simulation results, potential distributions.
*   **03_Economics**: Revenue sensitivity, monthly capacity payments.
*   **04_Reliability_DCF**: Cash flow waterfalls, Tornado charts, RRMSE distributions.

## Key Scripts Execution Order

1.  **Preprocessing**: `src/01_Preprocessing/generate_annual_load.py`
2.  **DR Simulation**: `src/03_DR_Modelling/process_dr_events_1h.py`
3.  **Revenue Analysis**: `src/04_Economic_Analysis/analyze_revenue_final.py`
4.  **Reliability**: `src/05_Reliability/analyze_rrmse.py`
5.  **Long-Term DCF**: `src/06_LongTerm_Strategy/analyze_dcf_sensitivity.py`

## Final Output
The most critical results are found in `data/03_Final/` and `figures/04_Reliability_DCF/`.
