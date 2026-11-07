import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

project_path = Path(__file__).parent

df = pd.read_csv(
    project_path / "cleaned_311_data.csv",
    dtype={"unique_key": "string", "incident_zip": "string"}
)

resolution = pd.to_numeric(df["resolution_hours"], errors="coerce").dropna()

print("Records loaded:", len(df))
print("Valid resolution durations:", len(resolution))

summary = resolution.describe()

summary["range"] = resolution.max() - resolution.min()
summary["variance"] = resolution.var()
summary["skewness"] = resolution.skew()

print(summary)

q1 = resolution.quantile(0.25)
q3 = resolution.quantile(0.75)
iqr = q3 - q1

lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

df["resolution_outlier"] = (
    (df["resolution_hours"] < lower_bound)
    | (df["resolution_hours"] > upper_bound)
)

print("IQR:", iqr)
print("Lower boundary:", lower_bound)
print("Upper boundary:", upper_bound)
print("Flagged durations:", df["resolution_outlier"].sum())
summary.to_csv(project_path / "resolution_statistics.csv", header=["value"])

df.loc[df["resolution_outlier"]].to_csv(
    project_path / "resolution_outliers.csv", index=False
)

print("Statistics and outlier records saved.")

plt.figure(figsize=(10, 5))
plt.hist(resolution, bins=50, edgecolor="black")
plt.title("Recorded Resolution Duration — Valid Cases")
plt.xlabel("Resolution hours")
plt.ylabel("Number of requests")
plt.yscale("log")
plt.tight_layout()
plt.savefig(project_path / "resolution_histogram.png", dpi=150)
plt.close()

print("Histogram saved.")

plt.figure(figsize=(10, 4))
plt.boxplot(resolution, vert=False, showfliers=True)
plt.title("Recorded Resolution Duration — Boxplot")
plt.xlabel("Resolution hours")
plt.tight_layout()
plt.savefig(project_path / "resolution_boxplot.png", dpi=150)
plt.close()

print("Boxplot saved.")


# 1. Total distinct request volume.

print("Total distinct requests:", df["unique_key"].nunique())

# 2. Top 10 complaint categories

top_complaints = df["complaint_type"].value_counts().head(10)
print("\n1. Total distinct request volume",top_complaints)

plt.figure(figsize=(10, 6))
top_complaints.sort_values().plot(kind="barh")
plt.title("Top 10 Complaint Types — Sample")
plt.xlabel("Number of requests")
plt.ylabel("Complaint type")
plt.tight_layout()
plt.savefig(project_path / "top_10_complaints.png", dpi=150)
plt.close()

# 3. Agency workload distribution
agency_counts = df["agency"].value_counts()

print("\n3. Agency workload distribution")
print(agency_counts)

agency_counts.to_csv(
    project_path / "agency_workload.csv",
    header=["request_count"]
)

plt.figure(figsize=(10, 7))
agency_counts.sort_values().plot(kind="barh")
plt.title("Recorded Request Volume by Agency — Sample")
plt.xlabel("Number of requests")
plt.ylabel("Agency")
plt.tight_layout()
plt.savefig(project_path / "agency_workload.png", dpi=150)
plt.close()

# 4. Request volume by borough
borough_counts = df["borough"].value_counts(dropna=False)

print("\n4. Request volume by borough")
print(borough_counts)

borough_counts.to_csv(
    project_path / "borough_request_volume.csv",
    header=["request_count"]
)

plt.figure(figsize=(9, 5))
borough_counts.sort_values().plot(kind="barh")
plt.title("Request Volume by Borough — Sample")
plt.xlabel("Number of requests")
plt.ylabel("Borough")
plt.tight_layout()
plt.savefig(project_path / "borough_request_volume.png", dpi=150)
plt.close()

# 5. Monthly request trend - full API counts
monthly_trend = pd.read_csv(project_path / "monthly_counts.csv")
monthly_trend["month"] = pd.to_datetime(monthly_trend["month"])
monthly_trend = monthly_trend.sort_values("month")

print("\n5. Monthly request trend - full API counts")
print(monthly_trend)

plt.figure(figsize=(10, 5))
plt.plot(
    monthly_trend["month"].dt.strftime("%Y-%m"),
    monthly_trend["request_count"],
    marker="o"
)
plt.title("Monthly NYC 311 Request Volume — Full API Counts")
plt.xlabel("Creation month")
plt.ylabel("Number of requests")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(project_path / "monthly_request_trend.png", dpi=150)
plt.close()

# 6. Demand by weekday and hour
weekday_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

weekday_hour = pd.crosstab(
    df["created_weekday"], df["created_hour"]
).reindex(index=weekday_order, columns=range(24), fill_value=0)

print("\n6. Demand by weekday and hour — Sample")
print(weekday_hour)

weekday_hour.to_csv(project_path / "weekday_hour_counts.csv")

plt.figure(figsize=(12, 5))
plt.imshow(weekday_hour, aspect="auto", cmap="Blues")
plt.xticks(range(24))
plt.yticks(range(7), weekday_order)
plt.colorbar(label="Number of requests")
plt.title("Requests by Weekday and Hour — Sample")
plt.xlabel("Creation hour (0–23)")
plt.ylabel("Creation weekday")
plt.tight_layout()
plt.savefig(project_path / "weekday_hour_heatmap.png", dpi=150)
plt.close()

# 7. Distribution of recorded request statuses
status_counts = df["status"].value_counts(dropna=False)

print("\n7. Recorded request statuses")
print(status_counts)

status_counts.to_csv(
    project_path / "request_status_counts.csv",
    header=["request_count"]
)

