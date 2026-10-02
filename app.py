import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Transfer Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")

# --- SIDEBAR INPUT ---
st.sidebar.header("📥 Data Input Options")
input_method = st.sidebar.radio("Choose Input Method:", ["📋 Copy-Paste Data", "📁 Upload Files", "🔘 Demo Data"])

def standardize_columns(df):
    if df is None or df.empty:
        return df

    df.columns = df.columns.astype(str).str.strip()

    column_mapping = {
        'DS Name': 'DS Name', 'To Location Name': 'DS Name', 'To Location': 'DS Name',
        'Quantity Transferred': 'Dispatched Qty', 'Dispatched Qty': 'Dispatched Qty', 
        'Sent Qty': 'Dispatched Qty', 'Quantity': 'Dispatched Qty',
        'Transfer Order#': 'TO Number', 'Transfer Order': 'TO Number', 'TO Number': 'TO Number',
        'TO Qty': 'TO Qty', 'Required Qty': 'TO Qty',
        'Qty Received': 'Qty Received (as per DS)', 'Qty Received (as per DS)': 'Qty Received (as per DS)'
    }

    new_cols = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        for key, val in column_mapping.items():
            if col_lower == key.lower():
                new_cols[col] = val
                break
            
    return df.rename(columns=new_cols)

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

def load_file(file):
    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    return standardize_columns(df)

df_to = None
df_dispatch = None

# --- INPUT HANDLING ---
if input_method == "📋 Copy-Paste Data":
    col_a, col_b = st.columns(2)
    with col_a:
        paste_to = st.text_area("Paste TO Raised Data", height=180)
        df_to = parse_pasted_data(paste_to)
    with col_b:
        paste_dispatch = st.text_area("Paste Dispatch Data", height=180)
        df_dispatch = parse_pasted_data(paste_dispatch)

elif input_method == "📁 Upload Files":
    file_to = st.sidebar.file_uploader("1. TO Raised File", type=["csv", "xlsx"])
    file_dispatch = st.sidebar.file_uploader("2. TO Picked File", type=["csv", "xlsx"])
    if file_to and file_dispatch:
        df_to = load_file(file_to)
        df_dispatch = load_file(file_dispatch)

else:  # Demo Data
    df_to = pd.DataFrame({
        "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
        "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu"],
        "TO Qty": [1015, 397, 420, 480, 278, 402]
    })
    
    df_dispatch = pd.DataFrame({
        "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
        "TO Number": ["TO-02078", "TO-02080", "TO-02088", "TO-02086", "TO-02082", "TO-02089", "TO-02084", "TO-02087", "TO-02090"],
        "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu"],
        "Dispatched Qty": [206, 730, 38, 361, 158, 216, 428, 251, 366],
        "Qty Received (as per DS)": [206, 730, 38, 361, 158, 216, 428, 251, 366]
    })

# --- RECONCILIATION PROCESSING ---
if df_to is not None and df_dispatch is not None:
    
    # Fallback column mapping
    if 'DS Name' not in df_dispatch.columns and 'To Location Name' in df_dispatch.columns:
        df_dispatch.rename(columns={'To Location Name': 'DS Name'}, inplace=True)
    if 'Dispatched Qty' not in df_dispatch.columns and 'Quantity Transferred' in df_dispatch.columns:
        df_dispatch.rename(columns={'Quantity Transferred': 'Dispatched Qty'}, inplace=True)

    if 'DS Name' in df_dispatch.columns and 'Dispatched Qty' in df_dispatch.columns:
        
        # Populate missing standard columns
        for col in ['Qty Received (as per DS)', 'Short Quantity', 'Damaged', 'Date', 'TO Number', 'Remarks']:
            if col not in df_dispatch.columns:
                df_dispatch[col] = df_dispatch['Dispatched Qty'] if col == 'Qty Received (as per DS)' else ""

        # Numeric conversions
        df_dispatch['Dispatched Qty'] = pd.to_numeric(df_dispatch['Dispatched Qty'], errors='coerce').fillna(0)
        df_dispatch['Qty Received (as per DS)'] = pd.to_numeric(df_dispatch['Qty Received (as per DS)'], errors='coerce').fillna(0)

        # TO Qty per DS
        if 'TO Qty' in df_to.columns:
            df_to['TO Qty'] = pd.to_numeric(df_to['TO Qty'], errors='coerce').fillna(0)
            ds_totals = df_to.groupby('DS Name')['TO Qty'].sum().reset_index()
        else:
            ds_totals = pd.DataFrame(df_to['DS Name'].unique(), columns=['DS Name'])
            ds_totals['TO Qty'] = 0

        merged_df = pd.merge(df_dispatch, ds_totals, on='DS Name', how='left')

        # Total Dispatched Qty per DS
        ds_dispatch_totals = merged_df.groupby('DS Name').agg(
            Total_Dispatched=('Dispatched Qty', 'sum')
        ).reset_index()

        ds_totals = pd.merge(ds_totals, ds_dispatch_totals, on='DS Name', how='left')
        ds_totals['DC TO Fill rate'] = np.where(ds_totals['TO Qty'] > 0, (ds_totals['Total_Dispatched'] / ds_totals['TO Qty']) * 100, 0)

        # Flags for displaying TO Qty and DC Fill rate ONLY on 1st row of each DS group
        merged_df['Is_First'] = ~merged_df.duplicated(subset=['DS Name'], keep='first')
        dc_fill_map = dict(zip(ds_totals['DS Name'], ds_totals['DC TO Fill rate']))

        merged_df['DC TO Fill rate raw'] = merged_df['DS Name'].map(dc_fill_map)

        table_df = merged_df.copy()
        table_df['TO Qty'] = table_df.apply(lambda r: f"{int(r['TO Qty']):,}" if r['Is_First'] and pd.notnull(r['TO Qty']) and r['TO Qty'] != 0 else "", axis=1)
        table_df['DC TO Fill rate'] = table_df.apply(lambda r: f"{r['DC TO Fill rate raw']:.0f}%" if r['Is_First'] and pd.notnull(r['DC TO Fill rate raw']) else "", axis=1)
        table_df['TO Fill Rate'] = "100%"

        # Calculate Summary Bottom Row
        tot_to_qty = ds_totals['TO Qty'].sum()
        tot_dispatch = df_dispatch['Dispatched Qty'].sum()
        tot_received = df_dispatch['Qty Received (as per DS)'].sum()
        overall_fill_rate = (tot_dispatch / tot_to_qty) * 100 if tot_to_qty > 0 else 0

        total_row = pd.DataFrame([{
            "Date": "",
            "TO Number": "0",
            "DS Name": "",
            "TO Qty": f"{tot_to_qty:.0f}",
            "Dispatched Qty": tot_dispatch,
            "Qty Received (as per DS)": tot_received,
            "Short Quantity": "",
            "Damaged": "",
            "TO Fill Rate": "100%",
            "DC TO Fill rate": f"{overall_fill_rate:.0f}%",
            "Remarks": ""
        }])

        cols_order = [
            "Date", "TO Number", "DS Name", "TO Qty", "Dispatched Qty", 
            "Qty Received (as per DS)", "Short Quantity", "Damaged", 
            "TO Fill Rate", "DC TO Fill rate", "Remarks"
        ]

        final_display = pd.concat([table_df[cols_order], total_row[cols_order]], ignore_index=True)

        st.markdown("---")
        
        # Display Table matching image layout
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
else:
    st.info("👈 Please enter data or select demo mode in the sidebar to generate the report.")
