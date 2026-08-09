from __future__ import annotations
from datetime import timedelta
import pendulum

from airflow.decorators import dag, task
from airflow.utils.helpers import chain

# SLI/SLO Definitions
DEFAULT_SLA = timedelta(minutes=5)
EMAIL_ALERT = ['sre-team@empresa.com.br']

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2025, 1, 1, tz="America/Sao_Paulo"),
    'email': EMAIL_ALERT,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'sla': DEFAULT_SLA,
}

@dag(
    dag_id='pdf_processing_pipeline',
    default_args=default_args,
    schedule=None,
    catchup=False,
    tags=['documentos', 'aws', 'sre', 'etl'],
    params={'s3_uri': 's3://uri_default/doc.pdf'},
)
def document_pipeline_dag():
    
    s3_uri = '{{ dag_run.conf["s3_uri"] }}'

    @task(task_id="extract_metadata_and_route")
    def extract_metadata_and_route(uri: str):
        print(f"Roteando documento S3: {uri}")
        return "contract_route" if "contract" in uri else "invoice_route"

    @task(task_id="process_pdf_lambda_trigger", sla=timedelta(minutes=3))
    def process_pdf_lambda_trigger(uri: str):
        print(f"Notificando evento para SQS/Lambda: {uri}")
        return "Lambda execution triggered."

    @task(task_id="validate_extracted_data")
    def validate_extracted_data():
        print("Validação de integridade concluída.")

    @task(task_id="send_notification")
    def send_notification():
        print("Notificação de pipeline finalizado enviada.")

    chain(
        extract_metadata_and_route(uri=s3_uri),
        process_pdf_lambda_trigger(uri=s3_uri),
        validate_extracted_data(),
        send_notification()
    )

pdf_pipeline_dag_instance = document_pipeline_dag()