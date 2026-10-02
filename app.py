import streamlit as st
import pandas as pd
import numpy as np
import io

# Set page configuration
st.set_page_config(page_title="DC to DS Reconciliation", layout="wide")

st.title("📦 DC to Dark Store Transfer Reconciliation")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("📥 Data Input Options")
input_method = st.sidebar.radio("Choose Input Method:", ["📋 Copy-Paste Data", "📁 Upload Files", "🔘 Demo Data"])

def standardize_columns(df):
    """Automatically maps common variations of column headers to standard names."""
    if df is None or df.empty:
        return df

    # Strip whitespace
    df.columns = df.columns.astype(str).str.strip()

    # Dynamic Column Mapping Dictionary
    column_mapping = {
        # DS Name mappings
        'ds': 'DS Name', 'ds_name': 'DS Name', 'dark_store': 'DS Name', 
        'darkstore': 'DS Name', 'store': 'DS Name', 'store_name': 'DS Name',
        'ds name': 'DS Name', 'dark store': 'DS Name', 'store name': 'DS Name',
        
        # Dispatched Qty mappings
        'sent_qty': 'Dispatched Qty', 'qty_sent': 'Dispatched Qty', 
        'dispatched_qty': 'Dispatched Qty', 'dispatch_qty': 'Dispatched Qty',
        'sent qty': 'Dispatched Qty', 'qty sent': 'Dispatched Qty',
        'dispatched qty': 'Dispatched Qty', 'dispatch qty': 'Dispatched Qty',
        'picked_qty': 'Dispatched Qty', 'picked qty': 'Dispatched Qty',
        
        # TO Qty / Required Qty mappings
        'to_qty': 'TO Qty', 'to qty': 'TO Qty', 'raised_qty': 'TO Qty',
        'raised qty': 'TO Qty', 'required_qty': 'Required Qty', 'required qty': 'Required Qty',
        
        # Received Qty mappings
        'qty_received': 'Qty Received', 'qty received': 'Qty Received',
        'received_qty': 'Qty Received', 'received qty': 'Qty Received',
        
        # TO Number mappings
        'to_number': 'TO Number', 'to number': 'TO Number', 'to_no': 'TO Number',
        'to no': 'TO Number', 'to_id': 'TO Number', 'to id': 'TO Number',
        
        # Item / SKU mappings
        'sku_code': 'SKU', 'sku code': 'SKU',
        'item_name': 'Item Name', 'item name': 'Item Name', 'description': 'Item Name'
    }

    # Rename matched columns (case-insensitive)
    new_cols = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in column_mapping:
            new_cols[col] = column_mapping[col_lower]
            
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

# --- INPUT HANDLING ---
if input_method == "📋 Copy-Paste Data":
    st.subheader("📋 Paste Raw Data Below (From Excel / Google Sheets)")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("**1. TO Raised Data**\n*(Headers accepted: DS Name / Dark Store, TO Qty / Required Qty, SKU, Item Name)*")
        paste_to = st.text_area("Paste TO Raised Data", height=200)
        df_to = parse_pasted_data(paste_to)

    with col_b:
        st.markdown("**2. TO Picked / Dispatched Data**\n*(Headers accepted: DS Name / Dark Store, Dispatched Qty / Sent Qty, Qty Received)*")
        paste_dispatch = st.text_area("Paste Dispatch Data", height=200)
        df_dispatch = parse_pasted_data(paste_dispatch)

elif input_method == "📁 Upload Files":
    file_to = st.sidebar.file_uploader("1. TO Raised File", type=["csv", "xlsx"])
    file_dispatch = st.sidebar.file_uploader("2. TO Picked File", type=["csv", "xlsx"])
    
    if file_to and file_dispatch:
        df_to = load_file(file_to)
        df_dispatch = load_file(file_dispatch)

