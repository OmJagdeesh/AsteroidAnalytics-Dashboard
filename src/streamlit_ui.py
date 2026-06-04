"""
Step 5: Streamlit UI for monitoring
Run: streamlit run 5_streamlit_ui.py --server.port 8501 --server.address 0.0.0.0
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=False)

# Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'neo_db')
DB_USER = os.getenv('DB_USER', 'neo_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'neo_password')

# Create database connection
def get_db_connection():
    connection_params = {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }

    try:
        return psycopg2.connect(**connection_params)
    except psycopg2.OperationalError:
        if DB_HOST in {"timescaledb", "postgres", "db"}:
            return psycopg2.connect(**{**connection_params, "host": "localhost"})
        raise

def read_sql(query):
    with get_db_connection() as conn:
        return pd.read_sql(query, conn)

@st.cache_data(ttl=60)
def load_raw_data():
    query = """
    SELECT * FROM neo_raw 
    ORDER BY close_approach_date DESC 
    LIMIT 10000
    """
    return read_sql(query)

@st.cache_data(ttl=60)
def load_processed_data():
    query = """
    SELECT * FROM neo_processed 
    ORDER BY close_approach_date DESC 
    LIMIT 10000
    """
    return read_sql(query)

@st.cache_data(ttl=60)
def load_daily_metrics():
    query = "SELECT * FROM neo_daily_metrics ORDER BY metric_date"
    return read_sql(query)

@st.cache_data(ttl=60)
def get_summary_stats():
    query = """
    SELECT 
        COUNT(*) as total_asteroids,
        COALESCE(SUM(CASE WHEN is_potentially_hazardous THEN 1 ELSE 0 END), 0) as hazardous_count,
        COALESCE(AVG(risk_score), 0) as avg_risk_score,
        COALESCE(SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END), 0) as anomaly_count,
        MIN(close_approach_date) as start_date,
        MAX(close_approach_date) as end_date
    FROM neo_processed
    """
    return read_sql(query).iloc[0]

def main():
    st.set_page_config(
        page_title="NASA NEO Analytics Dashboard",
        page_icon="🌌",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Premium Custom CSS
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Glassmorphic Metrics */
        div[data-testid="metric-container"] {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px 0 rgba(0, 255, 255, 0.2);
            border: 1px solid rgba(0, 255, 255, 0.3);
        }
        div[data-testid="metric-container"] label {
            color: #a0a0a0 !important;
            font-size: 1rem !important;
        }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-weight: 800 !important;
        }
        
        /* Fancy Titles */
        h1 {
            background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800 !important;
        }
        h2, h3 {
            color: #e0e0e0 !important;
            font-weight: 600 !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111119 0%, #0d1222 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* Dataframes */
        div[data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }
        
        /* Plotly Containers */
        .js-plotly-plot {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Set premium plotly defaults
    pio.templates.default = "plotly_dark"
    pio.templates["plotly_dark"].layout.paper_bgcolor = "rgba(0,0,0,0)"
    pio.templates["plotly_dark"].layout.plot_bgcolor = "rgba(0,0,0,0)"
    
    st.title("🌌 NASA Near-Earth Object Analytics Dashboard")
    st.markdown("Real-time monitoring of asteroid approaches using Kafka, Spark & TimescaleDB")
    
    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Go to", ["Overview", "Raw Data", "Processed Data", "Daily Metrics", "Top Risks"])
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    if page == "Overview":
        show_overview()
    elif page == "Raw Data":
        show_raw_data()
    elif page == "Processed Data":
        show_processed_data()
    elif page == "Daily Metrics":
        show_daily_metrics()
    elif page == "Top Risks":
        show_top_risks()

def show_overview():
    st.header("📊 Overview")
    
    try:
        stats = get_summary_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Asteroids", f"{int(stats['total_asteroids']):,}")
        with col2:
            st.metric("Hazardous", f"{int(stats['hazardous_count']):,}")
        with col3:
            st.metric("Avg Risk Score", f"{stats['avg_risk_score']:.4f}")
        with col4:
            st.metric("Anomalies", f"{int(stats['anomaly_count']):,}")
        
        st.markdown(f"**Date Range:** {stats['start_date']} to {stats['end_date']}")
        
        st.markdown("---")
        
        daily = load_daily_metrics()
        
        if not daily.empty:
            st.subheader("📈 Daily Trends")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.line(
                    daily, 
                    x='metric_date', 
                    y='asteroid_count',
                    title='Daily Asteroid Count',
                    labels={'metric_date': 'Date', 'asteroid_count': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.line(
                    daily, 
                    x='metric_date', 
                    y='avg_risk_score',
                    title='Average Daily Risk Score',
                    labels={'metric_date': 'Date', 'avg_risk_score': 'Risk Score'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            col3, col4 = st.columns(2)
            
            with col3:
                fig = px.bar(
                    daily, 
                    x='metric_date', 
                    y='hazardous_count',
                    title='Hazardous Asteroids per Day',
                    labels={'metric_date': 'Date', 'hazardous_count': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col4:
                fig = px.line(
                    daily, 
                    x='metric_date', 
                    y='min_miss_distance_km',
                    title='Closest Approach Distance (km)',
                    labels={'metric_date': 'Date', 'min_miss_distance_km': 'Distance (km)'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

def show_raw_data():
    st.header("📋 Raw Data Table")
    
    try:
        df = load_raw_data()
        
        st.write(f"Showing {len(df)} most recent records")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            hazardous_filter = st.checkbox("Show only hazardous")
        with col2:
            search = st.text_input("Search by name")
        
        # Apply filters
        filtered_df = df.copy()
        if hazardous_filter:
            filtered_df = filtered_df[filtered_df['is_potentially_hazardous'] == True]
        if search:
            filtered_df = filtered_df[filtered_df['name'].str.contains(search, case=False, na=False)]
        
        # Display table
        display_cols = [
            'id', 'name', 'close_approach_date', 'is_potentially_hazardous',
            'miss_distance_km', 'relative_velocity_km_s', 
            'estimated_diameter_km_min', 'estimated_diameter_km_max'
        ]
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            height=600
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"neo_raw_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

def show_processed_data():
    st.header("⚙️ Processed Data Table")
    
    try:
        df = load_processed_data()
        
        st.write(f"Showing {len(df)} most recent processed records")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            risk_level = st.multiselect(
                "Risk Level",
                options=["Very Low", "Low", "Medium", "High", "Very High"],
                default=[]
            )
        with col2:
            anomaly_filter = st.checkbox("Show only anomalies")
        with col3:
            hazardous_filter = st.checkbox("Show only hazardous", key="proc_haz")
        
        # Apply filters
        filtered_df = df.copy()
        if risk_level:
            filtered_df = filtered_df[filtered_df['risk_level'].isin(risk_level)]
        if anomaly_filter:
            filtered_df = filtered_df[filtered_df['is_anomaly'] == True]
        if hazardous_filter:
            filtered_df = filtered_df[filtered_df['is_potentially_hazardous'] == True]
        
        # Display table
        display_cols = [
            'id', 'name', 'close_approach_date', 'is_potentially_hazardous',
            'diameter_mean_km', 'miss_distance_km', 'relative_velocity_km_s',
            'risk_score', 'risk_level', 'is_anomaly'
        ]
        
        # Color code by risk level
        def highlight_risk(row):
            if row['risk_level'] == 'Very High':
                return ['background-color: #ff4444'] * len(row)
            elif row['risk_level'] == 'High':
                return ['background-color: #ff8844'] * len(row)
            elif row['risk_level'] == 'Medium':
                return ['background-color: #ffcc44'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            height=600
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"neo_processed_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

def show_daily_metrics():
    st.header("📅 Daily Aggregated Metrics")
    
    try:
        df = load_daily_metrics()
        
        if df.empty:
            st.warning("No daily metrics available. Run 4_calculate_daily_metrics.py first.")
            return
        
        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"neo_daily_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

def show_top_risks():
    st.header("⚠️ Top Risk Asteroids")
    
    try:
        df = load_processed_data()
        
        # Top 20 by risk score
        top_risk = df.nlargest(20, 'risk_score')
        
        st.subheader("Top 20 Highest Risk Asteroids")
        st.dataframe(
            top_risk[[
                'name', 'close_approach_date', 'risk_score', 'risk_level',
                'diameter_mean_km', 'miss_distance_km', 'relative_velocity_km_s',
                'is_potentially_hazardous', 'is_anomaly'
            ]],
            use_container_width=True
        )
        
        # Scatter plot
        st.subheader("Risk Score vs Miss Distance")
        fig = px.scatter(
            df,
            x='miss_distance_km',
            y='relative_velocity_km_s',
            color='risk_score',
            size='diameter_mean_km',
            hover_data=['name', 'risk_level'],
            color_continuous_scale='Reds',
            title='Asteroid Risk Profile'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk distribution
        col1, col2 = st.columns(2)
        
        with col1:
            risk_counts = df['risk_level'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title='Risk Level Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(
                df,
                x='risk_score',
                nbins=30,
                title='Risk Score Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

if __name__ == "__main__":
    main()
