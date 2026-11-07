import requests
import pandas as pd
from pathlib import Path
import json

api_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

row_limit = 100000
batch_size = 1000

all_records = []
start_date = "2026-01-01T00:00:00"
end_date = "2026-10-01T00:00:00"
print(all_records, start_date, end_date)

count_parameters = {
    "$select": "date_trunc_ym(created_date) AS month, count(*) AS request_count",
    "$where": f"created_date >= '{start_date}' AND created_date < '{end_date}'",
    "$group": "month",
    "$order": "month"
}
counts_path = Path(__file__).parent / "monthly_counts.csv"
if counts_path.exists():
    monthly_counts = pd.read_csv(counts_path)
else:
    count_response = requests.get(
        api_url, params=count_parameters, timeout=(15, 120)
    )
    count_response.raise_for_status()
    monthly_counts = pd.DataFrame(count_response.json())
    monthly_counts.to_csv(counts_path, index=False)


monthly_counts["request_count"] = monthly_counts["request_count"].astype(int)

monthly_counts["sample_target"] = (
    monthly_counts["request_count"]
    / monthly_counts["request_count"].sum()
    * row_limit
).astype(int)

remaining = row_limit - monthly_counts["sample_target"].sum()
monthly_counts.loc[monthly_counts.index[:remaining], "sample_target"] += 1

print(monthly_counts[["month", "sample_target"]])
print("Total target:", monthly_counts["sample_target"].sum())

selected_fields = [
    "unique_key", "created_date", "closed_date", "due_date",
    "agency", "agency_name", "complaint_type", "descriptor",
    "location_type", "incident_zip", "incident_address",
    "street_name", "cross_street_1", "cross_street_2",
    "address_type", "city", "status", "resolution_description",
    "resolution_action_updated_date", "community_board",
    "borough", "open_data_channel_type", "latitude",
    "longitude", "park_borough"
]
batches_path = Path(__file__).parent / "raw_batches"
batches_path.mkdir(exist_ok=True)

for _, month_row in monthly_counts.iterrows():
    month_start = pd.Timestamp(month_row["month"])
    month_end = month_start + pd.offsets.MonthBegin(1)
    month_target = int(month_row["sample_target"])
    month_total = int(month_row["request_count"])

    print(month_start.strftime("%B"), "target:", month_target)

    for collected in range(0, month_target, batch_size):
        limit = min(batch_size, month_target - collected)
        offset = collected * month_total // month_target

        parameters = {
            "$select": ",".join(selected_fields),
            "$where": (
                f"created_date >= '{month_start.isoformat()}' "
                f"AND created_date < '{month_end.isoformat()}'"
            ),
            "$limit": limit,
            "$offset": offset,
            "$order": "created_date ASC, unique_key ASC"
        }
        batch_path = batches_path / f"{month_start:%Y-%m}_{collected:06d}.json"

        if batch_path.exists():
            with open(batch_path, encoding="utf-8") as file:
                batch_records = json.load(file)
        else:
            response = requests.get(
                api_url, params=parameters, timeout=(15, 120)
            )
            response.raise_for_status()
            batch_records = response.json()

            if not isinstance(batch_records, list) or len(batch_records) != limit:
                raise ValueError(f"Unexpected batch size: {batch_path.name}")

            with open(batch_path, "w", encoding="utf-8") as file:
                json.dump(batch_records, file, ensure_ascii=False, indent=2)

        all_records.extend(batch_records)
        print("Records collected so far:", len(all_records))      

df_raw = pd.DataFrame(all_records).reindex(columns=selected_fields)

print("Rows and columns:", df_raw.shape)
print("Missing request IDs:", df_raw["unique_key"].isna().sum())
print("Repeated request IDs:", df_raw["unique_key"].duplicated().sum())

raw_csv_path = Path(__file__).parent / "raw_311_data.csv"
df_raw.to_csv(raw_csv_path, index=False)
print("Raw data saved:", raw_csv_path)