else:  # Demo Data
    df_to = pd.DataFrame({
        "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
        "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri"],
        "TO Qty": [1015, 1015, 1015, 1015, 397, 420],
        "SKU": ["T1", "T2", "T3", "T4", "T1", "T1"],
        "Item Name": ["Premium Tea 250g", "Full Cream Milk 1L", "Sunflower Oil 1L", "Sugar 1kg", "Premium Tea 250g", "Premium Tea 250g"],
        "Required Qty": [200, 500, 315, 100, 200, 200],
        "Sent Qty": [199, 475, 300, 100, 180, 150]
    })
    
    df_dispatch = pd.DataFrame({
        "Date": ["26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026", "26/7/2026"],
        "TO Number": ["TO-02078", "TO-02080", "TO-02088", "TO-02086", "TO-02082", "TO-02089", "TO-02084", "TO-02087", "TO-02090"],
        "DS Name": ["DS01 Sarjapur", "DS01 Sarjapur", "DS01 Sarjapur", "DS02 Bileshivale", "DS03 Kengeri", "DS03 Kengeri", "DS04 Chikkabanavara", "DS05 Basavanapura", "DS06 Kogilu"],
        "Dispatched Qty": [206, 730, 38, 361, 158, 216, 428, 251, 366],
        "Qty Received": [206, 730, 38, 361, 158, 216, 428, 251, 366],
        "Damaged": [0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

# --- RECONCILIATION DATA PROCESSING ---
if df_to is not None and df_dispatch is not None:
    
    # Auto-detect DS Name column if still not found
    if 'DS Name' not in df_dispatch.columns:
        possible_ds_cols = [c for c in df_dispatch.columns if 'ds' in c.lower() or 'store' in c.lower()]
        if possible_ds_cols:
            df_dispatch.rename(columns={possible_ds_cols[0]: 'DS Name'}, inplace=True)

    # Auto-detect Dispatched Qty column if still not found
    if 'Dispatched Qty' not in df_dispatch.columns:
        possible_qty_cols = [c for c in df_dispatch.columns if 'qty' in c.lower() or 'sent' in c.lower() or 'dispatch' in c.lower()]
        if possible_qty_cols:
            df_dispatch.rename(columns={possible_qty_cols[0]: 'Dispatched Qty'}, inplace=True)

    # Validate essential columns
    if 'DS Name' not in df_dispatch.columns or 'Dispatched Qty' not in df_dispatch.columns:
        st.warning(f"⚠️ Could not automatically identify Dark Store or Dispatched Quantity columns in Dispatch Data. Found columns: `{list(df_dispatch.columns)}`")
    else:
        # Default missing optional columns
        for col in ['Qty Received', 'Damaged', 'Date', 'TO Number']:
            if col not in df_dispatch.columns:
                df_dispatch[col] = df_dispatch['Dispatched Qty'] if col == 'Qty Received' else ""

        # Shortage calculation
        df_dispatch['Dispatched Qty'] = pd.to_numeric(df_dispatch['Dispatched Qty'], errors='coerce').fillna(0)
        df_dispatch['Qty Received'] = pd.to_numeric(df_dispatch['Qty Received'], errors='coerce').fillna(0)
        df_dispatch['Short Quantity'] = df_dispatch['Dispatched Qty'] - df_dispatch['Qty Received']

        # TO Qty resolution
        if 'TO Qty' in df_to.columns:
            ds_totals = df_to.groupby('DS Name')['TO Qty'].first().reset_index()
        elif 'Required Qty' in df_to.columns:
            df_to['Required Qty'] = pd.to_numeric(df_to['Required Qty'], errors='coerce').fillna(0)
            ds_totals = df_to.groupby('DS Name')['Required Qty'].sum().reset_index().rename(columns={'Required Qty': 'TO Qty'})
        else:
            ds_totals = pd.DataFrame(df_to['DS Name'].unique(), columns=['DS Name'])
            ds_totals['TO Qty'] = 0

        merged_df = pd.merge(df_dispatch, ds_totals, on='DS Name', how='left')

        # Total Dispatched Qty
        ds_dispatch_totals = merged_df.groupby('DS Name').agg(
            Total_Dispatched=('Dispatched Qty', 'sum')
        ).reset_index()

        ds_totals = pd.merge(ds_totals, ds_dispatch_totals, on='DS Name', how='left')
        ds_totals['DC TO Fill rate'] = np.where(ds_totals['TO Qty'] > 0, (ds_totals['Total_Dispatched'] / ds_totals['TO Qty']) * 100, 0)
        ds_totals['Unsent Qty'] = ds_totals['TO Qty'] - ds_totals['Total_Dispatched']

        # Formatting Flags
        merged_df['Is_First'] = ~merged_df.duplicated(subset=['DS Name'], keep='first')
        dc_fill_map = dict(zip(ds_totals['DS Name'], ds_totals['DC TO Fill rate']))
        unsent_map = dict(zip(ds_totals['DS Name'], ds_totals['Unsent Qty']))

        merged_df['DC TO Fill rate raw'] = merged_df['DS Name'].map(dc_fill_map)
        merged_df['Unsent Qty Raw'] = merged_df['DS Name'].map(unsent_map)

        table_df = merged_df.copy()
        table_df['TO Qty'] = table_df.apply(lambda r: f"{int(r['TO Qty']):,}" if r['Is_First'] and pd.notnull(r['TO Qty']) and r['TO Qty'] != 0 else "", axis=1)
        table_df['Unsent Qty'] = table_df.apply(lambda r: f"{int(r['Unsent Qty Raw']):,}" if r['Is_First'] and pd.notnull(r['Unsent Qty Raw']) else "", axis=1)
        table_df['DC TO Fill rate'] = table_df.apply(lambda r: f"{r['DC TO Fill rate raw']:.0f}%" if r['Is_First'] and pd.notnull(r['DC TO Fill rate raw']) else "", axis=1)
        table_df['TO Fill Rate'] = "100%"

        # Summary Metrics
        tot_to_qty = ds_totals['TO Qty'].sum()
        tot_dispatch = df_dispatch['Dispatched Qty'].sum()
        tot_unsent = tot_to_qty - tot_dispatch
        overall_fill_rate = (tot_dispatch / tot_to_qty) * 100 if tot_to_qty > 0 else 0

        # Metrics Display
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total TO Requested", f"{tot_to_qty:,}")
        m2.metric("Total Dispatched", f"{tot_dispatch:,}")
        m3.metric("Total Unsent Qty", f"{tot_unsent:,}")
        m4.metric("DC Fill Rate", f"{overall_fill_rate:.1f}%")

        st.markdown("---")
        
        col_h, col_b = st.columns([4, 1])
        with col_h:
            st.subheader("📋 Main Reconciliation Summary")
        with col_b:
            csv_data = table_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export CSV", data=csv_data, file_name="reconciliation_summary.csv", mime="text/csv", use_container_width=True)

        cols_order = ["Date", "TO Number", "DS Name", "TO Qty", "Dispatched Qty", "Qty Received", "Short Quantity", "Damaged", "Unsent Qty", "TO Fill Rate", "DC TO Fill rate"]
        existing_display_cols = [c for c in cols_order if c in table_df.columns]

        st.dataframe(
            table_df[existing_display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TO Qty": st.column_config.TextColumn(alignment="right"),
                "Dispatched Qty": st.column_config.NumberColumn(alignment="right"),
                "Qty Received": st.column_config.NumberColumn(alignment="right"),
                "Short Quantity": st.column_config.NumberColumn(alignment="right"),
                "Damaged": st.column_config.NumberColumn(alignment="right"),
                "Unsent Qty": st.column_config.TextColumn(alignment="right"),
                "TO Fill Rate": st.column_config.TextColumn(alignment="center"),
                "DC TO Fill rate": st.column_config.TextColumn(alignment="center"),
            }
        )

        # --- SKU UNSENT BREAKDOWN ---
        st.markdown("---")
        st.subheader("🔍 UNSENT SKU BREAKDOWN")

        if 'DS Name' in df_to.columns:
            selected_ds = st.selectbox("Select Dark Store to inspect unfulfilled SKUs:", options=df_to['DS Name'].unique())

            if selected_ds in df_to['DS Name'].values:
                sku_filtered = df_to[df_to['DS Name'] == selected_ds].copy()
                
                if "Required Qty" in sku_filtered.columns and "Sent Qty" in sku_filtered.columns:
                    sku_filtered['Required Qty'] = pd.to_numeric(sku_filtered['Required Qty'], errors='coerce').fillna(0)
                    sku_filtered['Sent Qty'] = pd.to_numeric(sku_filtered['Sent Qty'], errors='coerce').fillna(0)
                    
                    sku_filtered['Unsent Qty'] = sku_filtered['Required Qty'] - sku_filtered['Sent Qty']
                    
                    # STRICT FILTER: ONLY SHOW UNFULFILLED SKUS
                    unsent_skus_only = sku_filtered[sku_filtered['Unsent Qty'] > 0].copy()

                    if not unsent_skus_only.empty:
                        display_sku_cols = ["SKU", "Item Name", "Required Qty", "Sent Qty", "Unsent Qty"]
                        existing_cols = [c for c in display_sku_cols if c in unsent_skus_only.columns]

                        st.dataframe(
                            unsent_skus_only[existing_cols],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Required Qty": st.column_config.NumberColumn(alignment="right"),
                                "Sent Qty": st.column_config.NumberColumn(alignment="right"),
                                "Unsent Qty": st.column_config.NumberColumn(alignment="right"),
                            }
                        )
                    else:
                        st.success(f"🎉 All SKUs for {selected_ds} were 100% fulfilled! No unsent items.")
                else:
                    st.info("Include `SKU`, `Required Qty`, and `Sent Qty` headers in your TO Raised input to view SKU-level shortages.")
else:
    st.info("👈 Please enter data or select demo mode in the sidebar to generate the report.")
