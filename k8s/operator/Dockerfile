FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV ARKHE_K8S_MOCK=false

USER 65534:65534
ENTRYPOINT ["python", "-m", "k8s.operator.main"]
