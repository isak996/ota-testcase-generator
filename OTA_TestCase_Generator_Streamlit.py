import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="OTA Test Case Generator", layout="wide")
st.title("🚗 OTA Test Case Generator")

st.sidebar.header("Configuration")
random_seed = st.sidebar.number_input("Random Seed", value=42)
per_template_samples = st.sidebar.slider("Samples per Template", 1, 20, 3)
max_cases_per_intent = st.sidebar.slider("Max Cases per Intent", 10, 500, 50)
add_noise = st.sidebar.checkbox("Add Noise Variations", value=True)
random.seed(random_seed)

st.markdown("### Upload or Edit Intent Inventory")
uploaded_file = st.file_uploader("Upload Excel with intents/templates (optional)", type=["xlsx"])

if uploaded_file:
    df_intents = pd.read_excel(uploaded_file, sheet_name="intents")
else:
    df_intents = pd.DataFrame({
        "intent": ["play_music", "navigate", "weather"],
        "templates": [
            "play some music;play a song;I want to listen to music",
            "take me to the bank;navigate to the hospital;go to the airport",
            "what's the weather;how is the weather today;weather forecast"
        ]
    })

st.dataframe(df_intents)

def generate_cases(df):
    rows = []
    for _, row in df.iterrows():
        intent = row["intent"]
        templates = str(row["templates"]).split(";")
        for t in templates:
            for i in range(per_template_samples):
                q = t.strip()
                if add_noise and random.random() < 0.3:
                    q = q + " please"
                rows.append({
                    "Query": q,
                    "ExpectedIntent": intent,
                    "TestType": "base" if i == 0 else "variation",
                    "Difficulty": "easy" if i < 2 else "medium"
                })
    df_out = pd.DataFrame(rows)
    return df_out.head(max_cases_per_intent * len(df))

if st.button("Generate Test Cases"):
    generated = generate_cases(df_intents)
    st.success(f"Generated {len(generated)} cases.")
    st.dataframe(generated.head(20))
    st.download_button("Download CSV",
                       generated.to_csv(index=False).encode("utf-8"),
                       "test_cases.csv", "text/csv")
    generated.to_excel("test_cases.xlsx", index=False)
    with open("test_cases.xlsx", "rb") as f:
        st.download_button("Download Excel", f,
                           "test_cases.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
