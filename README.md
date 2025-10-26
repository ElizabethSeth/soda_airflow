# 🧠 Chicago Crimes Data Pipeline – Airflow + Soda + PostgreSQL

## 📋 Project Overview
This project implements a **complete data pipeline** using **Apache Airflow** (via Astro CLI), **Soda Core** for data quality validation, and **PostgreSQL** for storage.  
It automates the process of **ingesting**, **validating**, **transforming**, and **loading** public crime data from the **City of Chicago API**.

---

## 🚀 Architecture

### 🧰 Tools & Technologies

| Tool | Role |
|------|------|
| 🌀 **Airflow (Astro CLI)** | Orchestrates ETL tasks |
| 🧪 **Soda Core** | Validates data quality before and after transformation |
| 🗄️ **PostgreSQL** | Stores raw and cleaned datasets |
| 🌐 **Public API (Chicago Crimes)** | Data source |

---

## 🏗️ Pipeline Structure

### DAG: `chicago_crimes_pipeline`

| Step | Task ID | Description |
|------|----------|-------------|
| 1️⃣ | `ingest_api` | Fetches data from the **Chicago Crimes API** and stores it in the PostgreSQL raw table |
| 2️⃣ | `soda_scan_raw` | Performs Soda data quality checks on **raw data** |
| 3️⃣ | `transform_and_load` | Cleans and transforms data before loading into the cleaned table |
| 4️⃣ | `soda_scan_clean` | Runs final Soda quality checks on **transformed data** |
| 5️⃣ | `load_to_postgres` | Final load of validated data into PostgreSQL for analytics |

---

## 📂 Project Structure

app_docker/
├── dags/
│ ├── chicago_crimes_pipeline.py # Main Airflow DAG
│ ├── soda/
│ │ ├── configuration.yml # Soda configuration
│ │ └── checks/
│ │ ├── raw_chicago_crimes.yml # Soda checks for raw data
│ │ └── crimes_clean.yml # Soda checks for cleaned data
├── data/ # (optional) Local storage
├── docker-compose.override.yml # Custom Docker setup
├── airflow_settings.yaml # Airflow connection settings
├── Dockerfile # Custom Airflow image build
├── requirements.txt # Python dependencies
└── README.md # Documentation


### 1️⃣ Start the environment
astro dev start
Airflow UI → http://localhost:8080

PostgreSQL → localhost:5432

Default credentials → postgres/postgres

### 2️⃣ Verify running containers
astro dev ps

### 3️⃣ Run the pipeline manually

Go to the Airflow UI and trigger the DAG:

chicago_crimes_pipeline

### 4️⃣ View Soda results

Open the logs of soda_scan_raw and soda_scan_clean to view data quality validation summaries.

## ✅ Data Quality Checks (Soda)
raw_chicago_crimes.yml
checks for raw_chicago_crimes:
  - row_count > 0
  - missing_count(id) = 0
  - duplicate_count(id) = 0
  - invalid_percent(primary_type) < 20 %:
      valid values:
        - THEFT
        - ASSAULT
        - BATTERY
        - ROBBERY

crimes_clean.yml
checks for crimes_clean:
  - row_count > 0
  - missing_count(id) = 0
  - duplicate_count(id) = 0
  - freshness(ts) < 48h
  - invalid_percent(latitude) = 0:
      valid min: -90
      valid max: 90
  - invalid_percent(longitude) = 0:
      valid min: -180
      valid max: 180

### 📊 Results

✅ Fully automated end-to-end pipeline
✅ Soda quality checks before and after transformation
✅ Seamless integration between Airflow, PostgreSQL, and Soda
✅ Ready for extension to other public datasets
