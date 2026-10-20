import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="DS Sent Qty Summary", layout="wide")

# Excel Classic Light Yellow (#FFF2CC) Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* Excel Header & Grid Styling */
    .excel-table {
        border-collapse: collapse;
        width: 100%;
        font-family: Arial, sans-serif;
        font-size: 14px;
        color: #000000;
        margin-top: 10px;
    }
    .excel-table th {
        background-color: #FFF2CC !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #000000;
        text-align: center;
        padding: 8px 12px;
    }
    .excel-table td {
        border: 1px solid #000000;
        padding: 6px 12px;
        color: #000000;
    }
    .excel-table tr:hover {
        background-color: #F9FAFB;
    }
    .total-row {
        background-color: #FFE699;
        font-weight: bold;
    }
    
    /* Streamlit Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        color: #856404;
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #000000;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFF2CC;
        border-right: 1px solid #D6D8DB;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Dispatched Quantity Summary (DS Wise)")

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

    # Total quantity
    total_qty = result_df['qty'].sum()

    # Metrics Display
    m1, m2 = st.columns(2)
    m1.metric("Total Dispatched Quantity", f"{int(total_qty):,}")
    m2.metric("Total Transfer Orders", f"{len(result_df):,}")

    st.markdown("---")

    # Action Buttons
    col_h, col_b1, col_b2 = st.columns([3, 1, 1])
    with col_h:
        st.subheader("📋 Dispatched Quantity Table")
    with col_b1:
        csv_data = result_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv_data, file_name="sent_qty_summary.csv", mime="text/csv", use_container_width=True)
    with col_b2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, sheet_name="Sent_Summary", index=False)
        st.download_button("📥 Download Excel", data=buffer.getvalue(), file_name="sent_qty_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # HTML Table Rendering for Perfect Yellow Header & Grid Theme
    html_rows = ""
    for idx, row in result_df.iterrows():
        html_rows += f"""
        <tr>
            <td style="text-align: center;">{row['date']}</td>
            <td style="text-align: left; font-weight: bold;">{row['DS']}</td>
            <td style="text-align: center;">{row['TO']}</td>
            <td style="text-align: left;">{row['reson']}</td>
            <td style="text-align: right; font-weight: 500;">{int(row['qty']):,}</td>
        </tr>
        """
    
    # Add Total Row
    html_rows += f"""
    <tr class="total-row">
        <td style="text-align: center;">Total</td>
        <td></td>
        <td></td>
        <td style="text-align: left;">Total Dispatched Qty</td>
        <td style="text-align: right;">{int(total_qty):,}</td>
    </tr>
    """

    full_table_html = f"""
    <table class="excel-table">
        <thead>
            <tr>
                <th style="width: 12%;">date</th>
                <th style="width: 20%;">DS</th>
                <th style="width: 18%;">TO</th>
                <th style="width: 35%;">reson</th>
                <th style="width: 15%;">qty</th>
            </tr>
        </thead>
        <tbody>
            {html_rows}
        </tbody>
    </table>
    """

    st.markdown(full_table_html, unsafe_allow_html=True)

else:
    st.info("👈 Please upload your Transfer Order file in the sidebar.")
