import streamlit as st
import pandas as pd
import numpy as np
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

                # Determine PR Number and Receive Date columns safely
                pr_no_col = 'Receive Number' if 'Receive Number' in df_pr.columns else 'PR Number'
                date_col = 'Receive Date' if 'Receive Date' in df_pr.columns else 'PR Date'

                # Ensure Quantity Received is strictly numeric
                df_pr['Quantity Received'] = pd.to_numeric(df_pr['Quantity Received'], errors='coerce').fillna(0)

                # Clean PR Data
                df_pr_clean = df_pr.dropna(subset=['PO Number']).copy()
                df_pr_clean['DT'] = pd.to_datetime(df_pr_clean[date_col], errors='coerce')
                
                # Filter for PR entries created in the last 15 hours
                max_time = df_pr_clean['DT'].max()
                if pd.notna(max_time):
                    cutoff_time = max_time - pd.Timedelta(hours=15)
                    df_today = df_pr_clean[df_pr_clean['DT'] >= cutoff_time]
                    df_prior = df_pr_clean[df_pr_clean['DT'] < cutoff_time]
                else:
                    df_today = df_pr_clean
                    df_prior = pd.DataFrame(columns=df_pr_clean.columns)

                # Aggregate Today's PR Data
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
                df_po_clean['QuantityOrdered'] = pd.to_numeric(df_po_clean['QuantityOrdered'], errors='coerce').fillna(0)
                
                po_summary = df_po_clean.groupby('Purchase Order Number').agg(
                    PO_Qty=('QuantityOrdered', 'sum'),
                    Vendor_PO=('Vendor Name', 'first')
                ).reset_index()

                # Merge Today's PRs with PO and Prior MTD Data
                merged = pd.merge(today_summary, po_summary, left_on='PO Number', right_on='Purchase Order Number', how='left')
                merged = pd.merge(merged, prior_summary, on='PO Number', how='left')

                # Format Date safely
                merged['Date'] = merged['PR_Date'].dt.strftime('%d-%m-%y').fillna('')
                
                # Fill missing text values
                merged['Vendor Name'] = merged['Vendor_PR'].fillna(merged['Vendor_PO']).fillna('')
                
                # Ensure all quantities are clean integers
                merged['PO Qty'] = pd.to_numeric(merged['PO_Qty'], errors='coerce').fillna(0).astype(int)
                merged['PR Qty'] = pd.to_numeric(merged['PR_Qty'], errors='coerce').fillna(0).astype(int)
                merged['PRMTD'] = pd.to_numeric(merged['PRMTD'], errors='coerce').fillna(0).astype(int)
                
                # Total Received Qty = Today's PR Qty + Previous PR Qty
                merged['Total Received'] = merged['PR Qty'] + merged['PRMTD']
                
                # Separate Excess and Short based on Total Received vs PO Qty
                merged['Diff'] = merged['Total Received'] - merged['PO Qty']
                merged['Excess'] = merged['Diff'].apply(lambda x: x if x > 0 else 0).astype(int)
                merged['Short'] = merged['Diff'].apply(lambda x: abs(x) if x < 0 else 0).astype(int)
                merged['Sl.no'] = range(1, len(merged) + 1)

                # Overall Totals
                total_po = int(merged['PO Qty'].sum())
                total_pr = int(merged['PR Qty'].sum())
                total_prmtd = int(merged['PRMTD'].sum())
                total_excess = int(merged['Excess'].sum())
                total_short = int(merged['Short'].sum())
                total_fr_val = ((total_pr + total_prmtd) / total_po * 100) if total_po > 0 else 0

                # Formatted headers
                expected_headers = ["Sl.no", "Date", "PO Number", "PR_no", "Vendor Name", "PO Qty", "PR Qty", "PRMTD", "Excess", "Short"]
                final_df = merged[expected_headers].rename(columns={'PO Number': 'PO No', 'PR_no': 'PR No'})
                
                # Safe PO FR % Calculation
                fr_numeric = np.where(final_df['PO Qty'] > 0, ((final_df['PR Qty'] + final_df['PRMTD']) / final_df['PO Qty']) * 100, 0)
                final_df['PO FR %'] = np.round(fr_numeric).astype(int).astype(str) + '%'

                # Build Total row separately without forcing datatype conversions on final_df
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
                    "PO FR %": f"{int(round(total_fr_val))}%"
                }])

                # Concatenate as string objects to prevent pandas type conversion crashes
                display_df = pd.concat([final_df, total_row], ignore_index=True)

                # Cache in Session State
                st.session_state["processed_df"] = display_df

        except Exception as e:
            st.error(f"Error processing files: {e}")

# Render Excel Worksheet
if "processed_df" in st.session_state:
    display_df = st.session_state["processed_df"]

    # Safe cell styling loop that handles mixed string/numeric values
    def highlight_excel_cells(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        
        for idx, row in df.iterrows():
            if str(row['Vendor Name']) == 'Total':
                styles.loc[idx, :] = 'background-color: #f4b084; font-weight: bold; color: black; border-top: 2px solid black; border-bottom: 2px double black'
            else:
                # Safe Excess conversion
                try:
                    excess_val = float(row['Excess'])
                    if excess_val > 0:
                        styles.loc[idx, 'Excess'] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                except (ValueError, TypeError):
                    pass

                # Safe Short conversion
                try:
                    short_val = float(row['Short'])
                    if short_val > 0:
                        styles.loc[idx, 'Short'] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                except (ValueError, TypeError):
                    pass
                    
        return styles

    styled_df = display_df.style.apply(highlight_excel_cells, axis=None)

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
    excel_bytes = generate_excel_file(display_df)
    st.download_button(
        label="📥 Download Summary as Excel (.xlsx)",
        data=excel_bytes,
        file_name="PO_PR_Summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
