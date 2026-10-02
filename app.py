import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="DS Transfer Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")

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
        'TO Qty': 'TO Qty', 'Required Qty': 'TO Qty', 'Quantity Required': 'TO Qty'
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

if input_method == "📋 Copy-Paste Data":
    col_a, col_b = st.columns(2)
    with col_a:
        paste_to = st.text_area("Paste TO Raised Data (Draft 1-2 PM)", height=180)
        df_to = parse_pasted_data(paste_to)
    with col_b:
        paste_dispatch = st.text_area("Paste Transfer Order / Dispatch Data", height=180)
        df_dispatch = parse_pasted_data(paste_dispatch)

elif input_method == "📁 Upload Files":
    file_to = st.sidebar.file_uploader("1. TO Raised File (Draft 1-2 PM)", type=["csv", "xlsx"])
    file_dispatch = st.sidebar.file_uploader("2. TO Picked / Dispatch File", type=["csv", "xlsx"])
    if file_to and file_dispatch:
        df_to = load_file(file_to)
        df_dispatch = load_file(file_dispatch)

else:  # Demo Data
    df_to = pd.DataFrame({
        "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar"],
        "TO Qty": [1015, 601, 800, 188, 520, 402, 576, 126]
    })
    
    df_dispatch = pd.DataFrame({
        "Date": ["2026-10-02"] * 8,
        "TO Number": ["TO-07369", "TO-07370", "TO-07361", "TO-07360", "TO-07368", "TO-07371", "TO-07364", "TO-07387"],
        "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar"],
        "Dispatched Qty": [557, 601, 774, 188, 520, 172, 576, 126],
        "Reason": ["HomeRun picker · TO-07333 · vehicle KA01AP5507", "HomeRun picker · TO-07334 · vehicle KA52A0811", "HomeRun picker · TO-07335 · vehicle KA52B0355", "Internal Transfer", "HomeRun picker · TO-07337 · vehicle KA02AN1565", "HomeRun picker · TO-07338 · vehicle KA03AN0421", "HomeRun picker · TO-07345 · vehicle KA52B7406", "Internal Transfer"]
    })

# --- RECONCILIATION PROCESSING ---
if df_to is not None and df_dispatch is not None:
    
    # Extract Draft TO Number
    if 'Reason' in df_dispatch.columns:
        def extract_draft_to(reason):
            match = re.search(r'TO-\d+', str(reason))
            return match.group(0) if match else "Direct / Manual"
        df_dispatch['Draft TO (1-2 PM)'] = df_dispatch['Reason'].apply(extract_draft_to)
    else:
        df_dispatch['Draft TO (1-2 PM)'] = df_dispatch['TO Number']

    grouped_dispatch = df_dispatch.groupby(['Date', 'TO Number', 'DS Name', 'Draft TO (1-2 PM)'], as_index=False).agg({
        'Dispatched Qty': 'sum'
    })

    if 'TO Qty' in df_to.columns:
        df_to['TO Qty'] = pd.to_numeric(df_to['TO Qty'], errors='coerce').fillna(0)
        ds_totals = df_to.groupby('DS Name')['TO Qty'].sum().reset_index()
    else:
        ds_totals = pd.DataFrame(df_to['DS Name'].unique(), columns=['DS Name'])
        ds_totals['TO Qty'] = 0

    merged_df = pd.merge(grouped_dispatch, ds_totals, on='DS Name', how='left')

    ds_dispatch_totals = merged_df.groupby('DS Name').agg(
        Total_Dispatched=('Dispatched Qty', 'sum')
    ).reset_index()

    ds_totals = pd.merge(ds_totals, ds_dispatch_totals, on='DS Name', how='left')
    ds_totals['Unsent Qty'] = ds_totals['TO Qty'] - ds_totals['Total_Dispatched']
    ds_totals['DC TO Fill rate'] = np.where(ds_totals['TO Qty'] > 0, (ds_totals['Total_Dispatched'] / ds_totals['TO Qty']) * 100, 0)

    merged_df['Is_First'] = ~merged_df.duplicated(subset=['DS Name'], keep='first')
    unsent_map = dict(zip(ds_totals['DS Name'], ds_totals['Unsent Qty']))
    dc_fill_map = dict(zip(ds_totals['DS Name'], ds_totals['DC TO Fill rate']))

    merged_df['Unsent Qty Raw'] = merged_df['DS Name'].map(unsent_map)
    merged_df['DC TO Fill rate raw'] = merged_df['DS Name'].map(dc_fill_map)

    table_df = merged_df.copy()
    table_df['TO Qty'] = table_df.apply(lambda r: f"{int(r['TO Qty']):,}" if r['Is_First'] and pd.notnull(r['TO Qty']) and r['TO Qty'] != 0 else "", axis=1)
    table_df['Unsent Qty'] = table_df.apply(lambda r: f"{int(r['Unsent Qty Raw']):,}" if r['Is_First'] and pd.notnull(r['Unsent Qty Raw']) else "", axis=1)
    table_df['DC TO Fill rate'] = table_df.apply(lambda r: f"{r['DC TO Fill rate raw']:.0f}%" if r['Is_First'] and pd.notnull(r['DC TO Fill rate raw']) else "", axis=1)
    table_df['TO Fill Rate'] = "100%"

    tot_to_qty = ds_totals['TO Qty'].sum()
    tot_dispatch = grouped_dispatch['Dispatched Qty'].sum()
    tot_unsent = tot_to_qty - tot_dispatch
    overall_fill_rate = (tot_dispatch / tot_to_qty) * 100 if tot_to_qty > 0 else 0

    # Summary Alert Box for Large Unsent Quantities
    if tot_unsent > 0:
        st.warning(f"⚠️ **Unsent Quantity Alert:** Total **{tot_unsent:,} units** were requested but not dispatched across the Dark Stores (DC Fill Rate: **{overall_fill_rate:.1f}%**).")

    total_row = pd.DataFrame([{
        "Date": "",
        "Draft TO (1-2 PM)": "",
        "TO Number": "TOTAL",
        "DS Name": "",
        "TO Qty": f"{tot_to_qty:.0f}",
        "Dispatched Qty": tot_dispatch,
        "Unsent Qty": f"{tot_unsent:.0f}",
        "TO Fill Rate": "100%",
        "DC TO Fill rate": f"{overall_fill_rate:.0f}%"
    }])

    cols_order = [
        "Date", "Draft TO (1-2 PM)", "TO Number", "DS Name", "TO Qty", 
        "Dispatched Qty", "Unsent Qty", "TO Fill Rate", "DC TO Fill rate"
    ]

    final_display = pd.concat([table_df[cols_order], total_row[cols_order]], ignore_index=True)

    st.markdown("---")
    
    st.dataframe(
        final_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "TO Qty": st.column_config.TextColumn("TO Raised Qty", alignment="right"),
            "Dispatched Qty": st.column_config.NumberColumn("Sent Qty", alignment="right"),
            "Unsent Qty": st.column_config.TextColumn("Unsent Qty", alignment="right"),
            "TO Fill Rate": st.column_config.TextColumn(alignment="center"),
            "DC TO Fill rate": st.column_config.TextColumn(alignment="center"),
        }
    )
else:
    st.info("👈 Please enter data or select demo mode in the sidebar to generate the report.")
