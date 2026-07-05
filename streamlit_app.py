import streamlit as st
import pandas as pd
import numpy as np
import joblib

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Air Quality Monitor", layout="wide")

# 2. LOAD YOUR MODEL
# Ensure your model file is in the same directory as this script
@st.cache_resource
def load_model():
    return joblib.load('your_model.pkl') # Replace with your actual model filename

model = load_model()

# 3. DATA ACQUISITION
# Fetching the latest data (Replace with your actual Google Sheet API call or CSV source)
@st.cache_data(ttl=300)
def get_latest_data():
    # Placeholder: Replace with your actual logic to fetch the latest row from Google Sheets
    # Example: df = pd.read_csv("https://docs.google.com/spreadsheets/d/...")
    # For now, we simulate the structure:
    return {
        'tvoc': 38, 'eco2': 433, 'temp': 28.9, 'hum': 49.2, 
        'mq135': 1040, 'mq7': 1223, 'pm25': 0, 'pm10': 0
    }

data = get_latest_data()

# 4. PREDICTION LOGIC
def predict_quality(d):
    # PREPARE FEATURES: Must be in the EXACT order used during training (8 features)
    # Order: TVOC, eCO2, Temp, Hum, MQ135, MQ7, PM2.5, PM10
    features = [
        float(d['tvoc']), 
        float(d['eco2']), 
        float(d['temp']), 
        float(d['hum']), 
        float(d['mq135']), 
        float(d['mq7']), 
        float(d['pm25']), 
        float(d['pm10'])
    ]
    
    # Reshape for the model
    input_data = np.array(features).reshape(1, -1)
    
    # Perform prediction
    prediction = model.predict(input_data)
    return prediction[0]

# 5. UI DISPLAY
st.title("Air Quality Intelligence Dashboard")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Latest Sensor Readings")
    st.write(pd.DataFrame([data]))
    
    if st.button("Analyze Air Quality"):
        result = predict_quality(data)
        st.success(f"Model Prediction: {result}")

with col2:
    st.subheader("System Status")
    st.write("Monitoring active. Data refreshing every 5 minutes.")
    # Add charts or other visual elements here
