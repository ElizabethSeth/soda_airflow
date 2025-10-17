from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine

def ingest():
    df = pd.read_csv("/shared_data/fact_resultats_epreuves.csv")
    engine = create_engine("postgresql+psycopg2://user:password@db:5432/sportsdb")
    df.to_sql("fact_resultats_epreuves", engine, if_exists="replace", index=False)

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG("ingest_sports_data",
         default_args=default_args,
         schedule_interval='@hourly',
         catchup=False) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_csv",
        python_callable=ingest
    )
