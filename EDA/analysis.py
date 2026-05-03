import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import datetime
from wordcloud import WordCloud
from textblob import TextBlob


df=pd.read_csv("/Users/sangeetha/Downloads/complaints-2026-01-19_23_57.csv")
print(df.head())

print(df.info())

print("Check Null Columns:")
print(df.isnull().sum())


# 1. Create a proper DataFrame for plotting
# reset_index() converts the Series into a DataFrame with columns 'State' and 'count'
state_count = df['State'].value_counts().reset_index()

# 2. Rename columns to be safe (Pandas 2.0+ uses 'count', older uses 'State')
state_count.columns = ['State', 'Count']

# 3. Pass the SUMMARY table (state_count), not the raw table (df)
fig = px.bar(
    state_count,           # <--- Use the summary table here
    x='State',             # Use the string name of the column
    y='Count',             # Use the string name of the column
    title="State Distribution",
    text='Count',          # Show the numbers on the bars
    
    # To fix the color issue:
    # If you want them all red:
    color_discrete_sequence=['blue']
    
    # OR if you want them colored by intensity (Thermal):
    # color='Count',
    # color_continuous_scale=px.colors.sequential.Thermal
)

fig.update_layout(width=600, height=400)
fig.show()

####---------------------------------------- DATA ENGINEERING-----------------------###
print(isinstance(df['Date received'], datetime.date))
print(df['Date received'].dtype)
format_string = "%m/%d/%y"

# df = datetime.datetime.strptime(df['Date received'], format_string).date()
# print(df.info())

df['Date received'] = pd.to_datetime(df['Date received'], format=format_string)

#print(isinstance(df['Date received'], datetime.date))
print(df['Date received'].dtype)


na_count_per_column = df.isna().sum()
print("NA count")
print(na_count_per_column)

#df_cleaned = df['Consumer complaint narrative'].dropna()
df.dropna(subset=['Consumer complaint narrative'], inplace=True)
print(df)

print("Cleaned NA count")
print(df.isna().sum())

print(df)
print(df.info())


# Convert all elements in the Series to strings, then join them
text = ' '.join(str(item) for item in df['Consumer complaint narrative'])
wordcloud = WordCloud(width=800, height=400, background_color='black').generate(text)

# # Display the word cloud
plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
#Bilinear interpolation is a method of smoothing an image when it is displayed at a resolution different from its original size.
plt.axis('off')  # Turn off axis
plt.show()

# Define the hand-off file name
CLEAN_DATA_PATH = "cleaned_data_staging.csv"

# Save the dataframe without the index numbers
# This creates the file that pipeline.py will look for
df.to_csv(CLEAN_DATA_PATH, index=False)

print(f"Success: Cleaned data handed off to {CLEAN_DATA_PATH}")