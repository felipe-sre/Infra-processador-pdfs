FROM python:3.11-slim

WORKDIR /app

# Evita geração de arquivos .pyc e força saída instantânea de logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker_alert_bot.py .

CMD ["python", "-u", "docker_alert_bot.py"]