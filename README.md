# Urban Pulse | NYC 311

An analytics project exploring 100,000 NYC 311 service requests using Python, MySQL and Streamlit.

## Project overview

Urban Pulse examines complaint categories, agency workload, geographic concentration, request trends and recorded time to closure.

The workflow covers API extraction, data cleaning, exploratory analysis, 15 SQL investigations and an interactive dashboard.

## Data

- Source — NYC Open Data 311 API
- Creation window — January 1 through September 30, 2026
- Sample size — 100,000 requests with 25 source fields
- Sampling — monthly proportional allocation with spaced batches
- Full monthly API totals are stored separately in monthly_counts.csv.

## Main results

| Metric | Value |
|---|---:|
| Distinct requests | 100,000 |
| Recorded closure rate | 96.19% |
| Requests without a closure date | 3,811 |
| Valid resolution durations | 96,161 |
| Median recorded resolution | 6.29 hours |
| Valid durations over 72 hours | 26.25% |

Cleaning identified 28 requests whose closure dates preceded their creation dates. These records were retained with quality flags, and their durations were excluded from duration statistics.

## Dashboard

The Streamlit dashboard includes creation-date, borough and complaint-type filters, five KPI cards, complaint and borough charts, a monthly sample trend and a preview of matching records.

The dashboard runs locally and requires a running MySQL database.

## Files

| File | Purpose |
|---|---|
| extract_data.py | Extracts API records and preserves raw batches |
| clean_data.py | Cleans data and creates validation flags |
| eda_analysis.py | Performs Python analysis and creates charts |
| load_mysql.py | Loads cleaned data into MySQL |
| analysis_queries.SQL | Contains the SQL investigations |
| app.py | Runs the Streamlit dashboard |
| monthly_counts.csv | Contains full API monthly totals |
| cleaning_validation_report.csv | Summarizes cleaning checks |
| requirements.txt | Lists Python dependencies |
| Urban_Pulse_Project_Report.md | Documents methods, findings and limitations |

## Local setup

Use Python 3.13 and MySQL 8.0, matching the development environment.

Install dependencies from the repository folder:

```powershell
python -m pip install -r requirements.txt
```

The data scripts use raw_311_data.csv and cleaned_311_data.csv in the project folder. Preserve the saved snapshot to reproduce the reported results. Running extraction again uses the live API, whose records may change.

For a fresh extraction and cleaning run:

```powershell
python extract_data.py
python clean_data.py
python eda_analysis.py
```

Create the database in MySQL Workbench:

```sql
CREATE DATABASE IF NOT EXISTS Urban_pulse_db;
```

Set the connection variables in PowerShell. Replace the username if needed and enter your own password when prompted:

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_DATABASE = "Urban_pulse_db"
$env:MYSQL_USER = "root"

$mysqlPassword = Read-Host "Enter MySQL password" -AsSecureString
$env:MYSQL_PASSWORD = [System.Net.NetworkCredential]::new("", $mysqlPassword).Password
```

Run the loader in that terminal:

```powershell
python load_mysql.py
```

The loader creates service_requests_staging and loads monthly_request_counts. In Workbench, validate staging before publishing:

```sql
USE Urban_pulse_db;

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT unique_key) AS distinct_requests
FROM service_requests_staging;
```

For the first setup, when service_requests does not yet exist:

```sql
RENAME TABLE service_requests_staging TO service_requests;
```

Apply case-sensitive category grouping to match pandas:

```sql
ALTER TABLE service_requests
MODIFY COLUMN complaint_type TEXT
CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
```

Run analysis_queries.SQL in Workbench.

Launch the dashboard from the same PowerShell terminal containing the connection variables:

```powershell
python -m streamlit run app.py
```

Open the local URL printed in the terminal.

## Interpretation

Results describe the collected sample. Spaced batch sampling can affect weekday and hour patterns. Full monthly API totals support the citywide monthly trend.

Recorded closure is measured by closure-date presence. Status labels are analyzed separately. Duration measures elapsed time between recorded creation and closure timestamps.

The 72-hour threshold and IQR boundaries are analytical screening rules. Long durations were retained for investigation.

See [the project report](Urban_Pulse_Project_Report.md) for the data dictionary, investigations and limitations.
