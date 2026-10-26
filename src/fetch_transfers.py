"""Download every USDC Transfer event on Ethereum in the sample window.

Uses eth_getLogs on a public RPC in 100-block chunks. Each chunk is written
to its own parquet shard so the download can be resumed after interruption.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from config import CHUNK, END_BLOCK, RAW, RPC_URL, START_BLOCK, TRANSFER_TOPIC, USDC

OUT = RAW / "transfers"
OUT.mkdir(parents=True, exist_ok=True)
session = requests.Session()


def get_logs(lo, hi, tries=8):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs",
               "params": [{"address": USDC, "topics": [TRANSFER_TOPIC],
                           "fromBlock": hex(lo), "toBlock": hex(hi)}]}
    for k in range(tries):
        try:
            r = session.post(RPC_URL, json=payload, timeout=90).json()
            if "result" in r:
                return r["result"]
        except Exception:
            pass
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"failed {lo}-{hi}")


def fetch_chunk(lo):
    hi = min(lo + CHUNK - 1, END_BLOCK)
    path = OUT / f"{lo}.parquet"
    if path.exists():
        return 0
    logs = get_logs(lo, hi)
    df = pd.DataFrame({
        "block": [int(l["blockNumber"], 16) for l in logs],
        "ts": [int(l["blockTimestamp"], 16) for l in logs],
        "tx_hash": [l["transactionHash"] for l in logs],
        "log_index": [int(l["logIndex"], 16) for l in logs],
        "from": ["0x" + l["topics"][1][-40:] for l in logs],
        "to": ["0x" + l["topics"][2][-40:] for l in logs],
        # raw integer amount (6 decimals) kept as string to avoid overflow
        "value_raw": [str(int(l["data"], 16)) for l in logs],
    })
    df.to_parquet(path, index=False)
    return len(df)


def main(workers=6):
    starts = list(range(START_BLOCK, END_BLOCK + 1, CHUNK))
    done, n = 0, 0
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(fetch_chunk, s) for s in starts]
        for f in as_completed(futs):
            n += f.result()
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(starts)} chunks, {n:,} new logs", flush=True)
    print("finished", done, "chunks")


if __name__ == "__main__":
    main()
