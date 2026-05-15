# Civic-Complaint-Triage-Intelligence-Engine

Prioritizes consumer complaints filed in New York State by combining keyword rules with a zero-shot transformer classifier, orchestrated through a PySpark pipeline. Results are served as an interactive Streamlit dashboard.

### Tools Used: Python, PySpark, Hugging Face Transformers, PyTorch, Streamlit, Plotly

### Data Source: https://www.consumerfinance.gov/data-research/consumer-complaints/

### Link: https://civic-complaint-triage-intelligence-engine.streamlit.app/

## Technologies Used

- **PySpark** — CSV ingestion, filtering, SQL-based keyword rules, and serving transformer inference through a vectorized `pandas_udf`.
- **Hugging Face Transformers + PyTorch** — Zero-shot classification using `valhalla/distilbart-mnli-12-3`, a distilled BART-MNLI variant.
- **pandas** — Final aggregation and CSV export for the dashboard.
- **Streamlit + Plotly** — Web dashboard with a priority-distribution bar chart, a triage queue for Critical cases, and an interactive narrative tester.
- **gdown** — Downloads the multi-hundred-megabyte processed dataset from Google Drive at app startup (too large for GitHub's 100 MB file limit).
- **Google Colab (T4 GPU)** — Free GPU runtime for offline classification. CPU inference takes 1–2 hours; Colab GPU cuts it to ~15 minutes.

## Data Acquisition

```
EDA/analysis.py
    ↓ (cleans raw CFPB data, drops nulls, etc.)
cleaned_data_staging.csv   ← intermediate file (406 MB, gitignored)
    ↓ Pipeline/pipeline.py
    ↓ Spark filters to State == "NY" + non-null narrative
    ↓ Spark keyword rules flag obvious Critical / High cases
    ↓ pandas_udf invokes DistilBART-MNLI on the remaining rows
    ↓ Priority_Flag column written (Critical / High / Medium / Standard)
dashboard_data.csv         ← final file (242 MB, hosted on Google Drive)
    ↓ visualization/app.py downloads via gdown on first run
Streamlit Dashboard
```

## Methodology

The pipeline uses a **two-stage hybrid scoring strategy**:

1. **Stage 1 — Spark SQL keyword rules.** Cheap substring matches on the narrative flag the obvious cases:
   - Contains `"identity theft"` → `Critical`
   - Contains `"elderly"` → `High`

   These run inside a Spark `withColumn` / `when().otherwise()` chain and cost effectively nothing.

2. **Stage 2 — Zero-shot transformer.** Rows the rules didn't catch are routed through a vectorized `@pandas_udf` that invokes a Hugging Face `zero-shot-classification` pipeline. The four candidate labels and their priority mapping:

   | Candidate label | Priority |
   |---|---|
   | identity theft or fraud | Critical |
   | elder abuse or scam targeting elderly | High |
   | billing or fee dispute | Medium |
   | general complaint | Standard |

The model is loaded once per Spark executor process via a module-level singleton — the idiomatic pattern for serving Hugging Face models inside Spark UDFs.

## Data Exploration

The dataset has data from January 1, 2020 to December 31, 2025 (6 years). There is a total of 1,127,372 rows. 

The raw CFPB dataset covers all U.S. consumer financial complaints. For this prototype the working set is filtered to:

- `State == "NY"` — scoped to the NY State Office of the Attorney General
- Non-null `Consumer complaint narrative` — the field the classifier reads

After filtering, ~308,000 narratives feed into the scoring stage.

## Modeling

`valhalla/distilbart-mnli-12-3` was chosen as the zero-shot classifier — a distilled BART-MNLI variant ~3× faster than the full `facebook/bart-large-mnli` baseline at a modest accuracy cost. Zero-shot classification was preferred over supervised fine-tuning because:

- No labeled training data exists for this taxonomy.
- The four candidate labels are semantically distinct enough that NLI-based zero-shot performs well out of the box.
- The taxonomy can be re-targeted by editing one list — no retraining required.

## Results

On a 200-row local smoke test, the pipeline produced this distribution:

| Label | Count |
|---|---:|
| Standard | 133 |
| Critical | 43 |
| Medium | 20 |
| High | 4 |

Spot-checked samples per label: identity-theft complaints correctly Critical, billing/fee disputes correctly Medium, generic credit-report disputes correctly Standard. The full ~308k-row run is performed offline via Google Colab.

## Limitations

- **"Elderly" over-calling.** The model classifies any narrative involving an older relative (e.g., a parent's SSN being misused) as "elder abuse," even when the victim isn't elderly. Tightening the label string is one mitigation.
- **Offline inference.** Classification happens in Colab; the Streamlit app only reads the pre-scored CSV. Re-scoring on new data requires re-running the Colab notebook and replacing the Drive-hosted file.
- **Streamlit Cloud memory.** A 242 MB CSV expands to ~1.5 GB in pandas, near the Streamlit Cloud free-tier RAM limit. Future iterations could pre-aggregate or load only the columns the dashboard reads.
- **NY-only scope.** The state filter is hard-coded. Extending to other jurisdictions is a one-line change, but rules and labels may need re-tuning.

## Setup

### Local environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r Pipeline/requirements.txt
```

### Smoke test (200 rows, ~5 minutes on CPU)

```bash
python Pipeline/pipeline.py --sample 200
```

### Full classification run (Google Colab, T4 GPU, ~15 minutes)

1. Open a new Colab notebook → Runtime → Change runtime type → **T4 GPU**.
2. Clone the repo and install dependencies:
   ```python
   !git clone https://github.com/Sangeetha-007/Civic-Complaint-Triage-Intelligence-Engine.git
   %cd Civic-Complaint-Triage-Intelligence-Engine
   !pip install -r Pipeline/requirements.txt
   ```
3. Get `cleaned_data_staging.csv` into the Colab filesystem (e.g., from your Drive):
   ```python
   !pip install gdown
   !gdown --id <YOUR_FILE_ID> -O cleaned_data_staging.csv
   ```
4. Run the pipeline:
   ```python
   !python Pipeline/pipeline.py
   ```
5. Download `dashboard_data.csv` and replace the Drive-hosted version (right-click the existing Drive file → **Manage versions** → upload new) so the file ID — and the app — keeps working unchanged.

### Local Streamlit dashboard

```bash
pip install -r visualization/requirements.txt
streamlit run visualization/app.py
```

<!--
=====================================================================
Earlier draft notes, kept for reference.
=====================================================================

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



Refactor Pipeline/pipeline.py — drop Spark (no benefit on a single Colab node), keep pandas.
Read cleaned_data_staging.csv, filter to NY + non-null narrative, run zero-shot classification with valhalla/distilbart-mnli-12-3 and the four-label set, write dashboard_data.csv.
Add a --sample N flag so you can smoke-test on 1k rows locally before the full run.
Update visualization/requirements.txt — leave it lean (no torch/transformers in the deployed app; those only need to be installed in Colab).
Add Pipeline/requirements.txt — transformers, torch, pandas for the offline job. Keeps deploy deps and training/inference deps separate.
Colab usage — just two cells: !git clone <your-repo> && pip install -r Pipeline/requirements.txt and
!python Pipeline/pipeline.py --input cleaned_data_staging.csv --output dashboard_data.csv. You upload the staging CSV to Colab once.



SparkSession, spark.read.csv, df.filter(), col() — all stay
New: @pandas_udf wrapping the DistilBART-MNLI classifier, with the model loaded once per executor
(module-level singleton, the idiomatic pattern)
Optional: hybrid keyword-then-model — Spark when().otherwise() catches the obvious cases cheaply,
the UDF only runs on the leftover "uncertain" rows. That's both rule-based logic and ML in the same pipeline,
which reads great.
Final .toPandas().to_csv() for the dashboard, unchanged.



New Colab notebook → Runtime → Change runtime type → GPU (T4).
Cell 1: !git clone https://github.com/Sangeetha-007/Civic-Complaint-Triage-Intelligence-Engine.git && cd Civic-Complaint-Triage-Intelligence-Engine && pip install -r Pipeline/requirements.txt
Upload cleaned_data_staging.csv to the Colab file browser (or gdown it from your Drive).
Cell 2: !cd Civic-Complaint-Triage-Intelligence-Engine && python Pipeline/pipeline.py --input ../cleaned_data_staging.csv --output ../dashboard_data.csv
Download the resulting dashboard_data.csv and re-upload to Drive (or just replace your existing Drive file via "Manage versions" so the file ID stays the same and app.py needs no change).
-->
