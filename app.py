import streamlit as st
import pandas as pd
import io

# Page config - Standard Excel Wide Layout
st.set_page_config(page_title="PO vs PR Summary", page_icon="📊", layout="wide")

# Excel Grid Styling (Light Theme, Borders, Compact Padding, Wide Layout)
st.markdown("""
    <style>
        /* Hide default Streamlit headers, footers, and menu bars */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stHeader"] {display: none;}
        
        /* Force White Background and Excel Aesthetics */
        .main {
            background-color: #ffffff !important;
        }

        .stTable {
            background-color: #ffffff !important;
            font-family: "Segoe UI", Arial, sans-serif !important;
            font-size: 13px !important;
            color: #000000 !important;
        }
        
        .stTable table {
            border-collapse: collapse !important;
            width: 100% !important;
            border: 1px solid #d9d9d9 !important;
        }
        
        /* Excel Table Headers */
        .stTable th {
            background-color: #e6e6e6 !important;
            color: #000000 !important;
            font-weight: bold !important;
            text-align: center !important;
            border: 1px solid #bfbfbf !important;
            padding: 6px 10px !important;
            white-space: nowrap !important;
        }
        
        /* Excel Data Cells & Gridlines */
        .stTable td {
            border: 1px solid #d9d9d9 !important;
            padding: 6px 10px !important;
            color: #000000 !important;
            white-space: nowrap !important;
        }
        
        /* Zebra Striping (Light Excel rows) */
        .stTable tr:nth-child(even) {
            background-color: #f9f9f9 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 PO vs PR Excel View")

# Toggle panel to hide uploaders
show_uploaders = st.toggle("🎚️ Show Upload Panel", value=True)

if show_uploaders:
    col1, col2 = st.columns(2)
    with col1:
        po_file = st.file_uploader("Upload PO Data (Excel)", type=['xlsx', 'xls'])
    with col2:
        pr_file = st.file_uploader("Upload PR Data (Excel)", type=['xlsx', 'xls'])
        
    if po_file and pr_file:
        try:
            with st.spinner("Processing files..."):
                # Load raw data
                df_po = pd.read_excel(po_file)
                df_pr = pd.read_excel(pr_file)

                # Clean column names
                df_po.columns = df_po.columns.str.strip()
                df_pr.columns = df_pr.columns.str.strip()

                # Determine PR Number and Receive Date columns
                pr_no_col = 'Receive Number' if 'Receive Number' in df_pr.columns else 'PR Number'
                date_col = 'Receive Date' if 'Receive Date' in df_pr.columns else 'PR Date'

                # Clean PR Data
                df_pr_clean = df_pr.dropna(subset=['PO Number']).copy()
                df_pr_clean['DT'] = pd.to_datetime(df_pr_clean[date_col], errors='coerce')
                
                # Dynamic cut-off: Filter for PR entries created in the last 15 hours
                max_time = df_pr_clean['DT'].max()
                cutoff_time = max_time - pd.Timedelta(hours=15)

                # Split PRs into Today (Last 15 Hours) vs Prior (MTD Previous)
                df_today = df_pr_clean[df_pr_clean['DT'] >= cutoff_time]
                df_prior = df_pr_clean[df_pr_clean['DT'] < cutoff_time]

                # Aggregate Today's PR Data (Only POs active in last 15 hours)
                today_summary = df_today.groupby('PO Number').agg(
                    PR_no=(pr_no_col, lambda x: " & ".join(sorted(x.dropna().astype(str).unique()))),
                    PR_Qty=('Quantity Received', 'sum'),
                    PR_Date=('DT', 'max'),
                    Vendor_PR=('Vendor Name', 'first')
                ).reset_index()

                # Aggregate Prior MTD PR Qty per PO Number
                prior_summary = df_prior.groupby('PO Number').agg(
                    PRMTD=('Quantity Received', 'sum')
                ).reset_index()

                # Process PO Data
                df_po_clean = df_po.dropna(subset=['Purchase Order Number']).copy()
                po_summary = df_po_clean.groupby('Purchase Order Number').agg(
                    PO_Qty=('QuantityOrdered', 'sum'),
                    Vendor_PO=('Vendor Name', 'first')
                ).reset_index()

                # Merge Today's PRs with PO and Prior MTD Data
                merged = pd.merge(today_summary, po_summary, left_on='PO Number', right_on='Purchase Order Number', how='left')
                merged = pd.merge(merged, prior_summary, on='PO Number', how='left')

                # Format Date
                merged['Date'] = merged['PR_Date'].dt.strftime('%d-%m-%y')
                
                # Clean and calculate values
                merged['Vendor Name'] = merged['Vendor_PR'].fillna(merged['Vendor_PO'])
                merged['PO Qty'] = merged['PO_Qty'].fillna(0).astype(int)
                merged['PR Qty'] = merged['PR_Qty'].fillna(0).astype(int)
                merged['PRMTD'] = merged['PRMTD'].fillna(0).astype(int)
                
                # Total Received Qty = Today's PR Qty + Previous PR Qty
                merged['Total Received'] = merged['PR Qty'] + merged['PRMTD']
                
                # Separate Excess and Short based on Total Received vs PO Qty
                merged['Diff'] = merged['Total Received'] - merged['PO Qty']
                merged['Excess'] = merged['Diff'].apply(lambda x: x if x > 0 else 0)
                merged['Short'] = merged['Diff'].apply(lambda x: abs(x) if x < 0 else 0)
                merged['Sl.no'] = range(1, len(merged) + 1)

                # Overall Totals
                total_po = merged['PO Qty'].sum()
                total_pr = merged['PR Qty'].sum()
                total_prmtd = merged['PRMTD'].sum()
                total_excess = merged['Excess'].sum()
                total_short = merged['Short'].sum()
                total_fr = ((total_pr + total_prmtd) / total_po * 100) if total_po > 0 else 0

                # Formatted headers
                expected_headers = ["Sl.no", "Date", "PO Number", "PR_no", "Vendor Name", "PO Qty", "PR Qty", "PRMTD", "Excess", "Short"]
                final_df = merged[expected_headers].rename(columns={'PO Number': 'PO No', 'PR_no': 'PR No'})
                
                # Fill Rate calculated against total receipts (PR Qty + PRMTD)
                final_df['PO FR %'] = (((merged['PR Qty'] + merged['PRMTD']) / merged['PO Qty']).fillna(0) * 100).round(0).astype(int).astype(str) + '%'

                # Excel Total Row
                total_row = pd.DataFrame([{
                    "Sl.no": "",
                    "Date": "",
                    "PO No": "",
                    "PR No": "",
                    "Vendor Name": "Total",
                    "PO Qty": total_po,
                    "PR Qty": total_pr,
                    "PRMTD": total_prmtd,
                    "Excess": total_excess,
                    "Short": total_short,
                    "PO FR %": f"{int(round(total_fr))}%"
                }])

                # Append Total Row
                final_df = pd.concat([final_df, total_row], ignore_index=True)

                # Cache in Session State
                st.session_state["processed_df"] = final_df

        except Exception as e:
            st.error(f"Error processing files: {e}")

# Render Excel Worksheet
if "processed_df" in st.session_state:
    final_df = st.session_state["processed_df"]

    # Excel-style Highlight for Total Row and Conditional Coloring for Excess / Short
    def apply_excel_styles(row):
        styles = [''] * len(row)
        if row['Vendor Name'] == 'Total':
            return ['background-color: #f4b084; font-weight: bold; color: black; border-top: 2px solid black; border-bottom: 2px double black'] * len(row)
        
        # Excess column highlight (Light Green)
        if row['Excess'] > 0:
            excess_idx = final_df.columns.get_loc('Excess')
            styles[excess_idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
            
        # Short column highlight (Light Red)
        if row['Short'] > 0:
            short_idx = final_df.columns.get_loc('Short')
            styles[short_idx] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            
        return styles

    styled_df = final_df.style.apply(apply_excel_styles, axis=1)

    # Render as native HTML Excel Table
    st.table(styled_df)

    # --- EXCEL DOWNLOAD GENERATOR ---
    def generate_excel_file(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='PO vs PR Summary')
        return output.getvalue()

    # Excel File Download Button at bottom
    st.markdown("---")
    excel_bytes = generate_excel_file(final_df)
    st.download_button(
        label="📥 Download Summary as Excel (.xlsx)",
        data=excel_bytes,
        file_name="PO_PR_Summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
