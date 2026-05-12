# Civic-Complaint-Triage-Intelligence-Engine

### Tools Used: Python, PySpark

### Data Source: https://www.consumerfinance.gov/data-research/consumer-complaints/

### Link: https://civic-complaint-triage-intelligence-engine.streamlit.app/

## Technologies Used

## Data Acquisition
EDA/analysis.py
    ↓ (cleans raw data, drops nulls, etc.)
cleaned_data_staging.csv   ← intermediate file (406 MB)
    ↓ pipeline.py reads this
    ↓ filters to State == "NY" + non-null narrative
    ↓ adds Priority_Flag column (Critical / High / Standard)
    ↓
dashboard_data.csv         ← final file for Streamlit (242 MB)
    ↓
visualization/app.py
## Methodology

## Data Exploration

## Modeling

## Results

## Limitations
