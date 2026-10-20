import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="DS Transfer Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")

uploaded_file = st.file_uploader("Upload Transfer Order File", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str).str.strip()

    # Filter DC to DS transfers
    dc_df = df[df['From Location Name'].str.contains('DC', na=False) & df['To Location Name'].str.contains('DS', na=False)].copy()

    pattern = r'Internal Transfer|HomeRun picker|Internal Transfer - created by'
    filtered = dc_df[dc_df['Reason'].str.contains(pattern, case=False, na=False)].copy()

    # Draft TO Raised
    draft_df = filtered[filtered['Status'] == 'Draft'].groupby('To Location Name').agg(
        TO_Qty=('Quantity Transferred', 'sum')
    ).reset_index()

    # Sent Dispatched TOs
    dispatched_df = filtered[filtered['Status'].isin(['Transferred', 'In Transit'])].groupby(['Date', 'Transfer Order#', 'To Location Name']).agg(
        Dispatched_Qty=('Quantity Transferred', 'sum')
    ).reset_index()

    dispatched_df['Date'] = pd.to_datetime(dispatched_df['Date']).dt.strftime('%d/%m/%Y')

    # Merge
    merged = pd.merge(dispatched_df, draft_df, on='To Location Name', how='left')

    ds_sent_totals = dispatched_df.groupby('To Location Name').agg(
        Total_Dispatched=('Dispatched_Qty', 'sum')
    ).reset_index()

    draft_df = pd.merge(draft_df, ds_sent_totals, on='To Location Name', how='left').fillna(0)
    draft_df['DC TO Fill rate'] = (draft_df['Total_Dispatched'] / draft_df['TO_Qty']) * 100

    merged['Is_First'] = ~merged.duplicated(subset=['To Location Name'], keep='first')

    dc_fill_map = dict(zip(draft_df['To Location Name'], draft_df['DC TO Fill rate']))
    to_qty_map = dict(zip(draft_df['To Location Name'], draft_df['TO_Qty']))

    merged['TO Qty Raw'] = merged['To Location Name'].map(to_qty_map)
    merged['DC TO Fill rate Raw'] = merged['To Location Name'].map(dc_fill_map)

    merged['TO Qty'] = merged.apply(lambda r: f"{int(r['TO Qty Raw']):,}" if r['Is_First'] and pd.notnull(r['TO Qty Raw']) else "", axis=1)
    merged['Qty Received (as per DS)'] = merged['Dispatched_Qty']
    merged['Short Quantity'] = ""
    merged['Damaged'] = ""
    merged['TO Fill Rate'] = "100%"
    merged['DC TO Fill rate'] = merged.apply(lambda r: f"{r['DC TO Fill rate Raw']:.0f}%" if r['Is_First'] and pd.notnull(r['DC TO Fill rate Raw']) else "", axis=1)
    merged['Remarks'] = ""

    # Summary Row
    tot_to_qty = draft_df['TO_Qty'].sum()
    tot_dispatch = dispatched_df['Dispatched_Qty'].sum()
    overall_fill_rate = (tot_dispatch / tot_to_qty) * 100

    total_row = pd.DataFrame([{
        "Date": "",
        "Transfer Order#": "0",
        "To Location Name": "",
        "TO Qty": f"{int(tot_to_qty):,}",
        "Dispatched_Qty": tot_dispatch,
        "Qty Received (as per DS)": tot_dispatch,
        "Short Quantity": "",
        "Damaged": "",
        "TO Fill Rate": "100%",
        "DC TO Fill rate": f"{overall_fill_rate:.0f}%",
        "Remarks": ""
    }])

    cols_order = [
        "Date", "Transfer Order#", "To Location Name", "TO Qty", "Dispatched_Qty", 
        "Qty Received (as per DS)", "Short Quantity", "Damaged", 
        "TO Fill Rate", "DC TO Fill rate", "Remarks"
    ]

    final_display = pd.concat([merged[cols_order], total_row[cols_order]], ignore_index=True)
    final_display.rename(columns={'Transfer Order#': 'TO Number', 'To Location Name': 'DS Name', 'Dispatched_Qty': 'Dispatched Qty'}, inplace=True)

    st.dataframe(
        final_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "TO Qty": st.column_config.TextColumn(alignment="right"),
            "Dispatched Qty": st.column_config.NumberColumn(alignment="right"),
            "Qty Received (as per DS)": st.column_config.NumberColumn(alignment="right"),
            "TO Fill Rate": st.column_config.TextColumn(alignment="center"),
            "DC TO Fill rate": st.column_config.TextColumn(alignment="center"),
        }
    )
