import json
import os
import time
import logging
import boto3
from pypdf import PdfReader

# Configuração de Logging para Observabilidade
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização dos clientes AWS fora do handler (Reaproveitamento de conexão)
s3_client = boto3.client('s3')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')

def lambda_handler(event, context):
    """
    Handler principal acionado pelo gatilho do Amazon SQS.
    """
    start_time = time.time()
    
    try:
        # 1. Leitura do evento SQS
        for record in event.get('Records', []):
            body = json.loads(record['body'])
            
            # Suporta se a mensagem for um evento direto do S3 ou um JSON customizado
            s3_bucket = body.get('bucket', body.get('s3_bucket'))
            s3_key = body.get('key', body.get('s3_key'))
            
            if not s3_bucket or not s3_key:
                raise ValueError("Payload inválido: 'bucket' e 'key' são obrigatórios.")

            logger.info(f"Iniciando processamento: s3://{s3_bucket}/{s3_key}")
            
            # 2. Download do PDF para o armazenamento temporário (/tmp/) da Lambda
            local_filename = os.path.basename(s3_key)
            local_pdf_path = f"/tmp/{local_filename}"
            
            s3_client.download_file(s3_bucket, s3_key, local_pdf_path)
            
            # 3. Extração e Processamento
            reader = PdfReader(local_pdf_path)
            num_pages = len(reader.pages)
            extracted_text = ""
            
            for page in reader.pages:
                extracted_text += page.extract_text() or ""
            
            # Simulação de regra de negócio
            if "VALOR_INVALIDO" in extracted_text:
                raise ValueError("Erro de Validação: Documento contém dados inválidos.")

            # 4. Upload do resultado JSON para o Bucket S3 de Saída
            output_data = {
                "filename": local_filename,
                "text": extracted_text,
                "pages": num_pages,
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            output_key = f"processed/{os.path.splitext(local_filename)[0]}.json"
            
            s3_client.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=json.dumps(output_data),
                ContentType='application/json'
            )
            
            # Limpeza do arquivo local temporário
            if os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)

            # Métricas SLI gravadas nos logs para captura do CloudWatch/Prometheus
            latency_seconds = time.time() - start_time
            logger.info(f"SLI_LATENCY_SUCCESS|{latency_seconds:.2f}|PAGES|{num_pages}")

        return {"statusCode": 200, "body": "Processamento concluído com sucesso."}

    except Exception as e:
        latency_seconds = time.time() - start_time
        error_type = type(e).__name__
        logger.error(f"SLI_LATENCY_FAILURE|{latency_seconds:.2f}|TYPE|{error_type}")
        logger.error(f"Falha ao processar arquivo: {str(e)}")
        raise e