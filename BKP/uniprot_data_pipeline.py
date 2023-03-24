import sys
import os
import logging
from datetime import datetime, timedelta
from parse_uniprot_xml import download_xml_from_minio, parse_uniprot_xml, connect_to_neo4j, store_data_in_neo4j
from airflow.models import DAG, Variable
from airflow.operators.python import PythonOperator
from minio import Minio
from minio.error import S3Error


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 3, 19),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 4
}

dag = DAG(
    'uniprot_data_pipeline',
    default_args=default_args,
    description='UniProt XML Data Pipeline',
    schedule_interval=timedelta(days=1),
    catchup=False,
    max_active_runs=1
)

def execute_pipeline():
    try:
        # Download the XML file from MinIO
        minio_client = Minio(
            "minio:9000",
            access_key="admin",
            secret_key="password",
            secure=False
        )
        bucket_name = "bucket"
        object_name = "Q9Y261.xml"
        local_xml_path = os.path.join(os.path.abspath("dags"), "Q9Y261.xml")
        download_xml_from_minio(bucket_name, object_name, minio_client, local_xml_path)

        # Parse the XML file and process the data
        parsed_data = parse_uniprot_xml(local_xml_path)

        # Connect to the Neo4j database
        uri = "bolt://neo4j:7687"
        user = "neo4j"
        password = "password"
        driver = connect_to_neo4j(uri, user, password)

        # Store the parsed data in the Neo4j database
        store_data_in_neo4j(driver, parsed_data)

        # Close the Neo4j driver
        driver.close()
        
    except S3Error as e:
        logging.warning(f"S3 operation failed: {e}")
        
    except ET.ParseError as e:
        logging.warning(f"Error parsing XML file: {e}")

execute_pipeline_task = PythonOperator(
    task_id="execute_pipeline",
    python_callable=execute_pipeline,
    dag=dag,
)
