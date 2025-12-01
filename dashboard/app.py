import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components 
from sqlalchemy import create_engine
from dotenv import load_dotenv
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_agent.backend import AnalyticsAgent 
from analytics.graph_algo import SuspiciousBehaviorDetector 
from analytics.visuals import generate_cluster_map 

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


logo_path = "dashboard/assets/sauroneye.png" 
try:
    page_icon_img = Image.open(logo_path)
except:
    page_icon_img = "👁️"

st.set_page_config(page_title="Sauron Eye", layout="wide", page_icon=page_icon_img)

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FF4B4B !important; }
    div[data-testid="stMetricValue"] { color: #FFA500 !important; }
    iframe { display: block; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    return create_engine(db_url)

try:
    engine = get_db_connection()
except:
    st.error("Database Connection Failed.")
    st.stop()

@st.cache_data(ttl=60)
def load_data():
    try:
        query = "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 2000"
        df = pd.read_sql(query, engine)
        if 'amount' in df.columns:
            df['Risk Label'] = df['amount'].apply(lambda x: "🐋 Whale" if x > 4000 else ("🦐 Shrimp" if x < 10 else "👤 User"))
        if 'tx_type' not in df.columns: df['tx_type'] = 'Unknown'
        else: df['tx_type'] = df['tx_type'].fillna('Unknown')
        return df
    except:
        return pd.DataFrame(columns=['sender', 'amount', 'timestamp', 'tx_hash', 'tx_type', 'details', 'Risk Label'])

def show_overview(df):
    st.header("Network Overview")
    if df.empty:
        st.warning("Database empty. Use Admin Sidebar to seed data.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Transactions", len(df))
    m2.metric("Volume", f"{df['amount'].sum():,} BBN")
    m3.metric("Whales", len(df[df['Risk Label'] == "🐋 Whale"]))

    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_vol = df.groupby('date')['amount'].sum().reset_index()
    fig = px.bar(daily_vol, x='date', y='amount', title="Daily Volume", color_discrete_sequence=['#FF4B4B'])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Live Feed")
    st.dataframe(df.head(10), use_container_width=True)

def show_cluster(df):
    st.header(" Wallet Cluster Inspector")
    if df.empty:
        st.warning("No Data.")
        return

    senders = df['sender'].unique().tolist() if 'sender' in df.columns else []
    target = st.selectbox("Select Suspect:", senders)
    
    if target:
        c1, c2 = st.columns([3, 1])
        with c1:
            html = generate_cluster_map(df.head(1000), target)
            components.html(html, height=600, scrolling=True)
        with c2:
            st.markdown("### Forensics")
            st.write(f"**Target:** `{target[:10]}...`")
            if st.button("Run AI Analysis"):
                if api_key:
                    with st.spinner("Profiling..."):
                        agent = AnalyticsAgent(api_key=api_key)
                        st.info(agent.analyze_wallet_deep_dive(target))
                else:
                    st.error("No API Key")

def show_protocol(df):
    st.header("Protocol Activity")
    if df.empty:
        st.warning("No Data.")
        return

    if 'tx_type' in df.columns:
        counts = df['tx_type'].value_counts().reset_index()
        counts.columns = ['Type', 'Count']
        
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(counts, values='Count', names='Type', title="Transaction Types", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.metric("BTC Delegations", len(df[df['tx_type'] == "BTC_Stake"]))
            st.metric("Governance Votes", len(df[df['tx_type'] == "Governance_Vote"]))

        st.divider()
        st.subheader("Event Log")
        st.dataframe(df[['timestamp', 'tx_type', 'details']].head(20), use_container_width=True)

def show_ai():
    st.header("Ask Sauron")
    q = st.chat_input("Ask about the blockchain data...")
    if q:
        st.chat_message("user").write(q)
        if api_key:
            agent = AnalyticsAgent(api_key=api_key)
            st.chat_message("assistant").write(agent.ask(q))
        else:
            st.error("No API Key.")


df = load_data()

with st.sidebar:
    try:
        st.image(logo_path, use_container_width=True)
    except:
        st.write(" **SAURON EYE**")
        
    st.caption("VERSION 7.0 (COMPLETE)") 
    
    page = st.radio("Navigate", ["Network Overview", "Cluster Inspector", "Protocol Activity", "AI Analyst"])
    
    st.divider()
    if st.button("RESET & SEED DATA"):
        try:
            from seed_crime_data import run_seed 
            run_seed()
            st.cache_data.clear()
            st.success("Reset Done!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

c1, c2 = st.columns([1, 15])
with c1: 
    try:
        st.image(logo_path, width=60)
    except:
        pass 
with c2: 
    st.markdown("# SAURON EYE")
st.caption("The All-Seeing Lens for Babylon Chain")
st.divider()

if page == "Network Overview":
    show_overview(df)
elif page == "Cluster Inspector":
    show_cluster(df)
elif page == "Protocol Activity":
    show_protocol(df)
elif page == "AI Analyst":
    show_ai()