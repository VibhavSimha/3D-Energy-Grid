import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ml_logic import EnergyOptimizer, GENERATION_DATA

st.set_page_config(
    page_title="Energy Load Prediction & Distribution",
    page_icon="⚡",
    layout="wide"
)

selected_features = [
    "hour", "price day ahead", "day_of_week", "day", "month", "year",
    "temp_Barcelona", "pressure_Seville", "temp_max_Barcelona", "price actual",
    "temp_min_Seville", "temp_min_Barcelona", "temp_min_Valencia",
    "humidity_Barcelona", "pressure_Bilbao", "pressure_Barcelona",
    "temp_max_Seville", "temp_Madrid", "temp_max_Madrid", "temp_max_Bilbao",
]

# Initialize Optimizer
optimizer = EnergyOptimizer()

def calculate_stats(distribution: dict, optimization_type: str = "cost"):
    total_cost = 0
    total_impact = 0
    sources_list = []
    
    for source, load in distribution.items():
        if load > 0:
            data = GENERATION_DATA[source]
            # Cost calculation (simplified from original logic)
            cost = data["cost_value"] * (load / data["capacity"])
            impact = data["impact_value"] * (load / data["capacity"])
            
            total_cost += cost
            total_impact += impact
            sources_list.append((source, load))
            
    return total_cost, total_impact, sources_list

def main():
    st.title("⚡ Energy Load Prediction & Distribution Optimizer")
    st.image(r"img1.jpg",  use_container_width=True)
    
    st.sidebar.header("Input Features")
    
    input_data = {}
    
    st.sidebar.subheader("Temporal Features")
    input_data["hour"] = st.sidebar.slider("Hour", 0, 23, 12)
    input_data["day"] = st.sidebar.slider("Day", 1, 31, 15)
    input_data["month"] = st.sidebar.slider("Month", 1, 12, 6)
    input_data["year"] = st.sidebar.number_input("Year", 2000, 2030, 2015)
    input_data["day_of_week"] = st.sidebar.slider("Day of Week", 0, 6, 3)

    st.sidebar.subheader("Price Features")
    input_data["price day ahead"] = st.sidebar.number_input("Price Day Ahead", 0.0, 1000.0, 50.0)
    input_data["price actual"] = st.sidebar.number_input("Price Actual", 0.0, 1000.0, 50.0)

    # Simplified city inputs for the model (keeping original inputs as model expects them)
    cities = ["Barcelona", "Madrid", "Seville", "Valencia", "Bilbao"]
    for feature in selected_features:
        if any(city in feature for city in cities):
            if "temp" in feature:
                input_data[feature] = st.sidebar.slider(f"{feature.replace('_', ' ').title()}", -10.0, 45.0, 20.0)
            elif "pressure" in feature:
                input_data[feature] = st.sidebar.slider(f"{feature.replace('_', ' ').title()}", 900.0, 1100.0, 1013.0)
            elif "humidity" in feature:
                input_data[feature] = st.sidebar.slider(f"{feature.replace('_', ' ').title()}", 0.0, 100.0, 50.0)

    input_df = pd.DataFrame([input_data])
    input_df = input_df[selected_features]

    if st.button("Predict and Optimize", type="primary"):
        if optimizer.model is not None:
            try:
                # 1. Predict Load
                prediction = optimizer.model.predict(input_df)[0]
                
                # Scale prediction to Karnataka size if needed? 
                # Original model predicts ~20,000 MW? Karnataka plants sum to ~3500 MW.
                # Let's scale it down to fit our capacity for a realistic demo.
                total_capacity = sum(d['capacity'] for d in GENERATION_DATA.values())
                # Assuming original max load was around 30000, and we have ~8000 (including fossil backup)
                # Let's just clamp it or scale it.
                # For now, let's use a scaling factor of 0.2
                scaled_prediction = prediction * 0.2
                
                # 2. Optimize
                hour = input_data["hour"]
                cost_distribution = optimizer.optimize_distribution(scaled_prediction, hour, "cost")
                impact_distribution = optimizer.optimize_distribution(scaled_prediction, hour, "impact")

                # 3. Calculate Stats
                cost_total, cost_impact, cost_sources = calculate_stats(cost_distribution, "cost")
                impact_total, impact_impact, impact_sources = calculate_stats(impact_distribution, "impact")

                # 4. Display Results
                st.subheader("Load Prediction")
                col_pred1, col_pred2 = st.columns(2)
                col_pred1.metric("Original Predicted Load", f"{prediction:,.2f} MWh")
                col_pred2.metric("Scaled Target Load (Karnataka)", f"{scaled_prediction:,.2f} MWh")
                
                st.markdown("---")
                
                st.subheader("Energy Distribution Strategies")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Cost Optimized")
                    st.write(f"Avg Impact Score: {cost_impact:.2f}")
                    if cost_sources:
                        fig1, ax1 = plt.subplots(figsize=(8, 8))
                        sizes = [load for _, load in cost_sources]
                        labels = [source.title() for source, _ in cost_sources]
                        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                        ax1.axis('equal')
                        st.pyplot(fig1)
                    else:
                        st.write("No generation needed.")
                
                with col2:
                    st.subheader("Eco-Friendly")
                    st.write(f"Avg Impact Score: {impact_impact:.2f}")
                    if impact_sources:
                        fig2, ax2 = plt.subplots(figsize=(8, 8))
                        sizes = [load for _, load in impact_sources]
                        labels = [source.title() for source, _ in impact_sources]
                        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                        ax2.axis('equal')
                        st.pyplot(fig2)
                    else:
                        st.write("No generation needed.")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.error("Model not loaded. Please check the files.")
        
        st.image(r"img5.jpg",  use_container_width=True)

if __name__ == "__main__":
    main()