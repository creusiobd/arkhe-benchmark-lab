FROM python:3.12-slim

WORKDIR /app

# Instala curl para healthchecks e dependências de sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python em camada cacheadas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia a aplicação, os motores analíticos e os runners do ecossistema ARKHÉ
COPY app.py arkhe_detector.py traditional_monitor.py coi_engine.py benchmark_runner.py report_generator.py ./

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=3s --timeout=2s --start-period=3s --retries=5 \
  CMD curl -f http://localhost:8080/telemetry/as_of || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
