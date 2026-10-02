import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="Single-File Transfer Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")
st.caption("Upload your single ERP/WMS Transfer Order file to view DS-wise raised vs sent summary.")

# --- SIDEBAR INPUT ---
st.sidebar.header("📥 Upload Single Data File")
uploaded_file = st.sidebar.file_uploader("Upload Transfer Order File", type=["csv", "xlsx"])

use_demo = st.sidebar.checkbox("Use Demo Data", value=(uploaded_file is None))

def load_data(file):
    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    df.columns = df.columns.astype(str).str.strip()
    return df

df = None

if uploaded_file is not None:
    df = load_data(uploaded_file)
elif use_demo:
    # Sample structure matching your Excel file
    df = pd.DataFrame({
        "Date": ["2026-10-02"] * 8,
        "To Location Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar"],
        "Transfer Order#": ["TO-07369", "TO-07370", "TO-07361", "TO-07360", "TO-07368", "TO-07371", "TO-07364", "TO-07387"],
        "Quantity Transferred": [557, 601, 774, 188, 520, 172, 576, 126],
        "Reason": [
            "HomeRun picker · TO-07333 · vehicle KA01AP5507",
            "HomeRun picker · TO-07334 · vehicle KA52A0811",
            "HomeRun picker · TO-07335 · vehicle KA52B0355",
            "Internal Transfer - created by anjaneyappa.s@home-run.co",
            "HomeRun picker · TO-07337 · vehicle KA02AN1565",
            "HomeRun picker · TO-07338 · vehicle KA03AN0421",
            "HomeRun picker · TO-07345 · vehicle KA52B7406",
            "Internal Transfer 1/2 - created by anjaneyappa.s@home-run.co"
        ]
    })

if df is not None:
    # 1. Map standard columns flexible to naming variations
    col_map = {
        'To Location Name': 'DS Name', 'To Location': 'DS Name', 'DS Name': 'DS Name',
        'Transfer Order#': 'Dispatched TO', 'Transfer Order': 'Dispatched TO', 'TO Number': 'Dispatched TO',
        'Quantity Transferred': 'Sent Qty', 'Dispatched Qty': 'Sent Qty', 'Quantity': 'Sent Qty'
    }
    
    for old_col, new_col in col_map.items():
        if old_col in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)

    # Clean Date formatting
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(df['Date'])
    else:
        df['Date'] = ""

    # Ensure numeric sent quantity
    df['Sent Qty'] = pd.to_numeric(df['Sent Qty'], errors='coerce').fillna(0)

    # 2. Extract Draft TO Raised (1-2 PM) from Reason column if available
    if 'Reason' in df.columns:
        def extract_draft_to(reason):
            match = re.search(r'TO-\d+', str(reason))
            return match.group(0) if match else "Direct / Manual"
        df['Draft TO Raised (1-2 PM)'] = df['Reason'].apply(extract_draft_to)
    else:
        df['Draft TO Raised (1-2 PM)'] = df['Dispatched TO']

    # 3. Aggregate SKU-level rows into single TO totals
    grouped = df.groupby(['Date', 'DS Name', 'Draft TO Raised (1-2 PM)', 'Dispatched TO'], as_index=False).agg({
        'Sent Qty': 'sum'
    })

    # 4. Calculate DS-level Totals
    ds_summary = grouped.groupby('DS Name').agg(
        Total_Sent_Qty=('Sent Qty', 'sum'),
        TO_Count=('Dispatched TO', 'nunique')
    ).reset_index()

    # Map totals for multi-TO dispatches per DS
    grouped['Is_First'] = ~grouped.duplicated(subset=['DS Name'], keep='first')
    ds_totals_map = dict(zip(ds_summary['DS Name'], ds_summary['Total_Sent_Qty']))
    
    grouped['DS Total Sent Qty Raw'] = grouped['DS Name'].map(ds_totals_map)
    grouped['DS Total Sent Qty'] = grouped.apply(
        lambda r: f"{int(r['DS Total Sent Qty Raw']):,}" if r['Is_First'] else "", axis=1
    )

    # 5. Format Top Metric Cards
    tot_sent = grouped['Sent Qty'].sum()
    tot_ds_count = grouped['DS Name'].nunique()
    tot_tos_count = grouped['Dispatched TO'].nunique()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Dark Stores", f"{tot_ds_count}")
    m2.metric("Total Dispatched TOs", f"{tot_tos_count}")
    m3.metric("Total Sent / In-Transit Qty", f"{tot_sent:,}")

    st.markdown("---")

    col_h, col_b = st.columns([4, 1])
    with col_h:
        st.subheader("📋 Dark Store Transfer Summary")
    with col_b:
        csv_data = grouped.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", data=csv_data, file_name="single_file_reconciliation.csv", mime="text/csv", use_container_width=True)

    # 6. Bottom Total Row
    total_row = pd.DataFrame([{
        "Date": "",
        "DS Name": "TOTAL",
        "Draft TO Raised (1-2 PM)": "",
        "Dispatched TO": "TOTAL",
        "Sent Qty": tot_sent,
        "DS Total Sent Qty": f"{tot_sent:,}"
    }])

    cols_order = ["Date", "DS Name", "Draft TO Raised (1-2 PM)", "Dispatched TO", "Sent Qty", "DS Total Sent Qty"]
    final_table = pd.concat([grouped[cols_order], total_row[cols_order]], ignore_index=True)

    # Display Table
    st.dataframe(
        final_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sent Qty": st.column_config.NumberColumn("Sent Qty (per TO)", alignment="right"),
            "DS Total Sent Qty": st.column_config.TextColumn("Total In-Transit Qty (per DS)", alignment="right"),
        }
    )

else:
    st.info("👈 Please upload your Transfer Order file in the sidebar to view the report.")
