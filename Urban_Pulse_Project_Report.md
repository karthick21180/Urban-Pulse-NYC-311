# Urban Pulse | NYC 311 Service Requests

**GUVI Data Science Project · Karthick S**

## Project objective

Urban Pulse analyzes NYC 311 service requests to understand what residents report, where requests are concentrated, which agencies handle them, and how long recorded closure takes. The project combines Python for extraction and analysis, MySQL for storage and SQL investigations, and Streamlit for interactive exploration.

## Data source and extraction

The source is the [NYC Open Data 311 API](https://data.cityofnewyork.us/resource/erm2-nwe9.json). The extraction window includes requests created from January 1 through September 30, 2026. October 1 is the exclusive upper bound. Closure dates may fall after the creation window.

1. Queried the API for full monthly counts and saved them in `monthly_counts.csv`.
2. Allocated the 100,000-record target across months in proportion to their full counts. Rounded down to whole records and distributed the remaining slots.
3. Requested up to 1,000 records per batch, using spaced offsets within each month. Records were ordered by creation timestamp and request ID. Each batch was saved as JSON so extraction could resume after an interruption.
4. Combined the batches into `raw_311_data.csv`. The raw snapshot contained **100,000 rows and 25 columns**, with no missing or duplicate request IDs.

| Month | Full API count | Sample count |
|---|---:|---:|
| January | 348,511 | 11,655 |
| February | 334,691 | 11,193 |
| March | 342,390 | 11,451 |
| April | 302,190 | 10,106 |
| May | 331,980 | 11,102 |
| June | 334,834 | 11,198 |
| July | 343,133 | 11,474 |
| August | 328,922 | 10,999 |
| September | 323,632 | 10,822 |
| **Total** | **2,990,283** | **100,000** |

## Cleaning and validation

The cleaning script preserved the raw snapshot and wrote a separate `cleaned_311_data.csv` with all 100,000 rows. It trimmed text, treated blank strings as missing, preserved request IDs and ZIP codes as text, parsed timestamps, and converted coordinates to numeric values. Missing IDs, dates and coordinates were left missing. The script also derived creation year, month, weekday and hour.

| Check | Result |
|---|---:|
| Missing or repeated request IDs | 0 |
| Unparseable nonblank timestamps in the four checked date fields | 0 |
| Requests without a closure date | 3,811 |
| Closure dates before creation | 28 |
| Valid resolution durations | 96,161 |
| Usable coordinate pairs within global latitude and longitude ranges | 97,574 |

Resolution hours were calculated as `(closed_date − created_date) / 1 hour`. Missing or invalid durations were left blank for duration analysis. Long but valid durations were retained. Closure-date presence was tracked separately, so the 28 records with invalid date order still count as having a recorded closure date.

## Data dictionary

| Field or field group | Meaning and analytical use |
|---|---|
| `unique_key` | Source request identifier. Used for distinct request counts. |
| `created_date`, `closed_date` | Request creation and recorded closure timestamps. |
| `due_date`, `resolution_action_updated_date` | Optional source timestamps for the recorded due date and latest resolution action update. |
| `agency`, `agency_name` | Agency code and name. Used for workload and median-duration comparisons. |
| `complaint_type`, `descriptor` | Source complaint category and additional detail. Original case is preserved. |
| `status`, `resolution_description` | Source workflow status and recorded resolution text. |
| `borough`, `city`, `incident_zip`, `community_board`, `park_borough` | Geographic and administrative labels. |
| `incident_address`, `street_name`, `cross_street_1`, `cross_street_2`, `address_type`, `location_type` | Incident location details. |
| `latitude`, `longitude` | Numeric coordinates. |
| `open_data_channel_type` | Channel through which the request was recorded. |
| `created_year`, `created_month`, `created_weekday`, `created_hour` | Derived time fields used for grouping and trend analysis. |
| `resolution_hours` | Nonnegative elapsed hours between creation and recorded closure, where both dates are valid. |
| `is_closed` | True when a closure date is present. |
| Parse flags, `invalid_date_order`, `usable_coordinates` | Quality checks for conversion failures, reversed dates and coordinate ranges. |

## Python and MySQL investigations

Python used pandas for analysis and Matplotlib for charts. The cleaned CSV was loaded into a MySQL staging table in batches, then validated and renamed to `service_requests`. The full API monthly totals were loaded separately into `monthly_request_counts`. SQL category grouping was made case-sensitive to match Python, preserving labels such as `PLUMBING` and `Plumbing` as separate categories.

| # | Investigation | Result or interpretation |
|---:|---|---|
| 1 | Distinct request volume | 100,000 distinct request IDs in the sample. |
| 2 | Top 10 complaint categories | Illegal Parking ranked first with 15,852 requests, followed by Noise - Residential with 10,350. |
| 3 | Agency workload | NYPD handled 45,339 sampled requests, followed by HPD with 19,731. Volume measures recorded requests. |
| 4 | Borough volume | Brooklyn led with 31,002, followed by Queens with 25,074. |
| 5 | Full monthly trend | January had the highest full API count at 348,511. April had the lowest at 302,190. |
| 6 | Weekday and hour | Wednesday 10:00–10:59 had 3,210 sampled requests. The batch design can affect apparent peaks. |
| 7 | Recorded statuses | 95,080 requests had status Closed. This differs from the 96,189 with a closure date. |
| 8 | Resolution statistics | Across 96,161 valid durations, mean was 152.19 hours, median was 6.29 hours, and sample standard deviation was 441.08 hours. |
| 9 | Median by complaint category | Taxi Complaint had a median of 4,791.92 hours across 36 valid durations. Several high-ranking categories had very few cases. |
| 10 | Median by agency | OOS had a median of 1,199.60 hours across 95 valid durations. EDC had no valid durations for a median. |
| 11 | IQR screening | Q1 was 1.07 hours, Q3 was 78.23 hours and IQR was 77.16 hours. The 193.97-hour upper boundary flagged 14,909 durations for review. |
| 12 | Duration distribution | Skewness of 5.71 and a mean well above the median indicate a long right tail. |
| 13 | Geographic concentration | Brooklyn accounted for 31.00% of sampled requests, followed by Queens at 25.07%. |
| 14 | Recorded closure by borough | The Bronx had the highest rate among named boroughs at 97.72%. Brooklyn recorded 29,940 closure dates out of 31,002 requests (96.57%). |
| 15 | High-volume, long-duration categories | Six categories met the sample-based thresholds, including UNSANITARY CONDITION and PLUMBING. Screening used the 75th percentiles of volume and median duration among categories with at least 30 valid durations. |

## Streamlit dashboard

The app reads from MySQL and filters requests by **creation date, borough and complaint type**. Charts show top complaint types, borough volume and monthly volume within the filtered sample. A detail table displays the latest 100 matching requests.

| Default dashboard metric | Observed value | Definition |
|---|---:|---|
| Total requests | 100,000 | Distinct request IDs. |
| Recorded closure rate | 96.19% | Share of requests with a closure date. |
| No closure date | 3,811 | Requests with a missing closure date. |
| Median resolution | 6.29 hours | Median among valid durations. |
| Over 72 hours | 26.25% | Share of valid durations greater than 72 hours. |

The dashboard ran locally and displayed the default metrics above. The Brooklyn filter displayed a 100-row preview containing only Brooklyn requests.

## Interpretation and limitations

The monthly allocation preserves the approximate monthly mix, but the sample uses spaced blocks of consecutive records. Within-month patterns, especially weekday and hour peaks, may reflect how those blocks were selected. Use the separate full API counts for citywide monthly volume and describe the remaining findings as sample results.

Recorded closure reflects the source timestamp. It cannot establish resident satisfaction or how much time an agency actively worked on a request. The 72-hour threshold and IQR boundaries are analytical screening rules. Borough counts measure reporting volume and do not adjust for population or reporting behavior.

## Project files and reviewer setup

| File | Purpose |
|---|---|
| `extract_data.py` | Collects monthly totals and raw request batches. |
| `clean_data.py` | Cleans data, derives fields and checks quality. |
| `eda_analysis.py` | Runs Python investigations and generates analysis outputs. |
| `load_mysql.py` | Loads cleaned requests into staging and full monthly totals into MySQL. |
| `analysis_queries.sql` | Contains the SQL investigations. |
| `app.py` | Runs the interactive Streamlit dashboard. |
| `raw_311_data.csv`, `cleaned_311_data.csv`, `monthly_counts.csv` | Saved source snapshot, cleaned dataset and full monthly counts. |

To run the dashboard, use a Python environment with pandas, SQLAlchemy, PyMySQL and Streamlit. Start MySQL with the two project tables available. Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER` and `MYSQL_PASSWORD` in the same terminal used to run:

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. Keep database credentials out of submitted files.