plt.figure(figsize=(9, 5))
status_counts.sort_values().plot(kind="barh")
plt.title("Recorded Request Statuses — Sample")
plt.xlabel("Number of requests")
plt.ylabel("Status")
plt.tight_layout()
plt.savefig(project_path / "request_status_distribution.png", dpi=150)
plt.close()

# 9. Median resolution duration by complaint category
category_resolution = (
    df.groupby("complaint_type")["resolution_hours"]
    .agg(valid_duration_count="count", median_hours="median")
    .sort_values("median_hours", ascending=False)
)

print("\n9. Median resolution hours by complaint category")
print(category_resolution.head(10))

category_resolution.to_csv(
    project_path / "resolution_by_complaint_type.csv"
)

category_chart = (
    category_resolution[
        category_resolution["valid_duration_count"] >= 30
    ]
    .head(10)
    .sort_values("median_hours")
)

category_chart["median_hours"].plot(
    kind="barh", figsize=(11, 6)
)
plt.title("Highest Median Resolution Hours — Sample Categories with n ≥ 30")
plt.xlabel("Median resolution hours")
plt.ylabel("Complaint category")
plt.tight_layout()
plt.savefig(project_path / "resolution_by_complaint_type.png", dpi=150)
plt.close()

# 10. Median resolution duration by agency
agency_resolution = (
    df.groupby("agency")["resolution_hours"]
    .agg(valid_duration_count="count", median_hours="median")
    .sort_values("median_hours", ascending=False)
)

print("\n10. Median resolution hours by agency")
print(agency_resolution)

agency_resolution.to_csv(
    project_path / "resolution_by_agency.csv"
)

agency_chart = agency_resolution[
    agency_resolution["valid_duration_count"] >= 30
].sort_values("median_hours")

agency_chart["median_hours"].plot(kind="barh", figsize=(10, 6))
plt.title("Median Resolution Hours by Agency — Sample, n ≥ 30")
plt.xlabel("Median resolution hours")
plt.ylabel("Agency")
plt.tight_layout()
plt.savefig(project_path / "resolution_by_agency.png", dpi=150)
plt.close()

# 11. IQR-based outlier investigation
longest_cases = (
    df.loc[
        df["resolution_outlier"],
        ["unique_key", "agency", "complaint_type",
         "created_date", "closed_date", "resolution_hours"]
    ]
    .sort_values("resolution_hours", ascending=False)
    .head(10)
)

print("\n11. Ten longest IQR-flagged durations")
print(longest_cases.to_string(index=False))

longest_cases.to_csv(
    project_path / "longest_flagged_cases.csv", index=False
)

# 13. Geographic complaint concentration - borough summary
geographic_summary = borough_counts.rename("request_count").to_frame()

geographic_summary["sample_percentage"] = (
    geographic_summary["request_count"] / len(df) * 100
).round(2)

print("\n13. Geographic concentration by borough — Sample")
print(geographic_summary)

geographic_summary.to_csv(
    project_path / "geographic_borough_summary.csv"
)

# 14. Recorded closure-rate comparison by borough
closure_by_borough = (
    df.groupby("borough", dropna=False)["is_closed"]
    .agg(total_requests="size", recorded_closed="sum")
)

closure_by_borough["closure_rate_percent"] = (
    closure_by_borough["recorded_closed"]
    / closure_by_borough["total_requests"] * 100
)

print("\n14. Recorded closure rate by borough")
print(closure_by_borough)

closure_by_borough.to_csv(
    project_path / "closure_rate_by_borough.csv"
)

closure_by_borough["closure_rate_percent"].sort_values().plot(
    kind="barh", figsize=(9, 5)
)
plt.title("Recorded Closure Rate by Borough — Sample")
plt.xlabel("Requests with recorded closure (%)")
plt.ylabel("Borough")
plt.xlim(0, 100)
plt.tight_layout()
plt.savefig(project_path / "closure_rate_by_borough.png", dpi=150)
plt.close()

# 15. High volume and long median resolution duration
category_priority = (
    df.groupby("complaint_type")
    .agg(
        request_count=("unique_key", "nunique"),
        valid_duration_count=("resolution_hours", "count"),
        median_hours=("resolution_hours", "median")
    )
)

eligible = category_priority[
    category_priority["valid_duration_count"] >= 30
].copy()

volume_threshold = eligible["request_count"].quantile(0.75)
duration_threshold = eligible["median_hours"].quantile(0.75)

priority_categories = eligible[
    (eligible["request_count"] >= volume_threshold)
    & (eligible["median_hours"] >= duration_threshold)
].sort_values("request_count", ascending=False)

print("\n15. High-volume, long-duration categories")
print("Volume threshold:", volume_threshold)
print("Median-hours threshold:", duration_threshold)
print(priority_categories)

priority_categories.to_csv(
    project_path / "priority_complaint_categories.csv"
)

plt.figure(figsize=(10, 6))
plt.scatter(
    eligible["request_count"],
    eligible["median_hours"],
    alpha=0.6,
    label="Categories with 30+ valid durations"
)

plt.scatter(
    priority_categories["request_count"],
    priority_categories["median_hours"],
    color="red",
    label="Meets both thresholds"
)

plt.axvline(volume_threshold, color="grey", linestyle="--")
plt.axhline(duration_threshold, color="grey", linestyle="--")
plt.title("Complaint Volume and Median Resolution Duration — Sample")
plt.xlabel("Number of requests")
plt.ylabel("Median resolution hours")
plt.legend()
plt.tight_layout()
plt.savefig(project_path / "volume_vs_resolution.png", dpi=150)
plt.close()