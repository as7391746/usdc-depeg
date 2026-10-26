"""Check protocol labels on-chain: each labeled contract must point to USDC.

Uniswap pools are checked via token0()/token1(); aTokens via
UNDERLYING_ASSET_ADDRESS(); cTokens via underlying(); Comet via baseToken();
Maker PSM join via gem(); Curve 3pool via coins(1). Exchange hot-wallet tags
cannot be verified on-chain; for those we only report whether code is deployed.
"""
import pandas as pd

from config import PROC, ROOT, USDC
from rpc import eth_call, rpc

BLOCK = 16779844  # 2023-03-08 00:00 UTC


def addr_from_word(word):
    return "0x" + word[-40:]


def main():
    lab = pd.read_csv(ROOT / "data" / "labels.csv", dtype=str).fillna("")
    out = []
    for _, r in lab.iterrows():
        code = rpc("eth_getCode", [r.address, hex(BLOCK)])
        is_contract = len(code) > 2
        status = "not checkable"
        if r.verify_selector:
            res = [addr_from_word(eth_call(r.address, r.verify_selector, BLOCK))]
            if r.verify_selector == "0x0dfe1681":  # also check token1
                res.append(addr_from_word(eth_call(r.address, "0xd21220a7", BLOCK)))
            status = "verified" if USDC in res else f"FAILED {res}"
        out.append({**r.to_dict(), "is_contract": is_contract, "status": status})
    out = pd.DataFrame(out).drop(columns="verify_selector")
    out.to_csv(PROC / "labels_verified.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
