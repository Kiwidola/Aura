import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Air Quality Monitor", layout="wide")

# 2. LOAD YOUR MODEL
@st.cache_resource
def load_model():
    # Ensure this string matches your actual filename exactly
    model_filename = 'your_model.pkl' 
    if not os.path.exists(model_filename):
        st.error(f"Error: The file '{model_filename}' was not found. Please upload it to your repository.")
        st.stop()
    return joblib.load(model_filename)

model = load_model()

# 3. DATA ACQUISITION
@st.cache_data(ttl=300)
def get_latest_data():
    # Replace these values with your actual data fetching logic (e.g., from Google Sheets)
    return {
        'tvoc': 38, 'eco2': 433, 'temp': 28.9, 'hum': 49.2, 
        'mq135': 1040, 'mq7': 1223, 'pm25': 0, 'pm10': 0
    }

data = get_latest_data()

# 4. PREDICTION LOGIC
def predict_quality(d):
    # PREPARE FEATURES: Must be in the EXACT order used during training (8 features)
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
    
    input_data = np.array(features).reshape(1, -1)
    prediction = model.predict(input_data)
    return prediction[0]

# 5. UI DISPLAY
st.title("Air Quality Intelligence Dashboard")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Latest Sensor Readings")
    st.write(pd.DataFrame([data]))
    
    if st.button("Analyze Air Quality"):
        try:
            result = predict_quality(data)
            st.success(f"Model Prediction: {result}")
        except Exception as e:
            st.error(f"Prediction error: {e}")

with col2:
    st.subheader("System Status")
    st.write("Monitoring active. Ensure your model file is correctly named and uploaded.")
