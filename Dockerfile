# Multi-stage production Dockerfile for ARKHÉ Cybernetic Platform
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime image (Distroless-like minimal footprint)
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck & clean package cache
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed wheels from builder to /usr/local for system-wide non-root access
COPY --from=builder /install /usr/local

# Create non-root user for security (K8s restricted pod security standard)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Copy application code and modules
COPY --chown=appuser:appgroup app.py arkhe_detector.py traditional_monitor.py coi_engine.py benchmark_runner.py report_generator.py run_interactive_pov.py ./
COPY --chown=appuser:appgroup contracts/ ./contracts/
COPY --chown=appuser:appgroup detectors/ ./detectors/
COPY --chown=appuser:appgroup evaluator/ ./evaluator/
COPY --chown=appuser:appgroup otel/ ./otel/
COPY --chown=appuser:appgroup k8s/ ./k8s/
COPY --chown=appuser:appgroup ci/ ./ci/
COPY --chown=appuser:appgroup templates/ ./templates/
COPY --chown=appuser:appgroup static/ ./static/
COPY --chown=appuser:appgroup arkhe_pitch_deck_presentation.html ./arkhe_pitch_deck_presentation.html
COPY --chown=appuser:appgroup arkhe_pov_executive_summary.html ./arkhe_pov_executive_summary.html

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/telemetry/as_of || exit 1

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
