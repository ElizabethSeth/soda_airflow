from datetime import datetime, timedelta
import pandas as pd
import requests

from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# ---- Config ----
POSTGRES_CONN_ID = "postgres_chicago"   
RAW_TABLE = "raw_chicago_crimes"
CLEAN_TABLE = "crimes_clean"
AGG_TABLE = "crimes_by_day"
API_URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="chicago_crimes_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["chicago", "soda", "postgres"],
) as dag:

    @task
    def ingest_api(limit: int = 20000) -> int:
        """Ingest JSON from City of Chicago API to Postgres (raw table)."""
        r = requests.get(API_URL, params={"$limit": limit}, timeout=60)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)

        # Keep a focused set of columns; create them if missing
        wanted = [
            "id", "case_number", "date", "primary_type", "description",
            "location_description", "arrest", "domestic", "district", "ward",
            "community_area", "year", "latitude", "longitude"
        ]
        for c in wanted:
            if c not in df.columns:
                df[c] = None
        df = df[wanted]

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        engine = hook.get_sqlalchemy_engine()
        df.to_sql(RAW_TABLE, engine, index=False, if_exists="replace")
        return len(df)

    soda_scan_raw = BashOperator(
        task_id="soda_scan_raw",
        bash_command=(
            "soda scan "
            "-d postgres_chicago "
            "-c /usr/local/airflow/dags/soda/configuration.yml "
            "/usr/local/airflow/dags/soda/checks/raw_chicago_crimes.yml"
        ),
    )

    @task
    def transform_and_load():
        """Clean types, dedupe, filter, and write clean + daily aggregate tables."""
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        engine = hook.get_sqlalchemy_engine()

        raw = pd.read_sql(f'SELECT * FROM "{RAW_TABLE}"', engine)

        # Type casting
        raw["date"] = pd.to_datetime(raw["date"], errors="coerce", utc=True)
        for col in ["district", "ward", "community_area", "year"]:
            raw[col] = pd.to_numeric(raw[col], errors="coerce").astype("Int64")
        for col in ["latitude", "longitude"]:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

        # Basic cleaning
        clean = (
            raw.dropna(subset=["id"])
               .drop_duplicates(subset=["id"])
               .query("year.isna() == False and year >= 2015")
        )

        # Save clean table
        clean.to_sql(CLEAN_TABLE, engine, index=False, if_exists="replace")

        # Small aggregation: daily counts
        daily = (
            clean.assign(day=clean["date"].dt.date)
                 .groupby("day", dropna=False)
                 .size()
                 .rename("count")
                 .reset_index()
        )
        daily.to_sql(AGG_TABLE, engine, index=False, if_exists="replace")

    soda_scan_clean = BashOperator(
        task_id="soda_scan_clean",
        bash_command=(
            "soda scan "
            "-d postgres_chicago "
            "-c /usr/local/airflow/dags/soda/configuration.yml "
            "/usr/local/airflow/dags/soda/checks/crimes_clean.yml"
        ),
    )

    rows = ingest_api()
    rows >> soda_scan_raw >> transform_and_load() >> soda_scan_clean
