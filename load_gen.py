import asyncio
import os
import random
import sys
import time
from typing import Optional
import httpx

TARGET_URL = os.getenv("TARGET_URL", "http://localhost:8080/v1/charge")
TARGET_TPS = float(os.getenv("TARGET_TPS", "80.0"))
INTERVAL = 1.0 / TARGET_TPS

async def send_charge_attempt(client: httpx.AsyncClient, tx_id: str, attempt_num: int):
    headers = {
        "x-transaction-id": tx_id,
        "x-attempt-id": f"{tx_id}_{attempt_num}"
    }
    payload = {
        "card_token": f"tok_{random.randint(1000, 9999)}_4242",
        "amount_cents": random.choice([4900, 12000, 18900, 35000])
    }
    
    try:
        res = await client.post(TARGET_URL, json=payload, headers=headers, timeout=2.0)
        # Se sofrer timeout ou saturação, o cliente executa retry imediato (Efeito Cascata)
        if res.status_code in (503, 504) and attempt_num < 3:
            await asyncio.sleep(0.150 * attempt_num)  # Backoff curto e agressivo de checkout
            await send_charge_attempt(client, tx_id, attempt_num + 1)
    except (httpx.TimeoutException, httpx.NetworkError):
        if attempt_num < 3:
            await asyncio.sleep(0.150 * attempt_num)
            await send_charge_attempt(client, tx_id, attempt_num + 1)
    except Exception:
        pass

async def worker(queue: asyncio.Queue, client: httpx.AsyncClient):
    while True:
        tx_id = await queue.get()
        asyncio.create_task(send_charge_attempt(client, tx_id, 1))
        queue.task_done()

async def run_load(duration_seconds: Optional[float] = None):
    queue = asyncio.Queue()
    limits = httpx.Limits(max_keepalive_connections=200, max_connections=500)
    async with httpx.AsyncClient(limits=limits) as client:
        workers = [asyncio.create_task(worker(queue, client)) for _ in range(50)]
        print(f"[*] Gerador de carga ativo em {TARGET_URL} @ {TARGET_TPS} TPS nominais...")
        counter = 0
        start_t = time.time()
        try:
            while True:
                if duration_seconds and (time.time() - start_t) >= duration_seconds:
                    break
                t0 = time.perf_counter()
                tx_id = f"tx_{int(time.time())}_{counter}"
                await queue.put(tx_id)
                counter += 1
                
                elapsed = time.perf_counter() - t0
                sleep_time = max(0.0, INTERVAL - elapsed)
                await asyncio.sleep(sleep_time)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            print("[*] Encerrando emissão de carga.")
            for w in workers:
                w.cancel()

if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else None
    try:
        asyncio.run(run_load(dur))
    except KeyboardInterrupt:
        pass
