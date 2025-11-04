from __future__ import annotations
import pendulum

from airflow.decorators import dag, task
from airflow.providers.google.cloud.operators.pubsub import PubSubPublishMessageOperator
from airflow.utils.helpers import chain
from datetime import timedelta

# ==============================================================================
# 1. DEFINIÇÕES GLOBAIS E SLAS
# ==============================================================================

# Define os Objetivos de Nível de Serviço (SLOs) para o Airflow
DEFAULT_SLA = timedelta(minutes=5)   # SLO Principal: O pipeline completo deve rodar em 5 minutos.
EMAIL_ALERT = ['sre-team@empresa.com.br'] # Lista de e-mails para alertas

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2025, 1, 1, tz="America/Sao_Paulo"),
    'email': EMAIL_ALERT,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,                       # Tentar novamente em caso de falha transitória (Resiliência)
    'retry_delay': timedelta(minutes=1),
    'sla': DEFAULT_SLA,                 # Aplica o SLO de 5 minutos ao DAG
}

@dag(
    dag_id='pdf_processing_pipeline',
    default_args=default_args,
    schedule=None, # Rodará via trigger externo (Pub/Sub)
    catchup=False,
    tags=['documentos', 'sre', 'etl'],
    params={'gcs_uri': 'gs://uri_default/doc.pdf'}, # Parâmetro de entrada
)
def document_pipeline_dag():
    
    # Recebe a URI do PDF que acionou o DAG (via Pub/Sub/Trigger)
    pdf_uri = '{{ dag_run.conf["gcs_uri"] }}'

    # ==========================================================================
    # 2. DEFINIÇÃO DAS TASKS
    # ==========================================================================

    @task(task_id="extract_metadata_and_route")
    def extract_metadata_and_route(uri: str):
        """
        Tarefa que faz uma análise inicial do documento e decide a rota.
        Simula a lógica de classificação de documentos.
        """
        print(f"Iniciando metadados e roteamento para URI: {uri}")
        # Lógica: Se for um contrato, use o Processador Lento. Se for uma fatura, use o Processador Rápido.
        if "contract" in uri:
            return "contract_route"
        else:
            return "invoice_route"
    
    routing_choice = extract_metadata_and_route(uri=pdf_uri)


    @task(task_id="process_pdf_function_call", 
          sla=timedelta(minutes=3)) # SLO DE TAREFA: Este é o SLO mais crítico (Latência de Processamento)
    def process_pdf_function_call(uri: str):
        """
        Chama a Cloud Function (o código Python com PyPDF, Tesseract, etc.)
        para o processamento pesado de OCR e extração.
        """
        print(f"Chamando Cloud Function para processamento de: {uri}")
        # Aqui, na vida real, você usaria um operador para chamar a função GCP
        # Ex: GoogleCloudFunctionInvokeFunctionOperator
        return "Extraction complete."

    @task(task_id="validate_extracted_data")
    def validate_extracted_data():
        """
        Realiza a validação final da qualidade dos dados extraídos.
        """
        # Lógica: Verifica se campos críticos (CPF/CNPJ, Valor Total) estão presentes
        # Em caso de falha na validação (baixa qualidade), move para o GCS de Erros.
        print("Dados validados com sucesso.")

    @task(task_id="send_notification")
    def send_notification():
        """
        Notificação final após o processamento completo.
        """
        print("Notificação de conclusão enviada.")


    # ==========================================================================
    # 3. ORQUESTRAÇÃO DO FLUXO (Definição da Ordem)
    # ==========================================================================
    
    # 1. Roteamento (Decisão)
    # 2. Processamento (Core da Cloud Function)
    # 3. Validação
    # 4. Notificação
    chain(
        routing_choice,
        process_pdf_function_call(uri=pdf_uri),
        validate_extracted_data(),
        send_notification()
    )


# Cria a instância do DAG
pdf_pipeline_dag_instance = document_pipeline_dag()