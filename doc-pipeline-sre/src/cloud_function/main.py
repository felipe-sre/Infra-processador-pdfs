import json
import base64
import time
import logging

from google.cloud import storage
from pypdf import PdfReader
# Importe outras bibliotecas conforme o necessário (pdfplumber, Pillow, etc.)

# ==============================================================================
# 1. CONFIGURAÇÃO SRE: LOGGING E MÉTRICAS
# ==============================================================================

# Configura o Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTA SRE: Em um ambiente GCP, as métricas e logs são enviadas automaticamente
# para o Cloud Monitoring e Cloud Logging. O Prometheus e Loki (Fase III)
# serão configurados para 'ler' esses dados.

# ==============================================================================
# 2. FUNÇÃO PRINCIPAL DA CLOUD FUNCTION
# ==============================================================================

def process_pdf_pipeline(event, context):
    """
    Função principal que é chamada pelo gatilho do Pub/Sub.
    
    Args:
        event (dict): Dados do evento Pub/Sub (contém a mensagem codificada).
        context (google.cloud.functions.Context): Metadados de contexto.
    """
    
    # ----------------------------------------------------
    # SRE: MEDIÇÃO DE LATÊNCIA (START TIME)
    # ----------------------------------------------------
    start_time = time.time()
    
    try:
        # Decodifica a mensagem do Pub/Sub para obter a URI do GCS
        pubsub_data = base64.b64decode(event['data']).decode('utf-8')
        message_json = json.loads(pubsub_data)
        gcs_uri = message_json['gcs_uri']  # Ex: gs://seu-bucket-entrada/doc.pdf
        
        logger.info(f"Iniciando processamento do documento: {gcs_uri}")
        
        # 1. ANÁLISE INICIAL E LEITURA DO GCS
        # Separa o bucket e o nome do arquivo da URI
        bucket_name, file_name = gcs_uri.replace("gs://", "").split("/", 1)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        # Baixa o PDF para o ambiente temporário da função (/tmp/)
        local_pdf_path = f"/tmp/{file_name.split('/')[-1]}"
        blob.download_to_filename(local_pdf_path)
        
        # ----------------------------------------------------
        # 2. LÓGICA DE PROCESSAMENTO (Core do Pipeline)
        # ----------------------------------------------------
        
        reader = PdfReader(local_pdf_path)
        num_pages = len(reader.pages)
        extracted_text = ""
        
        # SRE/DEV: Log detalhado do processo de extração
        logger.info(f"Documento com {num_pages} páginas. Iniciando extração.")
        
        for page in reader.pages:
            # Aqui você teria a lógica mais complexa (pdfplumber, Pillow, etc.)
            extracted_text += page.extract_text() or ""
        
        # Simulação de um erro de lógica de negócio (ex: falta campo crítico)
        if "VALOR_INVALIDO" in extracted_text:
            raise ValueError("Erro de Validação: Campo crítico não encontrado ou inválido.")

        # 3. ESCRITA DOS RESULTADOS (Para o GCS de Saída)
        output_data = {"filename": file_name, "text": extracted_text, "pages": num_pages}
        output_blob = storage_client.bucket('seu-bucket-saida').blob(f"processed/{file_name}.json")
        output_blob.upload_from_string(
            data=json.dumps(output_data),
            content_type='application/json'
        )
        
        logger.info(f"Processamento concluído com sucesso. Dados salvos em 'seu-bucket-saida/processed/{file_name}.json'")

        # ----------------------------------------------------
        # SRE: SUCESSO E CÁLCULO FINAL DE LATÊNCIA
        # ----------------------------------------------------
        end_time = time.time()
        latency_seconds = end_time - start_time
        
        # Log que atua como Métrica (SLI): O Prometheus/Loki pode extrair esses dados
        logger.info(f"SLI_LATENCY_SUCCESS|{latency_seconds:.2f}|PAGES|{num_pages}")
        
        # Retorno de sucesso (necessário para que o Pub/Sub confirme a mensagem)
        return "OK" 

    except Exception as e:
        # ----------------------------------------------------
        # SRE: GESTÃO DE ERROS E ALERTA
        # ----------------------------------------------------
        end_time = time.time()
        latency_seconds = end_time - start_time
        
        error_type = type(e).__name__
        logger.error(f"SLI_LATENCY_FAILURE|{latency_seconds:.2f}|TYPE|{error_type}")
        logger.error(f"Falha ao processar o documento: {gcs_uri}. Erro: {e}")
        
        # SRE: Publicar a URI do PDF na DLQ (Dead Letter Queue) do Pub/Sub 
        # para investigação manual (Prática de "Blameless Postmortems")
        
        # É crucial re-levantar o erro (raise) para que o Cloud Function/PubSub
        # saiba que a mensagem DEVE ser re-entregue ou movida para a DLQ.
        raise