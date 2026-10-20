import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="Transfer Reconciliation Dashboard", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("📥 Choose Mode")
app_mode = st.sidebar.radio(
    "Select Functionality:", 
    [
        "🚚 1. Upload Sent Data Only (TO Number & Reason)",
        "📁 2. Dual Upload (Raised vs Sent Reconciliation)",
        "📋 3. Copy-Paste Raw Data"
    ]
)

def standardize_columns(df):
    if df is None or df.empty:
        return df

    df.columns = df.columns.astype(str).str.strip()

    column_mapping = {
        'DS Name': 'DS Name', 'To Location Name': 'DS Name', 'To Location': 'DS Name', 'Dark Store': 'DS Name',
        'Quantity Transferred': 'Sent Qty', 'Dispatched Qty': 'Sent Qty', 'Sent Qty': 'Sent Qty', 'Quantity': 'Sent Qty', 'TO Qty': 'Sent Qty',
        'Transfer Order#': 'TO Number', 'Transfer Order': 'TO Number', 'TO Number': 'TO Number', 'TO No': 'TO Number',
        'Reason': 'Reason', 'Status': 'Status', 'SKU': 'SKU'
    }

    new_cols = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        for key, val in column_mapping.items():
            if col_lower == key.lower():
                new_cols[col] = val
                break
            
    return df.rename(columns=new_cols)

def load_file(file):
    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    return standardize_columns(df)

def parse_pasted_data(text_data):
    if not text_data or not text_data.strip():
        return None
    try:
        try:
            df = pd.read_csv(io.StringIO(text_data), sep="\t")
            if len(df.columns) <= 1:
                df = pd.read_csv(io.StringIO(text_data), sep=",")
        except:
            df = pd.read_csv(io.StringIO(text_data), sep=",")
        return standardize_columns(df)
    except Exception as e:
        st.error(f"Error reading pasted data: {e}")
        return None

# ==============================================================================
# MODE 1: UPLOAD SENT DATA ONLY (TO NUMBER & REASON)
# ==============================================================================
if app_mode == "🚚 1. Upload Sent Data Only (TO Number & Reason)":
    st.subheader("🚚 Dispatched / Sent Data Summary")
    st.caption("Upload your Sent/Dispatched TO file to get a breakdown by TO Number, Dark Store, Reason, and Sent Quantity.")

    sent_file = st.file_uploader("Upload Dispatched / Sent Data File", type=["xlsx", "xls", "csv"])
    use_demo_sent = st.checkbox("Use Sample Sent Data", value=(sent_file is None))

    df_sent = None

    if sent_file is not None:
        df_sent = load_file(sent_file)
    elif use_demo_sent:
        # Sample dataset structure matching Transfer Order files
        df_sent = pd.DataFrame({
            "Date": ["2026-10-10"] * 8,
            "TO Number": ["TO-08171", "TO-08185", "TO-08186", "TO-08170", "TO-08184", "TO-08174", "TO-08177", "TO-08162"],
            "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar", "DS01 Sarjapur"],
            "Sent Qty": [1178, 1069, 475, 1260, 637, 687, 691, 151],
            "
