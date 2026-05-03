from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lower

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

if __name__ == "__main__":
    spark = create_spark_session()
    
    # Point to the file created by analysis.py
    STAGING_FILE = "cleaned_data_staging.csv"
    
    # Load the data that you already cleaned
    df = extract_clean_data(spark, STAGING_FILE)
    
    print(f"Pipeline loaded {df.count()} records from analysis.py")
    
    # Now you can go straight to the "Risk Scoring" or NLP steps!
    #Distributed Data Cleaning (Equivalent to our Pandas step)
    # Let's filter for NY and ensure there is a narrative
    df_filtered = df.filter(
    (col("State") == "NY") & 
    (col("Consumer complaint narrative").isNotNull())
    )

    #print(df_filtered.head())

    # 4. Simple "Risk Flag" Logic using Spark SQL functions
    # This shows you can translate 'complex data findings' into code
    df_prioritized = df_filtered.withColumn(
    "Priority_Flag",
    when(col("Consumer complaint narrative").contains("elderly"), "High")
    .when(col("Consumer complaint narrative").contains("identity theft"), "Critical")
    .otherwise("Standard")
    )

    df_prioritized.select("Product", "Priority_Flag").show(5)

    save_for_dashboard(df_prioritized)

    








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
