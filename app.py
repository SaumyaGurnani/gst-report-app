import streamlit as st
import pandas as pd
import os
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns
st.set_page_config(page_title="GST Sales Report", layout="wide")

st.title("🧾 Multi-Platform GST Sales Analyzer")

# --------- UTILITY FUNCTION TO EXTRACT MONTH ----------
def extract_month(file_name, df, platform):
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
              'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    
    for i, m in enumerate(months, start=1):
        if m in file_name.upper():
            return i, m

    # Fallback to column
    date_column = None
    if platform == "meesho":
        if 'month_number' in df.columns:
            try:
                month_num = int(df['month_number'].dropna().mode().iloc[0])
                return month_num, months[month_num - 1]
            except:
                return None, None
        elif 'order_date' in df.columns:
            date_column = 'order_date'
    elif platform == "amazon":
        for col in ['Invoice Date', 'Order Date', 'Shipment Date']:
            if col in df.columns:
                date_column = col
                break
    elif platform == "flipkart":
        if 'Amended Period' in df.columns:
            try:
                month_str = df['Amended Period'].dropna().astype(str).mode().iloc[0]
                dt = datetime.strptime(month_str, "%b-%Y")  # e.g., "Apr-2025"
                return dt.month, dt.strftime("%b").upper()
            except:
                pass

    if date_column:
        try:
            dates = pd.to_datetime(df[date_column], errors='coerce')
            month_num = dates.dt.month.mode().iloc[0]
            return month_num, months[month_num - 1]
        except:
            pass

    return None, None


# --------- LOAD FILE FUNCTION ----------
def load_file(uploaded_file):
    if uploaded_file is None:
        return None
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if file_ext == '.csv':
        return pd.read_csv(uploaded_file)
    elif file_ext in ['.xls', '.xlsx']:
        return pd.read_excel(uploaded_file)
    return None


# --------- FILE UPLOADS ----------
st.subheader("📤 Upload Monthly Files")

amazon_file = st.file_uploader("Amazon File", type=['csv', 'xlsx'], key="amazon")
flipkart_file = st.file_uploader("Flipkart File", type=['csv', 'xlsx'], key="flipkart")
meesho_file = st.file_uploader("Meesho File", type=['csv', 'xlsx'], key="meesho")

# --------- PROCESSING ----------
platform_data = {}

if amazon_file:
    df_amazon = load_file(amazon_file)
    month_num, month_name = extract_month(amazon_file.name, df_amazon, 'amazon')
    platform_data['Amazon'] = {'df': df_amazon, 'month': month_name}

if flipkart_file:
    df_flipkart = load_file(flipkart_file)
    month_num, month_name = extract_month(flipkart_file.name, df_flipkart, 'flipkart')
    platform_data['Flipkart'] = {'df': df_flipkart, 'month': month_name}

if meesho_file:
    df_meesho = load_file(meesho_file)
    month_num, month_name = extract_month(meesho_file.name, df_meesho, 'meesho')
    platform_data['Meesho'] = {'df': df_meesho, 'month': month_name}

# --------- SHOW ANALYSIS ----------


if not platform_data:
    st.warning("Please upload at least one platform's file to continue.")
else:
    st.subheader("📊 Platform-wise Summary")

    sales_summary = []
    tax_summary = []

    for platform, data in platform_data.items():
        df = data['df']
        month = data['month'] or "Unknown"

        # Determine columns dynamically
        if platform == "Amazon":
            total_col = 'Invoice Amount'
            tax_col = 'Total Tax Amount'
            state_col = 'Ship To State'  # if exists
        elif platform == "Flipkart":
            total_col = 'Aggregate Taxable Value Rs.'
            tax_col = 'IGST Amount Rs.'
            state_col = 'Delivered State (PoS)'  # if exists
        elif platform == "Meesho":
            total_col = 'total_invoice_value'
            tax_col = 'tax_amount'
            state_col = 'end_customer_state_new'

        # Basic checks
        if total_col in df.columns and tax_col in df.columns:
            total_sales = df[total_col].sum()
            total_tax = df[tax_col].sum()

            sales_summary.append({'Platform': platform, 'Sales': total_sales})
            tax_summary.append({'Platform': platform, 'Tax': total_tax})

            st.markdown(f"### {platform} – {month}")
            st.metric(label="Total Sales", value=f"₹ {total_sales:,.2f}")
            st.metric(label="Total GST", value=f"₹ {total_tax:,.2f}")

            # State-wise sales breakdown if possible
            if state_col in df.columns:
                state_sales = df.groupby(state_col)[total_col].sum().sort_values(ascending=False).reset_index()
                st.write(f"#### {platform} State-wise Sales Breakdown")
                st.dataframe(state_sales.head(10))

                # Plot top 10 states bar chart
                fig, ax = plt.subplots(figsize=(8,4))
                sns.barplot(data=state_sales.head(10), x=total_col, y=state_col, ax=ax, palette="viridis")
                ax.set_xlabel("Sales Amount")
                ax.set_ylabel("State")
                st.pyplot(fig)
        else:
            st.warning(f"Missing columns in {platform} data: '{total_col}' or '{tax_col}'")

    # Overall sales vs tax bar charts
    if sales_summary and tax_summary:
        sales_df = pd.DataFrame(sales_summary)
        tax_df = pd.DataFrame(tax_summary)

        fig, ax = plt.subplots(figsize=(8,5))
        width = 0.35
        ind = range(len(sales_df))

        ax.bar(ind, sales_df['Sales'], width, label='Sales')
        ax.bar([i + width for i in ind], tax_df['Tax'], width, label='GST Tax')

        ax.set_xticks([i + width/2 for i in ind])
        ax.set_xticklabels(sales_df['Platform'])
        ax.set_ylabel("Amount (₹)")
        ax.set_title("Total Sales vs GST Tax by Platform")
        ax.legend()

        st.pyplot(fig)
