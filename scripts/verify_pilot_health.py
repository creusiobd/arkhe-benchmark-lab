#!/usr/bin/env python3
"""
ARKHÉ Pilot Pre-Flight & Health Verification Tool
=================================================
Validates enterprise readiness, network connectivity, and OpenTelemetry
ingestion for ARKHÉ instances deployed in Design Partner environments.
"""

import sys
import os
import json
import time
import argparse

# Graceful console output encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"

def run_preflight_checks(base_url: str, client: httpx.Client = None):
    base_url = base_url.rstrip("/")
    print(f"\n{CYAN}{BOLD}================================================================================")
    print(f"      ARKHÉ DESIGN PARTNER PILOT — PRE-FLIGHT VERIFICATION TOOL")
    print(f"================================================================================{RESET}")
    print(f"Target Cluster Endpoint: {base_url}\n")
    
    passed_checks = 0
    total_checks = 4
    
    close_client = False
    if client is None:
        client = httpx.Client(base_url=base_url, timeout=5.0)
        close_client = True
    
    # Check 1: Healthcheck & Telemetry Endpoint
    print(f"1. Verificando API de Telemetria e Healthcheck ({base_url}/telemetry/as_of)... ", end="")
    try:
        r = client.get("/telemetry/as_of")
        if r.status_code == 200:
            data = r.json()
            occupancy = data.get("observables", {}).get("rho_pool", 0.0)
            print(f"{GREEN}[OK]{RESET} (Status 200, Ocupação atual: {occupancy*100:.1f}%)")
            passed_checks += 1
        else:
            print(f"{RED}[FALHA]{RESET} (Status code {r.status_code})")
    except Exception as e:
        print(f"{RED}[ERRO DE CONEXÃO]{RESET}: {e}")

    # Check 2: OpenTelemetry OTLP Trace Ingestion
    print(f"2. Validando Ingestão de Traces OTel ({base_url}/v1/traces)... ", end="")
    sample_trace = {
        "resourceSpans": [{
            "resource": {
                "attributes": [{"key": "service.name", "value": {"stringValue": "pilot-payment-gateway"}}]
            },
            "scopeSpans": [{
                "spans": [{
                    "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                    "spanId": "00f067aa0ba902b7",
                    "name": "authorize_payment",
                    "startTimeUnixNano": int((time.time() - 0.05) * 1e9),
                    "endTimeUnixNano": int(time.time() * 1e9),
                    "attributes": [
                        {"key": "queue.wait_ms", "value": {"doubleValue": 4.5}},
                        {"key": "service.time_ms", "value": {"doubleValue": 45.0}}
                    ]
                }]
            }]
        }]
    }
    try:
        r = client.post("/v1/traces", json=sample_trace)
        if r.status_code in [200, 202]:
            print(f"{GREEN}[OK]{RESET} (Status {r.status_code}, Ingestão de Spans confirmada)")
            passed_checks += 1
        else:
            print(f"{RED}[FALHA]{RESET} (Status code {r.status_code})")
    except Exception as e:
        print(f"{RED}[ERRO]{RESET}: {e}")

    # Check 3: Prometheus Metrics Exporter
    print(f"3. Validando Exporter Prometheus ({base_url}/metrics)... ", end="")
    try:
        r = client.get("/metrics")
        if r.status_code == 200 and "arkhe_pool_occupancy_ratio" in r.text:
            print(f"{GREEN}[OK]{RESET} (Métricas de Lyapunov ativas)")
            passed_checks += 1
        else:
            print(f"{RED}[FALHA]{RESET} (Métricas não encontradas no endpoint)")
    except Exception as e:
        print(f"{RED}[ERRO]{RESET}: {e}")

    # Check 4: Interactive Cockpit & Presentation
    print(f"4. Verificando Cockpit e Apresentação Executiva ({base_url}/presentation)... ", end="")
    try:
        r = client.get("/presentation")
        if r.status_code == 200:
            print(f"{GREEN}[OK]{RESET} (Pitch Deck e Cockpit carregados)")
            passed_checks += 1
        else:
            print(f"{RED}[FALHA]{RESET} (Status {r.status_code})")
    except Exception as e:
        print(f"{RED}[ERRO]{RESET}: {e}")

    # Summary
    print(f"\n{CYAN}--------------------------------------------------------------------------------{RESET}")
    if close_client:
        client.close()

    if passed_checks == total_checks:
        print(f"{GREEN}{BOLD}✓ SUCESSO: Todos os {total_checks}/{total_checks} testes de pré-voo foram aprovados!{RESET}")
        print(f"{CYAN}A instância ARKHÉ está 100% pronta para operação em Modo Shadow no cluster.{RESET}\n")
        return 0
    else:
        print(f"{YELLOW}{BOLD}⚠️ ATENÇÃO: Apenas {passed_checks}/{total_checks} verificações foram aprovadas.{RESET}\n")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARKHÉ Pilot Pre-flight Verification")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Base URL of ARKHÉ service")
    args = parser.parse_args()
    
    sys.exit(run_preflight_checks(args.url))
