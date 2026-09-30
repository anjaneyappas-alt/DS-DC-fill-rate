import streamlit as st
import pandas as pd
import numpy as np

# Set page config
st.set_page_config(page_title="DC to DS Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")
st.caption("Upload TO Raised, TO Picked, and DC Stock files to run reconciliation and SKU-level inventory analysis.")

# --- SIDEBAR 3-FILE UPLOADER ---
st.sidebar.header("📁 Upload Data Files")
to_raised_file = st.sidebar.file_uploader("1. Upload TO Raised Data", type=["csv", "xlsx"])
to_picked_file = st.sidebar.file_uploader("2. Upload TO Picked/Sent Data", type=["csv", "xlsx"])
dc_stock_file = st.sidebar.file_uploader("3. Upload DC Stock Snapshot", type=["csv", "xlsx"])

use_demo = st.sidebar.checkbox("Use Demo Data (3 Files Example)", value=True)

def load_file(file):
    return pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)

if use_demo or (to_raised_file and to_picked_file and dc_stock_file):
    if use_demo:
        # 1. TO Raised Data
        df_to = pd.DataFrame({
            "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
            "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu"],
            "TO Qty": [1015, 397, 420, 480, 278, 402]
        })
        
        # 2. TO Picked / Dispatched Data (Handles multiple vehicles per DS)
        df_dispatch = pd.DataFrame({
            "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
            "TO Number": ["TO-02078", "TO-02080", "TO-02088", "TO-02086", "TO-02082", "TO-02089", "TO-02084", "TO-02087", "TO-02090"],
            "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu"],
            "Dispatched Qty": [206, 730, 38, 361, 158, 216, 428, 251, 366],
            "Qty Received": [206, 730, 38, 361, 158, 216, 428, 251, 366],
            "Damaged": [0, 0, 0, 0, 0, 0, 0, 0, 0]
        })

        # 3. SKU Level Breakdown & DC Stock
        df_sku_raised = pd.DataFrame({
            "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale"],
            "SKU": ["T1", "T2", "T3", "T1"],
            "Item Name": ["Premium Tea 250g", "Full Cream Milk 1L", "Sunflower Oil 1L", "Premium Tea 250g"],
            "Required Qty": [200, 500, 315, 200],
            "Sent Qty": [199, 475, 300, 180]
        })

        df_dc_stock = pd.DataFrame({
            "SKU": ["T1", "T2", "T3"],
            "DC Stock": [250, 0, 10]
        })
    else:
        df_to = load_file(to_raised_file)
        df_dispatch = load_file(to_picked_file)
        df_dc_stock = load_file(dc_stock_file)

        df_to.columns = df_to.columns.str.strip()
        df_dispatch.columns = df_dispatch.columns.str.strip()
        df_dc_stock.columns = df_dc_stock.columns.str.strip()

        df_sku_raised = df_to.copy()

    # --- MERGE DC STOCK INTO SKU BREAKDOWN ---
    if "SKU" in df_sku_raised.columns and "SKU" in df_dc_stock.columns:
        df_sku = pd.merge(df_sku_raised, df_dc_stock[['SKU', 'DC Stock']], on='SKU', how='left')
        df_sku['DC Stock'] = df_sku['DC Stock'].fillna(0).astype(int)
    else:
        df_sku = df_sku_raised.copy()

    # --- CALCULATIONS ---
    df_dispatch['Short Quantity'] = df_dispatch['Dispatched Qty'] - df_dispatch['Qty Received']

    # Total TO Qty per DS
    ds_totals = df_to.groupby('DS Name')['TO Qty'].sum().reset_index()
    merged_df = pd.merge(df_dispatch, ds_totals, on='DS Name', how='left')

    # Total Dispatched Qty across all vehicles per DS
    ds_dispatch_totals = merged_df.groupby('DS Name').agg(
        Total_Dispatched=('Dispatched Qty', 'sum')
    ).reset_index()

    ds_totals = pd.merge(ds_totals, ds_dispatch_totals, on='DS Name', how='left')
    ds_totals['DC TO Fill rate'] = (ds_totals['Total_Dispatched'] / ds_totals['TO Qty']) * 100
    ds_totals['Unsent Qty'] = ds_totals['TO Qty'] - ds_totals['Total_Dispatched']

    # Display formatting (show TO Qty & Fill Rate on first row of each DS group)
    merged_df['Is_First'] = ~merged_df.duplicated(subset=['DS Name'], keep='first')
    dc_fill_map = dict(zip(ds_totals['DS Name'], ds_totals['DC TO Fill rate']))
    unsent_map = dict(zip(ds_totals['DS Name'], ds_totals['Unsent Qty']))

    merged_df['DC TO Fill rate raw'] = merged_df['DS Name'].map(dc_fill_map)
    merged_df['Unsent Qty Raw'] = merged_df['DS Name'].map(unsent_map)

    table_df = merged_df.copy()
    table_df['TO Qty'] = table_df.apply(lambda r: f"{int(r['TO Qty']):,}" if r['Is_First'] and pd.notnull(r['TO Qty']) else "", axis=1)
    table_df['Unsent Qty'] = table_df.apply(lambda r: f"{int(r['Unsent Qty Raw']):,}" if r['Is_First'] and pd.notnull(r['Unsent Qty Raw']) else "", axis=1)
    table_df['DC TO Fill rate'] = table_df.apply(lambda r: f"{r['DC TO Fill rate raw']:.0f}%" if r['Is_First'] and pd.notnull(r['DC TO Fill rate raw']) else "", axis=1)
    table_df['TO Fill Rate'] = "100%"

    # Summary Metrics
    tot_to_qty = df_to['TO Qty'].sum()
    tot_dispatch = df_dispatch['Dispatched Qty'].sum()
    tot_unsent = tot_to_qty - tot_dispatch
    overall_fill_rate = (tot_dispatch / tot_to_qty) * 100 if tot_to_qty > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total TO Requested", f"{tot_to_qty:,}")
    c2.metric("Total Dispatched", f"{tot_dispatch:,}")
    c3.metric("Total Unsent Qty", f"{tot_unsent:,}")
    c4.metric("DC Fill Rate", f"{overall_fill_rate:.1f}%")

    st.markdown("---")
    
    # Export CSV Header
    col_h, col_b = st.columns([4, 1])
    with col_h:
        st.subheader("📋 Main Reconciliation Summary")
    with col_b:
        csv_data = table_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", data=csv_data, file_name="reconciliation_summary.csv", mime="text/csv", use_container_width=True)

    cols_order = ["Date", "TO Number", "DS Name", "TO Qty", "Dispatched Qty", "Qty Received", "Short Quantity", "Damaged", "Unsent Qty", "TO Fill Rate", "DC TO Fill rate"]
    
    st.dataframe(
        table_df[cols_order],
        use_container_width=True,
        hide_index=True,
        column_config={
            "TO Qty": st.column_config.TextColumn(alignment="right"),
            "Dispatched Qty": st.column_config.NumberColumn(alignment="right"),
            "Qty Received": st.column_config.NumberColumn(alignment="right"),
            "Short Quantity": st.column_config.NumberColumn(alignment="right"),
            "Damaged": st.column_config.NumberColumn(alignment="right"),
            "Unsent Qty": st.column_config.TextColumn(alignment="right"),
            "TO Fill Rate": st.column_config.TextColumn(alignment="center"),
            "DC TO Fill rate": st.column_config.TextColumn(alignment="center"),
        }
    )

    # --- SKU UNSENT & DC STOCK BREAKDOWN ---
    st.markdown("---")
    st.subheader("🔍 Unsent SKU Breakdown & DC Stock")

    selected_ds = st.selectbox("Select Dark Store to inspect SKU stock details:", options=df_to['DS Name'].unique())

    if not df_sku.empty and selected_ds in df_sku['DS Name'].values:
        sku_filtered = df_sku[df_sku['DS Name'] == selected_ds].copy()
        
        if "Required Qty" in sku_filtered.columns and "Sent Qty" in sku_filtered.columns:
            sku_filtered['Unsent Qty'] = sku_filtered['Required Qty'] - sku_filtered['Sent Qty']

        display_sku_cols = ["SKU", "Item Name", "Required Qty", "Sent Qty", "Unsent Qty", "DC Stock"]
        existing_cols = [c for c in display_sku_cols if c in sku_filtered.columns]

        st.dataframe(
            sku_filtered[existing_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Required Qty": st.column_config.NumberColumn(alignment="right"),
                "Sent Qty": st.column_config.NumberColumn(alignment="right"),
                "Unsent Qty": st.column_config.NumberColumn(alignment="right"),
                "DC Stock": st.column_config.NumberColumn(alignment="right"),
            }
        )
    else:
        st.info("No SKU-level breakdown available for the selected Dark Store.")

else:
    st.info("👈 Please upload all 3 files in the sidebar to generate the report.")
