"""Classify sample addresses as EOA vs contract (eth_getCode at 2023-03-03)."""
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from config import PROC
from rpc import rpc

BLOCK = hex(16744289)


def is_contract(addr):
    return len(rpc("eth_getCode", [addr, BLOCK])) > 2


def main():
    b = pd.read_parquet(PROC / "balances.parquet")
    addrs = b.loc[(b.bal_0303 >= 1000) & (b.bal_0310 >= 1000), "address"].tolist()
    with ThreadPoolExecutor(10) as ex:
        flags = list(ex.map(is_contract, addrs))
    out = pd.DataFrame({"address": addrs, "is_contract": flags})
    out.to_parquet(PROC / "codes.parquet", index=False)
    print(out.is_contract.value_counts())


if __name__ == "__main__":
    main()
