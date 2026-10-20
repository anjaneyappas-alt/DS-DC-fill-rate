import streamlit as st
import pandas as pd

st.set_page_config(page_title="DS Sent Qty Table", layout="wide")

st.title("📦 Sent Quantity Summary (DS Wise)")

uploaded_file = st.file_uploader("Upload Transfer Order File", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str).str.strip()

    # Filter DC to DS transfers
    dc_df = df[df['From Location Name'].str.contains('DC', na=False) & df['To Location Name'].str.contains('DS', na=False)].copy()

    # Filter dispatches
    sent_df = dc_df[dc_df['Status'].isin(['Transferred', 'In Transit'])].copy()

    # Group by Date, DS, TO Number, and Reason
    grouped = sent_df.groupby(['Date', 'To Location Name', 'Transfer Order#', 'Reason'], as_index=False).agg(
        Qty=('Quantity Transferred', 'sum')
    )

    # Format Date
    grouped['date'] = pd.to_datetime(grouped['Date'], errors='coerce').dt.strftime('%d-%b')
    grouped.sort_values(by=['To Location Name', 'Transfer Order#'], inplace=True)

    # Blank out duplicate Date and DS for visual grouping
    grouped['Is_First_DS'] = ~grouped.duplicated(subset=['To Location Name'], keep='first')

    grouped['display_date'] = grouped.apply(lambda r: r['date'] if r['Is_First_DS'] else "", axis=1)
    grouped['display_ds'] = grouped.apply(lambda r: r['To Location Name'] if r['Is_First_DS'] else "", axis=1)

    result_df = grouped[['display_date', 'display_ds', 'Transfer Order#', 'Reason', 'Qty']].copy()
    result_df.columns = ['date', 'DS', 'TO', 'reson', 'qty']

    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.TextColumn("date", width="small"),
            "DS": st.column_config.TextColumn("DS", width="medium"),
            "TO": st.column_config.TextColumn("TO", width="medium"),
            "reson": st.column_config.TextColumn("reson", width="large"),
            "qty": st.column_config.NumberColumn("qty", alignment="right")
        }
    )
