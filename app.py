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
        except Exception:
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
        df_sent = pd.DataFrame({
            "Date": ["2026-10-10"] * 8,
            "TO Number": ["TO-08171", "TO-08185", "TO-08186", "TO-08170", "TO-08184", "TO-08174", "TO-08177", "TO-08162"],
            "DS Name": ["DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL", "DS08 Rajajinagar", "DS01 Sarjapur"],
            "Sent Qty": [1178, 1069, 475, 1260, 637, 687, 691, 151],
            "Status": ["Transferred", "Transferred", "Transferred", "Transferred", "Transferred", "Transferred", "In Transit", "Transferred"],
            "Reason": [
                "HomeRun picker · TO-08138 · vehicle KA01AB1234",
                "HomeRun picker · TO-08179 · vehicle KA02AN1565",
                "HomeRun picker · TO-08180 · vehicle KA01AB8634",
                "HomeRun picker · TO-08139 · vehicle KA54A0075",
                "HomeRun picker · TO-08181 · vehicle KA01AJ6533",
                "HomeRun picker · TO-08140 · vehicle KA52A0811",
                "HomeRun picker · TO-08141 · vehicle KA514894",
                "INTERNAL TRANSFER"
            ]
        })

    if df_sent is not None and not df_sent.empty:
        if 'Status' in df_sent.columns:
            sent_filtered = df_sent[df_sent['Status'].astype(str).str.lower().isin(['transferred', 'in transit'])].copy()
            if sent_filtered.empty:
                sent_filtered = df_sent.copy()
        else:
            sent_filtered = df_sent.copy()

        if 'Sent Qty' in sent_filtered.columns:
            sent_filtered['Sent Qty'] = pd.to_numeric(sent_filtered['Sent Qty'], errors='coerce').fillna(0)
        else:
            sent_filtered['Sent Qty'] = 0

        for col in ['TO Number', 'DS Name', 'Reason']:
            if col not in sent_filtered.columns:
                sent_filtered[col] = "N/A"

        grouped_sent = sent_filtered.groupby(['TO Number', 'DS Name', 'Reason'], as_index=False).agg(
            Sent_Qty=('Sent Qty', 'sum')
        )

        total_sent_units = grouped_sent['Sent_Qty'].sum()
        total_unique_tos = grouped_sent['TO Number'].nunique()
        total_unique_ds = grouped_sent['DS Name'].nunique()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Sent Units", f"{int(total_sent_units):,}")
        m2.metric("Total Dispatched TOs", f"{total_unique_tos:,}")
        m3.metric("Total Dark Stores", f"{total_unique_ds:,}")

        st.markdown("---")

        total_row = pd.DataFrame([{
            "TO Number": "TOTAL",
            "DS Name": "",
            "Reason": "GRAND TOTAL",
            "Sent_Qty": total_sent_units
        }])

        final_sent_table = pd.concat([grouped_sent, total_row], ignore_index=True)

        col_h, col_b = st.columns([4, 1])
        with col_h:
            st.subheader("📋 Sent Quantity by TO Number & Reason")
        with col_b:
            csv_data = final_sent_table.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export CSV", data=csv_data, file_name="sent_qty_by_to_and_reason.csv", mime="text/csv", use_container_width=True)

        st.dataframe(
            final_sent_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "TO Number": st.column_config.TextColumn("TO Number", width="medium"),
                "DS Name": st.column_config.TextColumn("Dark Store", width="medium"),
                "Reason": st.column_config.TextColumn("Reason / Vehicle Details", width="large"),
                "Sent_Qty": st.column_config.NumberColumn("Sent Qty", alignment="right", format="%d"),
            }
        )

# ==============================================================================
# MODE 2: DUAL UPLOAD (RAISED VS SENT RECONCILIATION)
# ==============================================================================
elif app_mode == "📁 2. Dual Upload (Raised vs Sent Reconciliation)":
    st.subheader("📁 Dual Input Reconciliation (Raised vs Sent)")
    
    col_file1, col_file2 = st.columns(2)
    df_draft = None
    df_sent = None

    with col_file1:
        file_draft = st.file_uploader("1. Upload TO Raised (Draft) File", type=["csv", "xlsx"])
        if file_draft:
            df_draft = load_file(file_draft)

    with col_file2:
        file_sent = st.file_uploader("2. Upload TO Sent (Dispatched) File", type=["csv", "xlsx"])
        if file_sent:
            df_sent = load_file(file_sent)

    if df_draft is not None and df_sent is not None:
        df_draft['Sent Qty'] = pd.to_numeric(df_draft['Sent Qty'], errors='coerce').fillna(0)
        df_sent['Sent Qty'] = pd.to_numeric(df_sent['Sent Qty'], errors='coerce').fillna(0)

        draft_summary = df_draft.groupby(['DS Name', 'TO Number'], as_index=False).agg(
            Draft_Raised_Qty=('Sent Qty', 'sum')
        ).rename(columns={'TO Number': 'Draft TO Number'})

        if 'Reason' in df_sent.columns:
            def extract_draft_ref(reason):
                match = re.search(r'TO-\d+', str(reason))
                return match.group(0) if match else None
            df_sent['Draft TO Number'] = df_sent['Reason'].apply(extract_draft_ref)
        else:
            df_sent['Draft TO Number'] = df_sent['TO Number']

        sent_summary = df_sent.groupby(['DS Name', 'TO Number', 'Draft TO Number'], as_index=False).agg(
            Sent_Qty=('Sent Qty', 'sum')
        ).rename(columns={'TO Number': 'Dispatched TO Number'})

        merged = pd.merge(draft_summary, sent_summary, on=['DS Name', 'Draft TO Number'], how='left').fillna({
            'Dispatched TO Number': 'NOT SENT',
            'Sent_Qty': 0
        })

        merged['Unsent Qty'] = merged['Draft_Raised_Qty'] - merged['Sent_Qty']
        merged['Fill Rate (%)'] = np.where(merged['Draft_Raised_Qty'] > 0, (merged['Sent_Qty'] / merged['Draft_Raised_Qty']) * 100, 0)

        st.markdown("---")
        st.dataframe(merged, use_container_width=True, hide_index=True)

# ==============================================================================
# MODE 3: COPY-PASTE RAW DATA
# ==============================================================================
else:
    st.subheader("📋 Copy-Paste Raw Data Below")
    paste_text = st.text_area("Paste Raw Data (Tab-Separated from Excel)", height=200)
    
    if paste_text.strip():
        df_pasted = parse_pasted_data(paste_text)
        if df_pasted is not None:
            st.dataframe(df_pasted, use_container_width=True, hide_index=True)
