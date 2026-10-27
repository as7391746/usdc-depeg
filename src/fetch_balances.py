"""USDC balances of every address in the sample at two snapshot blocks.

Snapshots are the first block of 2023-03-03 (start of the placebo window)
and 2023-03-10 (start of the stress window); both are Fridays. Balances are
read with Multicall3.aggregate(), batching balanceOf() calls, ABI-encoded by
hand to avoid extra dependencies.
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from config import PROC, USDC
from rpc import eth_call

MULTICALL3 = "0xca11bde05977b3631167028862be2a173976ca11"
BATCH = 500
SNAPSHOTS = {"bal_0303": "2023-03-03", "bal_0310": "2023-03-10"}


def word(x):
    return format(x, "064x")


def encode_aggregate(addrs):
    n = len(addrs)
    target = USDC[2:].rjust(64, "0")
    head = [word(1 * 32)] + [word(n)] + [word(32 * n + 160 * i) for i in range(n)]
    body = []
    for a in addrs:
        calldata = "70a08231" + a[2:].rjust(64, "0")  # balanceOf(a), 36 bytes
        body.append(target + word(64) + word(36) + calldata.ljust(128, "0"))
    return "0x252dba42" + "".join(head) + "".join(body)


def decode_aggregate(res):
    h = res[2:]
    w = lambda off: int(h[off * 2:off * 2 + 64], 16)
    arr = w(32)
    n = w(arr)
    base = arr + 32
    return [w(base + w(base + 32 * i) + 32) for i in range(n)]


def balances(addrs, block):
    chunks = [addrs[i:i + BATCH] for i in range(0, len(addrs), BATCH)]
    with ThreadPoolExecutor(6) as ex:
        parts = ex.map(lambda c: decode_aggregate(eth_call(MULTICALL3, encode_aggregate(c), block)), chunks)
    return np.concatenate([np.array(p, dtype=float) for p in parts]) / 1e6


def main():
    t = pd.read_parquet(PROC / "transfers.parquet", columns=["from", "to", "block", "time"])
    addrs = sorted(set(t["from"]) | set(t["to"]))
    out = pd.DataFrame({"address": addrs})
    for col, day in SNAPSHOTS.items():
        block = int(t.loc[t["time"] >= pd.Timestamp(day, tz="UTC"), "block"].min())
        out[col] = balances(addrs, block)
        print(col, "block", block, f"total {out[col].sum():,.0f}", flush=True)
    out.to_parquet(PROC / "balances.parquet", index=False)


if __name__ == "__main__":
    # sanity check against a single direct balanceOf call
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        a = ["0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7", "0x0a59649758aa4d66e25f08dd01271e891fe52199"]
        print(balances(a, 16779844))
        print([int(eth_call(USDC, "0x70a08231" + x[2:].rjust(64, "0"), 16779844), 16) / 1e6 for x in a])
    else:
        main()
