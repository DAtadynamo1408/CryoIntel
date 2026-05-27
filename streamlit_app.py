import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ml_model import PhysicsInformedModel

st.set_page_config(page_title="Refrigeration AI Predictor", layout="wide", page_icon="❄️")

# CSS to make the UI look premium and match modern design
st.markdown("""
<style>
    .reportview-container {
        background: #0b0f19;
    }
    .stApp {
        background: #0b0f19;
        color: #f1f5f9;
    }
    .css-1d391kg, .css-1lcbmhc {
        background: rgba(20, 26, 40, 0.6) !important;
    }
    h1, h2, h3 {
        color: #f1f5f9;
        font-family: 'Outfit', sans-serif;
    }
    .stSlider > div > div > div > div {
        background: #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_model():
    pm = PhysicsInformedModel()
    pm.load_model()
    return pm

st.title("❄️ Advanced Hybrid Physics-AI Refrigeration Model")
st.markdown("Predict transient refrigeration performance continuously over a 0–60 minute window.")

with st.spinner("Initializing physics-informed XGBoost model..."):
    model = load_model()

# Sidebar inputs
st.sidebar.header("⚙️ System Parameters")

duration = st.sidebar.slider("Prediction Window (minutes)", min_value=10, max_value=60, value=60, step=1)
mass = st.sidebar.number_input("Refrigerant Mass (kg)", min_value=1.0, max_value=5.0, value=1.5, step=0.1)

st.sidebar.subheader("Gas Composition")
blend_options = [
    "R407", 
    "R32/R125/R152a (20/10/70)", 
    "R32/R125/R152a (70/10/20)", 
    "R32/R125/R152a (15/15/70)", 
    "R32/R125/R152a (30/10/60)"
]
blend = st.sidebar.selectbox("Select Blend", blend_options)

st.sidebar.markdown("---")
if st.sidebar.button("Run Prediction", type="primary"):
    with st.spinner("Calculating physical constraints and executing ML prediction..."):
        results = model.predict_trajectory(mass, blend, duration=duration)
        df_res = pd.DataFrame(results)
        
        # Layout metrics
        col1, col2, col3, col4 = st.columns(4)
        final_row = df_res.iloc[-1]
        col1.metric("Final COP", f"{final_row['COP']:.3f}")
        col2.metric("Final W_comp (kW)", f"{final_row['Wcomp']:.3f}")
        col3.metric("Final Exergy Eff.", f"{final_row['Exergy']:.3f}")
        col4.metric("Evap Temp (°C)", f"{final_row['TL']:.2f}")

        # Charts
        st.subheader("📈 Performance Trajectories (Per-Minute)")
        
        fig_cop = px.line(df_res, x='Time', y='COP', title='Coefficient of Performance (COP) vs Time', 
                          template="plotly_dark", line_shape='spline')
        fig_cop.update_traces(line=dict(color="#10b981", width=3))
        
        fig_work = px.line(df_res, x='Time', y='Wcomp', title='Compressor Work vs Time (kW)', 
                           template="plotly_dark", line_shape='spline')
        fig_work.update_traces(line=dict(color="#3b82f6", width=3))

        fig_exergy = px.line(df_res, x='Time', y='Exergy', title='Exergy Efficiency vs Time', 
                             template="plotly_dark", line_shape='spline')
        fig_exergy.update_traces(line=dict(color="#8b5cf6", width=3))
        
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df_res['Time'], y=df_res['TL'], mode='lines', name='Evaporator (TL)', line=dict(color='#3b82f6', width=2, shape='spline')))
        fig_temp.add_trace(go.Scatter(x=df_res['Time'], y=df_res['TH'], mode='lines', name='Condenser (TH)', line=dict(color='#ef4444', width=2, shape='spline')))
        fig_temp.update_layout(title="Temperatures vs Time (°C)", template="plotly_dark")

        # Render charts in a grid
        c1, c2 = st.columns(2)
        c1.plotly_chart(fig_cop, use_container_width=True)
        c2.plotly_chart(fig_work, use_container_width=True)
        
        c3, c4 = st.columns(2)
        c3.plotly_chart(fig_exergy, use_container_width=True)
        c4.plotly_chart(fig_temp, use_container_width=True)
        
        # Display Data Table
        with st.expander("View Raw Data (0-60 Min)"):
            st.dataframe(df_res, use_container_width=True)
