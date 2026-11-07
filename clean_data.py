import pandas as pd
from pathlib import Path

project_path = Path(__file__).parent
df_raw = pd.read_csv(project_path / "raw_311_data.csv", dtype="string")

print("Raw dataset shape:", df_raw.shape)

df_clean = df_raw.copy()
print(df_clean.isna().sum().sort_values(ascending=False))

for column in df_clean.columns:
    df_clean[column] = df_clean[column].str.strip()
    df_clean[column] = df_clean[column].replace("", pd.NA)

print("Missing IDs:", df_clean["unique_key"].isna().sum())
print("Repeated IDs:", df_clean["unique_key"].duplicated().sum())  

date_columns = [
    "created_date", "closed_date",
    "due_date", "resolution_action_updated_date"
]

for column in date_columns:
    original_dates = df_clean[column].copy()
    df_clean[column] = pd.to_datetime(
        original_dates, format="ISO8601", errors="coerce"
    )
    parse_errors = original_dates.notna() & df_clean[column].isna()
    df_clean[column + "_parse_error"] = parse_errors
    print(column, "- unparseable values:", parse_errors.sum())

df_clean["invalid_date_order"] = (
    df_clean["closed_date"] < df_clean["created_date"]
)

duration = df_clean["closed_date"] - df_clean["created_date"]

df_clean["resolution_hours"] = (
    duration.dt.total_seconds() / 3600
).where(~df_clean["invalid_date_order"])

print("Invalid date order:", df_clean["invalid_date_order"].sum())
print("Valid resolution durations:", df_clean["resolution_hours"].count())

df_clean["is_closed"] = df_clean["closed_date"].notna()

df_clean["created_year"] = df_clean["created_date"].dt.year
df_clean["created_month"] = df_clean["created_date"].dt.strftime("%Y-%m")
df_clean["created_weekday"] = df_clean["created_date"].dt.day_name()
df_clean["created_hour"] = df_clean["created_date"].dt.hour

for column in ["latitude", "longitude"]:
    original_values = df_clean[column].copy()
    df_clean[column] = pd.to_numeric(original_values, errors="coerce")
    df_clean[column + "_parse_error"] = (
        original_values.notna() & df_clean[column].isna()
    )
    print(column, "- unparseable values:",
          df_clean[column + "_parse_error"].sum())

df_clean["usable_coordinates"] = (
    df_clean["latitude"].between(-90, 90)
    & df_clean["longitude"].between(-180, 180)
).fillna(False)

print("Usable coordinate pairs:", df_clean["usable_coordinates"].sum())

print("Earliest creation:", df_clean["created_date"].min())
print("Latest creation:", df_clean["created_date"].max())
print("Records per month:")
print(df_clean.groupby("created_month").size())
print("Rows after cleaning:", len(df_clean))    

clean_csv_path = project_path / "cleaned_311_data.csv"
df_clean.to_csv(clean_csv_path, index=False)
print("Cleaned data saved:", clean_csv_path)

quality_report = pd.DataFrame({
    "check": [
        "Raw rows", "Cleaned rows", "Missing request IDs",
        "Repeated request IDs", "Invalid date order",
        "Valid resolution durations", "Usable coordinate pairs"
    ],
    "count": [
        len(df_raw),
        len(df_clean),
        df_clean["unique_key"].isna().sum(),
        df_clean["unique_key"].duplicated().sum(),
        df_clean["invalid_date_order"].sum(),
        df_clean["resolution_hours"].count(),
        df_clean["usable_coordinates"].sum()
    ]
})

quality_report.to_csv(project_path / "cleaning_validation_report.csv", index=False)