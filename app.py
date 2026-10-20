import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import textwrap
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="DS Transfer Summary", layout="wide")

# Custom CSS Theme
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 14px;
        color: #000000;
        margin-top: 15px;
        background-color: #FFFFFF;
    }
    .custom-table th {
        background-color: #EAEAEA !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #D1D5DB;
        text-align: center;
        padding: 10px;
    }
    .custom-table td {
        border: 1px solid #E5E7EB;
        padding: 8px 12px;
        color: #000000;
    }
    .custom-table tr:nth-child(even) td {
        background-color: #F9FAFB;
    }
    .custom-table tr:nth-child(odd) td {
        background-color: #FFFFFF;
    }
    .custom-table tr.total-row td {
        background-color: #F8B486 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-top: 2px solid #D97706;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 30px;
        color: #F8B486;
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #E5E7EB;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] {
        background-color: #1F2937;
        color: #FFFFFF;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Dispatched Quantity Summary (DS Wise)")

uploaded_file = st.sidebar.file_uploader("Upload Transfer Order File", type=["csv", "xlsx"])
use_demo = st.sidebar.checkbox("Use Demo Data", value=(uploaded_file is None))

def classify_row_reason(reason_str, item_name_str=""):
    reason_str = str(reason_str).strip()
    item_name_str = str(item_name_str).strip()
    combined_text = f"{reason_str} {item_name_str}".lower()
    
    # 1. Match 'HomeRun picker · TO-XXXXX · vehicle YYYYY'
    picker_match = re.search(r'HomeRun picker\s*·\s*(TO-\d+)', reason_str, re.IGNORECASE)
    if picker_match:
        to_num = picker_match.group(1).upper()
        return f"picked by picker - {to_num}"
    
    # 2. Check for cement / bags / putty / mortar / plaster
    if re.search(r'cement|bag|putty|mortar|plaster|p-sand|m-sand', combined_text, re.IGNORECASE):
        return "BAG"
    
    # 3. Check for ply / internal transfer
    if re.search(r'ply|plywood|internal transfer', combined_text, re.IGNORECASE):
        return "PLY"
        
    return reason_str if reason_str else "PLY"

def generate_styled_excel(df, grand_total):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sent_Summary"

    headers = ["date", "DS", "TO", "reson", "qty"]
    ws.append(headers)

    for row in df.itertuples(index=False):
        ws.append([row.date, row.DS, row.TO, row.reson, row.qty])

    # Grand Total Row
    ws.append(["Total", "", "", "Total Dispatched Qty", grand_total])

    font_header = Font(name="Arial", size=11, bold=True, color="000000")
    font_body = Font(name="Arial", size=10, color="000000")
    font_total = Font(name="Arial", size=11, bold=True, color="000000")

    fill_header = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
    fill_even = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    fill_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_total = PatternFill(start_color="F8B486", end_color="F8B486", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    for col_num in range(1, 6):
        cell = ws.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    max_row = ws.max_row
    for row_num in range(2, max_row):
        fill = fill_even if row_num % 2 == 0 else fill_odd

        for col_num in range(1, 6):
            cell = ws.cell(row=row_num, column=col_num)
            cell.font = font_body
            cell.fill = fill
            cell.border = thin_border
            if col_num in [1, 3]:
                cell.alignment = Alignment(horizontal="center")
            elif col_num == 5:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = '#,##0'
            else:
                cell.alignment = Alignment(horizontal="left")

    for col_num in range(1, 6):
        cell = ws.cell(row=max_row, column=col_num)
        cell.font = font_total
        cell.fill = fill_total
        cell.border = thin_border
        if col_num == 5:
            cell.alignment = Alignment(horizontal="right")
            cell.number_format = '#,##0'
        elif col_num in [1, 4]:
            cell.alignment = Alignment(horizontal="left")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

df = None

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
elif use_demo:
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
        ],
        "Item Name": [
            "Asian Paints TruCare Wall Putty, 40 Kg Bag",
            "Hettich Hinges",
            "Hettich Hinges",
            "Hettich Hinges",
            "Hettich Hinges",
            "Hettich Hinges",
            "Hettich Hinges"
        ]
    })

if df is not None:
    df.columns = df.columns.astype(str).str.strip()

    dc_df = df[df['From Location Name'].astype(str).str.contains('DC', na=False) & df['To Location Name'].astype(str).str.contains('DS', na=False)].copy()
    sent_df = dc_df[dc_df['Status'].astype(str).str.lower().isin(['transferred', 'in transit'])].copy()

    if 'Item Name' not in sent_df.columns:
        sent_df['Item Name'] = ""

    sent_df['clean_reason'] = sent_df.apply(lambda r: classify_row_reason(r['Reason'], r['Item Name']), axis=1)

    grouped = sent_df.groupby(['Date', 'To Location Name', 'Transfer Order#', 'clean_reason'], as_index=False).agg(
        Qty=('Quantity Transferred', 'sum')
    )

    grouped['date'] = pd.to_datetime(grouped['Date'], errors='coerce').dt.strftime('%d-%b')
    grouped.sort_values(by=['To Location Name', 'Transfer Order#'], inplace=True)

    # Visual Grouping (Blank duplicate Date & DS names)
    grouped['Is_First_DS'] = ~grouped.duplicated(subset=['To Location Name'], keep='first')

    grouped['display_date'] = grouped.apply(lambda r: r['date'] if r['Is_First_DS'] else "", axis=1)
    grouped['display_ds'] = grouped.apply(lambda r: r['To Location Name'] if r['Is_First_DS'] else "", axis=1)

    result_df = grouped[['display_date', 'display_ds', 'Transfer Order#', 'clean_reason', 'Qty']].copy()
    result_df.columns = ['date', 'DS', 'TO', 'reson', 'qty']

    grand_total_qty = result_df['qty'].sum()
    total_to_count = len(result_df)

    m1, m2 = st.columns(2)
    m1.metric("Total Dispatched Quantity", f"{int(grand_total_qty):,}")
    m2.metric("Total Transfer Orders", f"{total_to_count:,}")

    st.markdown("---")

    col_h, col_b1, col_b2 = st.columns([3, 1, 1])
    with col_h:
        st.subheader("📋 Dispatched Quantity Table")
    with col_b1:
        csv_data = result_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv_data, file_name="sent_qty_summary.csv", mime="text/csv", use_container_width=True)
    with col_b2:
        excel_bytes = generate_styled_excel(result_df, grand_total_qty)
        st.download_button("📥 Download Excel", data=excel_bytes, file_name="sent_qty_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    html_rows = ""
    for idx, row in result_df.iterrows():
        html_rows += f"<tr><td style='text-align: center;'>{row['date']}</td><td style='text-align: left; font-weight: bold;'>{row['DS']}</td><td style='text-align: center;'>{row['TO']}</td><td style='text-align: left;'>{row['reson']}</td><td style='text-align: right;'>{int(row['qty']):,}</td></tr>"

    html_rows += f"<tr class='total-row'><td style='text-align: left;'>Total</td><td></td><td></td><td style='text-align: left;'>Total Dispatched Qty</td><td style='text-align: right;'>{int(grand_total_qty):,}</td></tr>"

    raw_html = f"""<table class="custom-table"><thead><tr><th style="width: 12%;">date</th><th style="width: 20%;">DS</th><th style="width: 18%;">TO</th><th style="width: 35%;">reson</th><th style="width: 15%;">qty</th></tr></thead><tbody>{html_rows}</tbody></table>"""

    st.markdown(textwrap.dedent(raw_html), unsafe_allow_html=True)

else:
    st.info("👈 Please upload your Transfer Order file in the sidebar.")
