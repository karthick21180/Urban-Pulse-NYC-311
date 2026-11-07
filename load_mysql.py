import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

project_path = Path(__file__).parent

df = pd.read_csv(
    project_path / "cleaned_311_data.csv",
    dtype={"unique_key": "string", "incident_zip": "string"}
)

print("Rows ready for loading:", len(df))

date_columns = [
    "created_date", "closed_date",
    "due_date", "resolution_action_updated_date"
]

for column in date_columns:
    df[column] = pd.to_datetime(df[column], errors="raise")

print(df[date_columns].dtypes)

connection_url = URL.create(
    drivername="mysql+pymysql",
    username=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    database=os.environ["MYSQL_DATABASE"]
)

engine = create_engine(connection_url)

with engine.connect() as connection:
    database_name = connection.execute(text("SELECT DATABASE()")).scalar()
    print("Connected database:", database_name)

print("Loading staging table...")

df.to_sql(
    name="service_requests_staging",
    con=engine,
    if_exists="replace",
    index=False,
    chunksize=1000
)

print("Staging load completed.")

monthly_counts = pd.read_csv(Path(__file__).parent / "monthly_counts.csv")
monthly_counts.to_sql("monthly_request_counts", con=engine, if_exists="replace", index=False)

