import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="Dual Input Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")
st.caption("Upload or paste BOTH 'TO Raised (Draft)' and 'TO Sent (Dispatched)' datasets for reconciliation.")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("📥 Data Input Method")
input_method = st.sidebar.radio("Choose Input Method:", ["📁 Upload 2 Files", "📋 Copy-Paste 2 Datasets", "🔘 Load Demo Datasets"])

def standardize_columns(df):
    if df is None or df.empty:
        return df

    df.columns = df.columns.astype(str).str.strip()

    column_mapping = {
        'DS Name': 'DS Name', 'To Location Name': 'DS Name', 'To Location': 'DS Name', 'Dark Store': 'DS Name',
        'Quantity Transferred': 'Qty', 'Dispatched Qty': 'Qty', 'Sent Qty': 'Qty', 'Quantity': 'Qty', 'TO Qty': 'Qty', 'Required Qty': 'Qty',
        'Transfer Order#': 'TO Number', 'Transfer Order': 'TO Number', 'TO Number': 'TO Number', 'TO No': 'TO Number'
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

df_draft = None
df_sent = None

# --- INPUT HANDLING ---
if input_method == "📁 Upload 2 Files":
    col_file1, col_file2 = st.columns(2)
    with col_file1:
        file_draft = st.file_uploader("1. Upload TO Raised (Draft) File", type=["csv", "xlsx"])
        if file_draft:
            df_draft = load_file(file_draft)
            st.success(f"Loaded Raised Data ({len(df_draft):,} rows)")

    with col_file2:
        file_sent = st.file_uploader("2. Upload TO Sent (Dispatched) File", type=["csv", "xlsx"])
        if file_sent:
            df_sent = load_file(file_sent)
            st.success(f"Loaded Sent Data ({len(df_sent):,} rows)")

elif input_method == "📋 Copy-Paste 2 Datasets":
    col_paste1, col_paste2 = st.columns(2)
    with col_paste1:
        st.markdown("**1. TO Raised Data (Draft 1–2 PM)**")
        paste_draft = st.text_area("Paste TO Raised Data", height=200)
        df_draft = parse_pasted_data(paste_draft)

    with col_paste2:
        st.markdown("**2. TO Sent Data (Dispatched / Picked)**")
        paste_sent = st.text_area("Paste TO Sent Data", height=200)
        df_sent = parse_pasted_data(paste_sent)

else:  # Load Demo Datasets
    df_draft = pd.DataFrame({
        "Date": ["2026-10-10"] * 9,
        "TO Number": ["TO-08138", "TO-08191", "TO-08179", "TO-08180", "TO-08187", "TO-08139", "TO-08181", "TO-08140", "TO-08141"],
        "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar"],
        "Qty": [1178, 917, 1069, 475, 552, 1260, 637, 687, 691]
    })

    df_sent = pd.DataFrame({
        "Date": ["2026-10-10"] * 7,
        "TO Number": ["TO-08171", "TO-08185", "TO-08186", "TO-08170", "TO-08184", "TO-08174", "TO-08177"],
        "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar"],
        "Qty": [1178, 1069, 475, 1260, 637, 687, 691],
        "Reason": [
            "HomeRun picker · TO-08138 · vehicle KA01AB1234",
            "HomeRun picker · TO-08179 · vehicle KA02AN1565",
            "HomeRun picker · TO-08180 · vehicle KA01AB8634",
            "HomeRun picker · TO-08139 · vehicle KA54A0075",
            "HomeRun picker · TO-08181 · vehicle KA01AJ6533",
            "HomeRun picker · TO-08140 · vehicle KA52A0811",
            "HomeRun picker · TO-08141 · vehicle KA514894"
        ]
    })

