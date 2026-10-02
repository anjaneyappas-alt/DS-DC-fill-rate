import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Transfer Reconciliation Dashboard", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")
st.caption("Upload a single multi-sheet Excel file or raw copy-paste data to generate full transfer reconciliation reports.")

# --- SIDEBAR CONTROL ---
st.sidebar.header("📥 Data Input Options")
input_method = st.sidebar.radio("Choose Input Method:", ["📁 Upload Excel Workbook", "📋 Copy-Paste Raw Data"])

df_dict = {}

def standardize_columns(df):
    if df is None or df.empty:
        return df

    df.columns = df.columns.astype(str).str.strip()

    column_mapping = {
        'DS Name': 'DS Name', 'To Location Name': 'DS Name', 'To Location': 'DS Name',
        'Quantity Transferred': 'Dispatched Qty', 'Dispatched Qty': 'Dispatched Qty', 
        'Sent Qty': 'Dispatched Qty', 'Quantity': 'Dispatched Qty',
        'Transfer Order#': 'TO Number', 'Transfer Order': 'TO Number', 'TO Number': 'TO Number',
        'TO Qty': 'TO Qty', 'Required Qty': 'TO Qty', 'Quantity Required': 'TO Qty',
        'Qty Received (as per DS)': 'Qty Received', 'Qty Received': 'Qty Received'
    }

    new_cols = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        for key, val in column_mapping.items():
            if col_lower == key.lower():
                new_cols[col] = val
                break
            
    return df.rename(columns=new_cols)

# --- INPUT HANDLING ---
if input_method == "📁 Upload Excel Workbook":
    uploaded_file = st.sidebar.file_uploader("Upload Excel File (.xlsx)", type=["xlsx", "xls", "csv"])

    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df_single = pd.read_csv(uploaded_file)
            df_dict["Main Data"] = standardize_columns(df_single)
        else:
            excel_file = pd.ExcelFile(uploaded_file)
            for sheet_name in excel_file.sheet_names:
                df_sheet = pd.read_excel(excel_file, sheet_name=sheet_name)
                df_dict[sheet_name] = standardize_columns(df_sheet)

elif input_method == "📋 Copy-Paste Raw Data":
    paste_data = st.text_area("Paste Raw Data Below (Tab-Separated from Excel)", height=200)
    if paste_data.strip():
        try:
            try:
                df_paste = pd.read_csv(io.StringIO(paste_data), sep="\t")
                if len(df_paste.columns) <= 1:
                    df_paste = pd.read_csv(io.StringIO(paste_data), sep=",")
            except:
                df_paste = pd.read_csv(io.StringIO(paste_data), sep=",")
            df_dict["Pasted Data"] = standardize_columns(df_paste)
        except Exception as e:
            st.error(f"Error reading pasted data: {e}")

# --- DASHBOARD RENDERING ---
if df_dict:
    # Navigation tabs for multiple sheets
    selected_sheet = st.sidebar.selectbox("📖 Select Sheet View:", options=list(df_dict.keys()))

    df_current = df_dict[selected_sheet].copy()

    st.subheader(f"📊 View: {selected_sheet}")

    # Check if the selected sheet is a Review / Summary sheet
    if any(k in selected_sheet.lower() for k in ["review", "summary", "main"]):
        
        # Display Metric Cards if standard columns exist
        if 'Dispatched Qty' in df_current.columns and 'TO Qty' in df_current.columns:
            tot_to_qty = pd.to_numeric(df_current['TO Qty'], errors='coerce').sum()
            tot_dispatch = pd.to_numeric(df_current['Dispatched Qty'], errors='coerce').sum()
            tot_unsent = tot_to_qty - tot_dispatch
            overall_fill_rate = (tot_dispatch / tot_to_qty) * 100 if tot_to_qty > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total TO Requested", f"{int(tot_to_qty):,}")
            m2.metric("Total Dispatched", f"{int(tot_dispatch):,}")
            m3.metric("Total Unsent Qty", f"{int(tot_unsent):,}")
            m4.metric("DC Fill Rate", f"{overall_fill_rate:.1f}%")

            st.markdown("---")

    # Clean display dataframe
    st.dataframe(
        df_current.dropna(how='all'),
        use_container_width=True,
        hide_index=True
    )

    # Export Option
    csv_data = df_current.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Current Sheet CSV", data=csv_data, file_name=f"{selected_sheet}.csv", mime="text/csv")

else:
    st.info("👈 Please upload your Excel workbook or paste data in the sidebar to get started.")
