import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

st.set_page_config(page_title="Urban Pulse | NYC 311", layout="wide")
st.title("Urban Pulse | NYC 311")
st.caption("Explore our sample of 100,000 service requests created January–September 2026.")


@st.cache_data(ttl=600)
def load_requests():
    database_url = URL.create(
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        database=os.environ["MYSQL_DATABASE"],
    )
    engine = create_engine(database_url)

    query = text("""
        SELECT unique_key, created_date, closed_date, borough,
               complaint_type, agency, status, resolution_hours
        FROM service_requests
    """)

    try:
        with engine.connect() as connection:
            return pd.read_sql_query(
                query,
                connection,
                parse_dates=["created_date", "closed_date"],
            )
    finally:
        engine.dispose()


try:
    requests_df = load_requests()
except KeyError as error:
    st.error(f"MySQL setting {error.args[0]} is missing. Start the app using the PowerShell block.")
    st.stop()
except SQLAlchemyError:
    st.error("Could not read service_requests. Check that MySQL is running and the login works in Workbench.")
    st.stop()

requests_df = requests_df.dropna(subset=["created_date"])

if requests_df.empty:
    st.info("No requests with creation dates were found.")
    st.stop()

st.sidebar.header("Filters")

first_date = requests_df["created_date"].min().date()
last_date = requests_df["created_date"].max().date()

date_range = st.sidebar.date_input(
    "Request creation date",
    value=(first_date, last_date),
    min_value=first_date,
    max_value=last_date,
)

boroughs = st.sidebar.multiselect(
    "Borough",
    options=sorted(requests_df["borough"].dropna().unique()),
    help="Leave empty to include all boroughs.",
)

complaint_types = st.sidebar.multiselect(
    "Complaint type",
    options=sorted(requests_df["complaint_type"].dropna().unique()),
    help="Leave empty to include all complaint types.",
)

if len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range
end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)

filtered = requests_df.loc[
    (requests_df["created_date"] >= pd.Timestamp(start_date))
    & (requests_df["created_date"] < end_exclusive)
]

if boroughs:
    filtered = filtered.loc[filtered["borough"].isin(boroughs)]

if complaint_types:
    filtered = filtered.loc[filtered["complaint_type"].isin(complaint_types)]

if filtered.empty:
    st.info("No requests match the selected filters.")
    st.stop()

total_requests = filtered["unique_key"].nunique()
recorded_closed = filtered["closed_date"].notna()
closure_rate = recorded_closed.mean() * 100
no_closure_date = filtered["closed_date"].isna().sum()

durations = filtered["resolution_hours"].dropna()
valid_durations = durations[durations >= 0]

median_display = "N/A"
over_72_display = "N/A"

if not valid_durations.empty:
    median_display = f"{valid_durations.median():,.2f} h"
    over_72_display = f"{(valid_durations > 72).mean() * 100:.2f}%"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total requests", f"{total_requests:,}")
col2.metric("Recorded closure rate", f"{closure_rate:.2f}%")
col3.metric("No closure date", f"{no_closure_date:,}")
col4.metric("Median resolution", median_display)
col5.metric("Over 72 hours", over_72_display)

st.caption(
    "Recorded closure means a closure date is present. "
    "Median resolution and the percentage over 72 hours use valid durations only."
)

left, right = st.columns(2)

with left:
    st.subheader("Top 10 complaint types")
    complaint_counts = filtered["complaint_type"].value_counts().head(10)
    st.bar_chart(complaint_counts.rename("Requests"))

with right:
    st.subheader("Requests by borough")
    borough_counts = filtered["borough"].value_counts()
    st.bar_chart(borough_counts.rename("Requests"))

st.subheader("Monthly request volume in the filtered sample")
monthly_counts = (
    filtered.groupby(filtered["created_date"].dt.to_period("M"))
    .size()
    .sort_index()
)
monthly_counts.index = monthly_counts.index.astype(str)
st.line_chart(monthly_counts.rename("Requests"))

st.subheader("Latest 100 matching requests")
st.dataframe(
    filtered.sort_values("created_date", ascending=False).head(100),
    hide_index=True,
)