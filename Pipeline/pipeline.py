import argparse

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, pandas_udf, when
from pyspark.sql.types import StringType

ZS_MODEL = "valhalla/distilbart-mnli-12-3"
CANDIDATE_LABELS = [
    "identity theft or fraud",
    "elder abuse or scam targeting elderly",
    "billing or fee dispute",
    "general complaint",
]
LABEL_TO_PRIORITY = {
    "identity theft or fraud": "Critical",
    "elder abuse or scam targeting elderly": "High",
    "billing or fee dispute": "Medium",
    "general complaint": "Standard",
}

# Loaded once per executor process, not once per row.
_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None:
        import torch
        from transformers import pipeline as hf_pipeline

        device = 0 if torch.cuda.is_available() else -1
        _classifier = hf_pipeline(
            "zero-shot-classification",
            model=ZS_MODEL,
            device=device,
        )
    return _classifier


@pandas_udf(StringType())
def classify_narratives_udf(narratives: pd.Series) -> pd.Series:
    classifier = get_classifier()
    texts = narratives.fillna("").tolist()
    results = classifier(texts, candidate_labels=CANDIDATE_LABELS, batch_size=16)
    if isinstance(results, dict):
        results = [results]
    return pd.Series([LABEL_TO_PRIORITY[r["labels"][0]] for r in results])


def create_spark_session():
    return SparkSession.builder.appName("CivicComplaintEngine").getOrCreate()

# --- CHANGED: Now we read the CLEAN file, not the raw one ---
def extract_clean_data(spark, file_path):
    return spark.read.csv(
        file_path,
        header=True,
        inferSchema=True,
        # We handle multi-line text just in case narratives have newlines
        multiLine=True,
        escape='"'
    )

def save_for_dashboard(df_spark, output_filename="dashboard_data.csv"):
    """
    Takes the final Spark DataFrame, converts it to a single CSV,
    and saves it for the Streamlit app to read.
    """
    print("Converting to Pandas for dashboard export...")

    # 1. Convert to Pandas (This brings the data to the driver)
    # WARNING: Only do this AFTER filtering/aggregating down to a reasonable size (<1GB)
    df_pandas = df_spark.toPandas()

    # 2. Save as a standard CSV
    df_pandas.to_csv(output_filename, index=False)
    print(f"Success! Dashboard data saved to: {output_filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="cleaned_data_staging.csv")
    parser.add_argument("--output", default="dashboard_data.csv")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="If set, classify only N rows (for local smoke tests).",
    )
    args = parser.parse_args()

    spark = create_spark_session()
    df = extract_clean_data(spark, args.input)
    print(f"Pipeline loaded {df.count()} records from {args.input}")

    df_filtered = df.filter(
        (col("State") == "NY") & (col("Consumer complaint narrative").isNotNull())
    )

    if args.sample:
        df_filtered = df_filtered.limit(args.sample)
        print(f"Sampling to {args.sample} rows for smoke test.")

    # Stage 1: cheap keyword pre-flagging via Spark SQL — catches the obvious cases.
    narrative = col("Consumer complaint narrative")
    df_staged = df_filtered.withColumn(
        "Rule_Flag",
        when(narrative.contains("identity theft"), "Critical")
        .when(narrative.contains("elderly"), "High")
        .otherwise(None),
    )

    # Stage 2: only invoke the transformer on rows the rules didn't catch.
    df_certain = (
        df_staged.filter(col("Rule_Flag").isNotNull())
        .withColumn("Priority_Flag", col("Rule_Flag"))
        .drop("Rule_Flag")
    )
    df_uncertain = (
        df_staged.filter(col("Rule_Flag").isNull())
        .withColumn("Priority_Flag", classify_narratives_udf(narrative))
        .drop("Rule_Flag")
    )
    df_prioritized = df_certain.unionByName(df_uncertain)

    df_prioritized.select("Product", "Priority_Flag").show(5)

    save_for_dashboard(df_prioritized, args.output)


if __name__ == "__main__":
    main()


# =====================================================================
# Previous keyword-only entrypoint, kept for reference.
# =====================================================================
# if __name__ == "__main__":
#     spark = create_spark_session()
#
#     # Point to the file created by analysis.py
#     STAGING_FILE = "cleaned_data_staging.csv"
#
#     # Load the data that you already cleaned
#     df = extract_clean_data(spark, STAGING_FILE)
#
#     print(f"Pipeline loaded {df.count()} records from analysis.py")
#
#     # Now you can go straight to the "Risk Scoring" or NLP steps!
#     #Distributed Data Cleaning (Equivalent to our Pandas step)
#     # Let's filter for NY and ensure there is a narrative
#     df_filtered = df.filter(
#     (col("State") == "NY") &
#     (col("Consumer complaint narrative").isNotNull())
#     )
#
#     #print(df_filtered.head())
#
#     # 4. Simple "Risk Flag" Logic using Spark SQL functions
#     # This shows you can translate 'complex data findings' into code
#     df_prioritized = df_filtered.withColumn(
#     "Priority_Flag",
#     when(col("Consumer complaint narrative").contains("elderly"), "High")
#     .when(col("Consumer complaint narrative").contains("identity theft"), "Critical")
#     .otherwise("Standard")
#     )
#
#     df_prioritized.select("Product", "Priority_Flag").show(5)
#
#     save_for_dashboard(df_prioritized)



#######################################################################
# 1. Initialize the Engine
# spark = SparkSession.builder \
#     .appName("CivicComplaintEngine") \
#     .getOrCreate()

# 2. Load the Data (Spark is lazy, so this is nearly instant)
# df_spark = spark.read.csv("/Users/sangeetha/Documents/GitHub/Civic Complaint/cleaned_data_staging.csv", header=True, inferSchema=True)

# 3. Distributed Data Cleaning (Equivalent to our Pandas step)
# Let's filter for NY and ensure there is a narrative
# df_filtered = df_spark.filter(
#     (col("State") == "NY") &
#     (col("Consumer complaint narrative").isNotNull())
# )

# #print(df_filtered.head())

# # 4. Simple "Risk Flag" Logic using Spark SQL functions
# # This shows you can translate 'complex data findings' into code
# df_prioritized = df_filtered.withColumn(
#     "Priority_Flag",
#     when(col("Consumer complaint narrative").contains("elderly"), "High")
#     .when(col("Consumer complaint narrative").contains("identity theft"), "Critical")
#     .otherwise("Standard")
# )

# df_prioritized.select("Product", "Priority_Flag").show(5)
