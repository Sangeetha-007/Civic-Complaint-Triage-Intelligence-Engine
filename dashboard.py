import streamlit as st
import pandas as pd
import plotly.express as px

gatherUsageStats = False
# 1. Page Setup
st.set_page_config(page_title="OAG Complaint Triage", layout="wide")
st.title("⚖️ Civic Complaint Triage & Intelligence Engine")
#st.markdown("Prototype for NYS Office of the Attorney General (OAG)")

# 2. Load Data (We use a cache so it doesn't reload every time you click)
@st.cache_data
def load_data():
    # In a real app, you would load the CSV. 
    # For this demo, let's create a sample so it runs immediately for you.
    data = {
        'Narrative': [
            "My elderly mother was tricked into sending money.", 
            "I saw a charge I didn't make.", 
            "This company is a scam and theft.", 
            "Late fee was charged incorrectly.", 
            "Identity theft regarding my credit card."
        ],
        'State': ['NY', 'NY', 'NY', 'CA', 'NY']
    }
    return pd.DataFrame(data)

df = load_data()

# 3. The Logic (Your Keyword Matching)
def simple_risk_scorer(text):
    text = text.lower()
    if "identity theft" in text:
        return "Critical"
    elif "elderly" in text:
        return "High"
    elif "scam" in text or "theft" in text:
        return "Medium"
    else:
        return "Standard"

# Apply the logic
df['Risk_Level'] = df['Narrative'].apply(simple_risk_scorer)

# 4. The Dashboard Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔍 Priority Distribution")
    # Your Plotly Chart
    fig = px.bar(
        df['Risk_Level'].value_counts().reset_index(),
        x='Risk_Level', 
        y='count', 
        color='Risk_Level',
        color_discrete_map={"Critical": "red", "High": "orange", "Medium": "yellow", "Standard": "green"}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 Triage Queue")
    # Show the "Critical" cases first
    st.dataframe(df[df['Risk_Level'] == 'Critical'][['Risk_Level', 'Narrative']], hide_index=True)

# 5. Interactive Tester
st.divider()
st.subheader("Test the Algorithm")
user_input = st.text_input("Paste a complaint narrative here:")
if user_input:
    score = simple_risk_scorer(user_input)
    st.success(f"Predicted Priority: **{score}**")