# --- RECONCILIATION DATA PROCESSING ---
if df_draft is not None and df_sent is not None:

    # Convert numeric columns
    df_draft['Qty'] = pd.to_numeric(df_draft['Qty'], errors='coerce').fillna(0)
    df_sent['Qty'] = pd.to_numeric(df_sent['Qty'], errors='coerce').fillna(0)

    # Clean Date formatting
    if 'Date' in df_draft.columns:
        df_draft['Date'] = pd.to_datetime(df_draft['Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(df_draft['Date'])
    if 'Date' in df_sent.columns:
        df_sent['Date'] = pd.to_datetime(df_sent['Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(df_sent['Date'])

    # 1. Aggregate TO Raised (Draft) per TO and DS
    draft_summary = df_draft.groupby(['DS Name', 'TO Number'], as_index=False).agg(
        Draft_Raised_Qty=('Qty', 'sum')
    ).rename(columns={'TO Number': 'Draft TO Number'})

    # 2. Extract Linked Draft TO Number from Sent Data Reason column if present
    if 'Reason' in df_sent.columns:
        def extract_draft_ref(reason):
            match = re.search(r'TO-\d+', str(reason))
            return match.group(0) if match else None
        df_sent['Draft TO Number'] = df_sent['Reason'].apply(extract_draft_ref)
    else:
        df_sent['Draft TO Number'] = df_sent['TO Number']

    # Aggregate Sent Data
    sent_summary = df_sent.groupby(['DS Name', 'TO Number', 'Draft TO Number'], as_index=False).agg(
        Sent_Qty=('Qty', 'sum')
    ).rename(columns={'TO Number': 'Dispatched TO Number'})

    # 3. Merge Raised vs Sent
    merged_reconciliation = pd.merge(draft_summary, sent_summary, on=['DS Name', 'Draft TO Number'], how='left')
    merged_reconciliation['Dispatched TO Number'] = merged_reconciliation['Dispatched TO Number'].fillna("NOT SENT")
    merged_reconciliation['Sent_Qty'] = merged_reconciliation['Sent_Qty'].fillna(0)

    # Unsent Balance & Fill Rate Calculations
    merged_reconciliation['Unsent Qty'] = merged_reconciliation['Draft_Raised_Qty'] - merged_reconciliation['Sent_Qty']
    merged_reconciliation['TO Fill Rate'] = np.where(
        merged_reconciliation['Draft_Raised_Qty'] > 0,
        (merged_reconciliation['Sent_Qty'] / merged_reconciliation['Draft_Raised_Qty']) * 100,
        0
    )

    # 4. Total Metrics Summary per Dark Store
    ds_totals = merged_reconciliation.groupby('DS Name').agg(
        Total_Draft_Qty=('Draft_Raised_Qty', 'sum'),
        Total_Sent_Qty=('Sent_Qty', 'sum'),
        Total_Unsent_Qty=('Unsent Qty', 'sum')
    ).reset_index()

    ds_totals['DC TO Fill rate'] = np.where(
        ds_totals['Total_Draft_Qty'] > 0,
        (ds_totals['Total_Sent_Qty'] / ds_totals['Total_Draft_Qty']) * 100,
        0
    )

    # Format 1st Row of DS Groups
    merged_reconciliation['Is_First'] = ~merged_reconciliation.duplicated(subset=['DS Name'], keep='first')
    dc_fill_map = dict(zip(ds_totals['DS Name'], ds_totals['DC TO Fill rate']))
    ds_unsent_map = dict(zip(ds_totals['DS Name'], ds_totals['Total_Unsent_Qty']))

    merged_reconciliation['DC TO Fill rate raw'] = merged_reconciliation['DS Name'].map(dc_fill_map)
    merged_reconciliation['DS Unsent Raw'] = merged_reconciliation['DS Name'].map(ds_unsent_map)

    table_df = merged_reconciliation.copy()
    table_df['DC TO Fill rate'] = table_df.apply(lambda r: f"{r['DC TO Fill rate raw']:.0f}%" if r['Is_First'] else "", axis=1)
    table_df['TO Fill Rate Str'] = table_df['TO Fill Rate'].apply(lambda x: f"{x:.0f}%")

    # 5. Top Metric Cards
    tot_draft = ds_totals['Total_Draft_Qty'].sum()
    tot_sent = ds_totals['Total_Sent_Qty'].sum()
    tot_unsent = tot_draft - tot_sent
    overall_fill_rate = (tot_sent / tot_draft) * 100 if tot_draft > 0 else 0

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Draft Raised Qty", f"{int(tot_draft):,}")
    m2.metric("Total Sent Qty", f"{int(tot_sent):,}")
    m3.metric("Total Unsent Qty", f"{int(tot_unsent):,}")
    m4.metric("DC Fill Rate", f"{overall_fill_rate:.1f}%")

    st.markdown("---")

    # Header & Export
    col_h, col_b = st.columns([4, 1])
    with col_h:
        st.subheader("📋 Reconciliation Summary (Draft TO Raised vs TO Sent)")
    with col_b:
        csv_data = table_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV Report", data=csv_data, file_name="dual_input_reconciliation.csv", mime="text/csv", use_container_width=True)

    # Bottom Summary Row
    total_row = pd.DataFrame([{
        "DS Name": "TOTAL",
        "Draft TO Number": "",
        "Draft_Raised_Qty": tot_draft,
        "Dispatched TO Number": "",
        "Sent_Qty": tot_sent,
        "Unsent Qty": tot_unsent,
        "TO Fill Rate Str": f"{overall_fill_rate:.0f}%",
        "DC TO Fill rate": f"{overall_fill_rate:.0f}%"
    }])

    cols_order = ["DS Name", "Draft TO Number", "Draft_Raised_Qty", "Dispatched TO Number", "Sent_Qty", "Unsent Qty", "TO Fill Rate Str", "DC TO Fill rate"]
    final_table = pd.concat([table_df[cols_order], total_row[cols_order]], ignore_index=True)

    st.dataframe(
        final_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Draft_Raised_Qty": st.column_config.NumberColumn("Draft Raised Qty", alignment="right"),
            "Sent_Qty": st.column_config.NumberColumn("Sent Qty", alignment="right"),
            "Unsent Qty": st.column_config.NumberColumn("Unsent Qty", alignment="right"),
            "TO Fill Rate Str": st.column_config.TextColumn("TO Fill Rate", alignment="center"),
            "DC TO Fill rate": st.column_config.TextColumn("DC TO Fill rate", alignment="center"),
        }
    )

else:
    st.info("👈 Please enter or upload both Raised and Sent data in the sidebar to generate the report.")
