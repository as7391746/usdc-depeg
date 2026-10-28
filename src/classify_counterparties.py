"""Rule-based on-chain classification of the main counterparties.

For the 400 addresses that received USDC from the most distinct sample
wallets during the placebo and stress windows, test whether the address is
an AMM pool that holds USDC:
  * Uniswap v2/v3-style (also Sushi, etc.): token0()/token1() include USDC
  * Curve-style: coins(0..3) include USDC
The other token's symbol() is recorded so swaps can be split by what USDC
was exchanged into. Addresses already in labels.csv are skipped.
"""
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from analysis import PLACEBO, STRESS, load
from config import PROC, USDC
from rpc import rpc

BLOCK = 16794062  # 2023-03-10 00:00 UTC
TOP_N = 400


def _call(to, data):
    # single attempt: reverts are expected for non-pools, so no retry loop
    import requests
    from config import RPC_URL
    r = requests.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                                     "params": [{"to": to, "data": data}, hex(BLOCK)]}, timeout=60).json()
    res = r.get("result")
    return res if res and len(res) >= 66 else None


def as_addr(res):
    return "0x" + res[-40:] if res else None


def symbol(token):
    res = _call(token, "0x95d89b41")
    if not res:
        return "?"
    h = res[2:]
    try:
        if len(h) == 64:  # bytes32 symbol (e.g. MKR)
            return bytes.fromhex(h).rstrip(b"\0").decode()
        n = int(h[64:128], 16)
        return bytes.fromhex(h[128:128 + 2 * n]).decode()
    except Exception:
        return "?"


def classify(addr):
    if len(rpc("eth_getCode", [addr, hex(BLOCK)])) <= 2:
        return {"address": addr, "kind": "eoa", "other_token": None}
    t0, t1 = as_addr(_call(addr, "0x0dfe1681")), as_addr(_call(addr, "0xd21220a7"))
    if USDC in (t0, t1):
        other = t1 if t0 == USDC else t0
        return {"address": addr, "kind": "amm_pool", "other_token": symbol(other)}
    coins = [as_addr(_call(addr, "0xc6610657" + format(i, "064x"))) for i in range(4)]
    if USDC in coins:
        others = [symbol(c) for c in coins if c and c != USDC]
        return {"address": addr, "kind": "curve_pool", "other_token": "/".join(others)}
    return {"address": addr, "kind": "other_contract", "other_token": None}


def main():
    t, lab, *_ = load()
    bal = pd.read_parquet(PROC / "balances.parquet")
    sample = set(bal.loc[(bal.bal_0303 >= 1000) & (bal.bal_0310 >= 1000), "address"])
    w = t[(((t.time >= PLACEBO[0]) & (t.time < PLACEBO[1])) | ((t.time >= STRESS[0]) & (t.time < STRESS[1])))
          & t["from"].isin(sample) & t.to_cat.isna()]
    top = w.groupby("to")["from"].nunique().sort_values(ascending=False).head(TOP_N)
    with ThreadPoolExecutor(8) as ex:
        out = pd.DataFrame(list(ex.map(classify, top.index)))
    out["n_senders"] = top.values
    out.to_csv(PROC / "counterparties.csv", index=False)
    print(out.kind.value_counts())
    print(out[out.kind != "eoa"].head(25).to_string(index=False))


if __name__ == "__main__":
    main()
