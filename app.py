import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="DS Sent Qty Reconciliation", layout="wide")

# Custom CSS for Industrial Dashboard Theme
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #FACA15;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Sent Quantity Summary (DS Wise)")

uploaded_file = st.sidebar.file_uploader("Upload Transfer Order File", type=["csv", "xlsx"])
use_demo = st.sidebar.checkbox("Use Demo Data", value=(uploaded_file is None))

def transform_reason(reason_str):
    reason_str = str(reason_str).strip()
    
    # 1. Match 'HomeRun picker · TO-XXXXX · vehicle YYYYY'
    picker_match = re.search(r'HomeRun picker\s*·\s*(TO-\d+)', reason_str, re.IGNORECASE)
    if picker_match:
        to_num = picker_match.group(1).upper()
        return f"picked by picker - {to_num}"
    
    # 2. Check for cement
    if re.search(r'cement', reason_str, re.IGNORECASE):
        return "BAG"
    
    # 3. Check for ply / internal transfer
    if re.search(r'ply|plywood|internal transfer', reason_str, re.IGNORECASE):
        return "PLY"
        
    return reason_str

df = None

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
elif use_demo:
    # Sample dataset
    df = pd.DataFrame({
        "Date": ["2026-10-10"] * 7,
        "From Location Name": ["DC01 Rampura"] * 7,
        "To Location Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS05 Basavanapura", "DS06 Kogilu", "DS07 HAL"],
        "Transfer Order#": ["TO-08162", "TO-08171", "TO-08185", "TO-08186", "TO-08170", "TO-08184", "TO-08174"],
        "Status": ["Transferred"] * 7,
        "Quantity Transferred": [151, 1178, 1069, 475, 1260, 637, 687],
        "Reason": [
            "INTERNAL TRANSFER",
            "HomeRun picker · TO-08138 · vehicle KA01AB1234",
            "HomeRun picker · TO-08179 · vehicle KA02AN1565",
            "HomeRun picker · TO-08180 · vehicle KA01AB8634",
            "HomeRun picker · TO-08139 · vehicle KA54A0075",
            "HomeRun picker · TO-08181 · vehicle KA01AJ6533",
            "HomeRun picker · TO-08140 · vehicle KA52A0811"
        ]
    })

if df is not None:
    df.columns = df.columns.astype(str).str.strip()

    # Filter DC to DS transfers
    dc_df = df[df['From Location Name'].astype(str).str.contains('DC', na=False) & df['To Location Name'].astype(str).str.contains('DS', na=False)].copy()

    # Filter dispatches
    sent_df = dc_df[dc_df['Status'].astype(str).str.lower().isin(['transferred', 'in transit'])].copy()

    # Apply Reason Rules
    sent_df['clean_reason'] = sent_df['Reason'].apply(transform_reason)

    # Group by Date, DS, TO Number, Reason
    grouped = sent_df.groupby(['Date', 'To Location Name', 'Transfer Order#', 'clean_reason'], as_index=False).agg(
        Qty=('Quantity Transferred', 'sum')
    )

    # Format Date (DD-Mon)
    grouped['date'] = pd.to_datetime(grouped['Date'], errors='coerce').dt.strftime('%d-%b')
    grouped.sort_values(by=['To Location Name', 'Transfer Order#'], inplace=True)

    # Blank out duplicate Date and DS for clean grouped view
    grouped['Is_First_DS'] = ~grouped.duplicated(subset=['To Location Name'], keep='first')

    grouped['display_date'] = grouped.apply(lambda r: r['date'] if r['Is_First_DS'] else "", axis=1)
    grouped['display_ds'] = grouped.apply(lambda r: r['To Location Name'] if r['Is_First_DS'] else "", axis=1)

    result_df = grouped[['display_date', 'display_ds', 'Transfer Order#', 'clean_reason', 'Qty']].copy()
    result_df.columns = ['date', 'DS', 'TO', 'reson', 'qty']

    # Total row
    total_qty = result_df['qty'].sum()
    total_row = pd.DataFrame([{
        "date": "Total",
        "DS": "",
        "TO": "",
        "reson": "Total Dispatched",
        "qty": total_qty
    }])

    final_table = pd.concat([result_df, total_row], ignore_index=True)

    # Metrics Display
    m1, m2 = st.columns(2)
    m1.metric("Total Dispatched Quantity", f"{int(total_qty):,}")
    m2.metric("Total Transfer Orders", f"{len(result_df):,}")

    st.markdown("---")

    col_h, col_b1, col_b2 = st.columns([3, 1, 1])
    with col_h:
        st.subheader("📋 Dispatched Quantity Breakdown")
    with col_b1:
        csv_data = final_table.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", data=csv_data, file_name="sent_qty_summary.csv", mime="text/csv", use_container_width=True)
    with col_b2:
        # Excel Download Option
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_table.to_excel(writer, sheet_name="Sent_Summary", index=False)
        st.download_button("📥 Export Excel", data=buffer.getvalue(), file_name="sent_qty_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # Render Table
    st.dataframe(
        final_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.TextColumn("date", width="small"),
            "DS": st.column_config.TextColumn("DS", width="medium"),
            "TO": st.column_config.TextColumn("TO", width="medium"),
            "reson": st.column_config.TextColumn("reson", width="large"),
            "qty": st.column_config.NumberColumn("qty", alignment="right", format="%d")
        }
    )
else:
    st.info("👈 Please upload your Transfer Order file in the sidebar.")
