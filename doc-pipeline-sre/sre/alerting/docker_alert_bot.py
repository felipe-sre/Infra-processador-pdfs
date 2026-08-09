import os
import sys
import logging
import json
import requests
import docker

# Configuração de Logging Operacional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] SRE-ALERT-BOT: %(message)s'
)
logger = logging.getLogger(__name__)

# Leitura da URL do Webhook do Slack via Variável de Ambiente
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def send_slack_alert(container_name, event_action, exit_code=None):
    """
    Envia uma notificação formatada para o canal do Slack via Webhook.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL não configurada. Alerta impresso apenas no log.")
        return

    payload = {
        "text": f"🚨 *[SRE ALERTA] Falha de Contêiner Detectada*",
        "attachments": [
            {
                "color": "#FF0000",
                "fields": [
                    {"title": "Contêiner", "value": f"`{container_name}`", "short": True},
                    {"title": "Evento", "value": f"`{event_action}`", "short": True},
                    {"title": "Exit Code", "value": f"`{exit_code if exit_code else 'N/A'}`", "short": True},
                    {"title": "Ambiente", "value": "`Local/Docker`", "short": True}
                ],
                "footer": "SRE Docker Alert Bot",
                "ts": int(os.environ.get("EXEC_TIME", 0))
            }
        ]
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        if response.status_code == 200:
            logger.info(f"Alerta do contêiner '{container_name}' enviado ao Slack com sucesso.")
        else:
            logger.error(f"Erro ao enviar alerta ao Slack. Status: {response.status_code}, Resposta: {response.text}")
    except Exception as e:
        logger.error(f"Exceção ao tentar se comunicar com o Slack: {e}")

def monitor_docker_events():
    """
    Escuta os eventos do Docker Socket em tempo real e dispara alertas em falhas.
    """
    try:
        client = docker.from_env()
        logger.info("Conectado ao Docker Socket. Monitorando eventos de contêineres...")
        
        # Filtra eventos de parada, morte e estouro de memória (OOM)
        for event in client.events(decode=True, filters={"type": "container"}):
            action = event.get('action')
            
            if action in ['die', 'kill', 'oom']:
                container_name = event.get('Actor', {}).get('Attributes', {}).get('name', 'Desconhecido')
                exit_code = event.get('Actor', {}).get('Attributes', {}).get('exitCode', 'N/A')
                
                # Ignora a saída normal (exit code 0)
                if str(exit_code) != '0':
                    logger.error(f"Evento crítico detectado! Contêiner: {container_name} | Ação: {action} | ExitCode: {exit_code}")
                    send_slack_alert(container_name, action, exit_code)

    except docker.errors.DockerException as e:
        logger.critical(f"Não foi possível conectar ao Docker Socket: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Erro inesperado no bot de monitoramento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    monitor_docker_events()