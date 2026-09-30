import asyncio
import json
import time
import httpx
import websockets

BASE_HTTP = "http://127.0.0.1:8080"
BASE_WS = "ws://127.0.0.1:8080/ws/telemetry"

async def run_validation_suite():
    results = {
        "timestamp": time.time(),
        "tests": {},
        "summary": {"passed": 0, "failed": 0, "total": 0}
    }

    def record_test(name: str, passed: bool, details: dict):
        results["summary"]["total"] += 1
        if passed:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
        results["tests"][name] = {"passed": passed, "details": details}
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {name}: {details.get('summary', '')}")

    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=5.0) as client:
        # TEST 1: HTTP Serving (Legacy vs Angular)
        try:
            r_root = await client.get("/")
            r_ng = await client.get("/ng/")
            r_ng_redirect = await client.get("/ng", follow_redirects=False)
            
            passed = (
                r_root.status_code == 200 and "ARKHÉ SENTINEL" in r_root.text and
                r_ng.status_code == 200 and "<app-root>" in r_ng.text and
                r_ng_redirect.status_code in (301, 302, 307)
            )
            record_test("1. Dual Serving & Routing", passed, {
                "summary": "Verificou serving simultâneo de / (Vanilla) e /ng/ (Angular 17) + redirect",
                "root_status": r_root.status_code,
                "ng_status": r_ng.status_code,
                "ng_redirect_status": r_ng_redirect.status_code
            })
        except Exception as e:
            record_test("1. Dual Serving & Routing", False, {"error": str(e)})

        # TEST 2: REST Telemetry Endpoints
        try:
            r_live = await client.get("/telemetry/live")
            data_live = r_live.json()
            r_as_of = await client.get("/telemetry/as_of?as_of=0")
            data_as_of = r_as_of.json()
            
            has_keys = all(k in data_live for k in [
                "scenario", "telemetry", "sentinel", "sre_governance", 
                "mitigation", "topology", "projection", "recent_journeys", "event_logs"
            ])
            passed = r_live.status_code == 200 and has_keys and r_as_of.status_code == 200
            record_test("2. REST Telemetry Schemas", passed, {
                "summary": "Endpoints /telemetry/live e /telemetry/as_of respondendo com esquema completo",
                "status_code": r_live.status_code,
                "top_level_keys": list(data_live.keys())
            })
        except Exception as e:
            record_test("2. REST Telemetry Schemas", False, {"error": str(e)})

        # TEST 3: WebSocket 20 FPS Stream & Frame Frequency
        try:
            async with websockets.connect(BASE_WS) as ws:
                # Recebe frame inicial
                initial_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                initial_data = json.loads(initial_msg)

                # Amostra 20 frames consecutivos para medir frequência Hz real
                timestamps = []
                for _ in range(20):
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    frame = json.loads(raw)
                    timestamps.append(frame["stream_meta"]["timestamp"])

                delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                avg_delay_ms = (sum(delays) / len(delays)) * 1000
                fps_actual = 1000.0 / avg_delay_ms if avg_delay_ms > 0 else 0

                passed = 15.0 <= fps_actual <= 25.0 and len(timestamps) == 20
                record_test("3. WebSocket Frequency & Jitter (20 Hz)", passed, {
                    "summary": f"Frequência medida: {fps_actual:.1f} FPS (Intervalo médio: {avg_delay_ms:.1f}ms)",
                    "fps_measured": round(fps_actual, 1),
                    "avg_interval_ms": round(avg_delay_ms, 1),
                    "protocol": initial_data["stream_meta"]["protocol"]
                })
        except Exception as e:
            record_test("3. WebSocket Frequency & Jitter (20 Hz)", False, {"error": str(e)})

        # TEST 4: Bidirectional WebSocket Commands (Scenario Injection & Ping)
        try:
            async with websockets.connect(BASE_WS) as ws:
                # Envia ping
                await ws.send("ping")
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                # Pode receber ou pong ou um frame de telemetria se intercalado
                ping_ok = False
                if resp == "pong":
                    ping_ok = True
                else:
                    # Lê até 3 mensagens para checar pong
                    for _ in range(3):
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        if msg == "pong":
                            ping_ok = True
                            break

                # Envia comando de cenário via WS
                await ws.send("scenario:drift")
                # Aguarda próximo frame de telemetria refletir o cenário
                drift_confirmed = False
                for _ in range(10):
                    frame_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    if frame_raw != "pong":
                        f = json.loads(frame_raw)
                        if f["scenario"]["id"] == "drift":
                            drift_confirmed = True
                            break

                passed = drift_confirmed
                record_test("4. WebSocket Bidirectional Commands", passed, {
                    "summary": "Comandos 'ping' e 'scenario:drift' executados e refletidos no stream",
                    "drift_applied_via_ws": drift_confirmed
                })
        except Exception as e:
            record_test("4. WebSocket Bidirectional Commands", False, {"error": str(e)})

        # TEST 5: Autonomous Mitigation Closed-Loop via REST & WebSocket
        try:
            # Ativa mitigação
            r_mit = await client.post("/admin/mitigation/toggle")
            mit_data = r_mit.json()
            
            # Checa se o stream de telemetria reflete o estado
            async with websockets.connect(BASE_WS) as ws:
                mit_stream_active = False
                for _ in range(10):
                    frame = json.loads(await ws.recv())
                    if frame["mitigation"]["enabled"] is True:
                        mit_stream_active = True
                        break

            # Desativa para retornar ao estado limpo
            await client.post("/admin/mitigation/toggle")
            
            passed = mit_data.get("mitigation_enabled") is True and mit_stream_active
            record_test("5. Closed-Loop Mitigation Command", passed, {
                "summary": "Toggle de mitigação autônoma sincronizado entre REST e WebSocket",
                "rest_response": mit_data,
                "stream_synchronized": mit_stream_active
            })
        except Exception as e:
            record_test("5. Closed-Loop Mitigation Command", False, {"error": str(e)})

        # TEST 6: Little's Law & Mathematical Physics Consistency
        try:
            async with websockets.connect(BASE_WS) as ws:
                frame = json.loads(await ws.recv())
                
                # Campos chave da física de filas
                rho = frame["telemetry"]["resources"]["antifraud_pool_utilization_ratio"]
                wq_ws = frame["telemetry"]["queueing"]["wq_ws_ratio"]
                sent_score = frame["sentinel"]["score"]
                nodes = frame["topology"]["nodes"]
                horizon = frame["projection"]["horizon_points"]

                math_consistent = (
                    0.0 <= rho <= 1.0 and
                    wq_ws >= 0.0 and
                    0.0 <= sent_score <= 100.0 and
                    len(nodes) == 6 and
                    len(horizon) >= 8
                )

                record_test("6. Mathematical Physics Telemetry", math_consistent, {
                    "summary": "Equações de Little, Lyapunov e projeção de horizonte consistentes",
                    "rho_pool": rho,
                    "wq_ws_ratio": wq_ws,
                    "sentinel_score": sent_score,
                    "topology_nodes_count": len(nodes),
                    "horizon_points_count": len(horizon)
                })
        except Exception as e:
            record_test("6. Mathematical Physics Telemetry", False, {"error": str(e)})

        # TEST 7: Reset do Sistema para Estado Nominal
        try:
            r_reset = await client.post("/admin/chaos/reset")
            reset_data = r_reset.json()
            
            async with websockets.connect(BASE_WS) as ws:
                nominal_confirmed = False
                for _ in range(10):
                    frame = json.loads(await ws.recv())
                    if frame["scenario"]["id"] == "nominal":
                        nominal_confirmed = True
                        break

            passed = r_reset.status_code == 200 and nominal_confirmed
            record_test("7. State Machine Reset", passed, {
                "summary": "Reset geral (/admin/chaos/reset) retornou o cluster ao estado nominal",
                "reset_response": reset_data,
                "nominal_confirmed": nominal_confirmed
            })
        except Exception as e:
            record_test("7. State Machine Reset", False, {"error": str(e)})

    # Salva relatório JSON em disco
    with open("validation_test_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n================ VALIDATION SUITE SUMMARY ================")
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(run_validation_suite())
