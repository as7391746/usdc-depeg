"""Combine raw shards into one transfer table and validate completeness.

Validation: the change in USDC totalSupply() between the first and last block
must equal mints minus burns in the data, and the change in each verified
protocol contract's balanceOf() must equal its net inflow. Both are exact
integer identities, so any missing chunk would show up as a discrepancy.
"""
import pandas as pd

from config import END_BLOCK, PROC, RAW, START_BLOCK, USDC, ZERO
from rpc import eth_call


def total_supply(block):
    return int(eth_call(USDC, "0x18160ddd", block), 16)


def balance_of(addr, block):
    return int(eth_call(USDC, "0x70a08231" + addr[2:].rjust(64, "0"), block), 16)


def main():
    df = pd.concat([pd.read_parquet(p) for p in sorted((RAW / "transfers").glob("*.parquet"))])
    df = df.drop_duplicates(["tx_hash", "log_index"]).sort_values(["block", "log_index"])
    df["value_int"] = df["value_raw"].apply(int)
    df["usdc"] = df["value_int"] / 1e6
    df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    assert df.block.min() >= START_BLOCK and df.block.max() <= END_BLOCK

    mint = df.loc[df["from"] == ZERO, "value_int"].sum()
    burn = df.loc[df["to"] == ZERO, "value_int"].sum()
    d_supply = total_supply(END_BLOCK) - total_supply(START_BLOCK - 1)
    print(f"transfers: {len(df):,}  blocks: {df.block.nunique():,}")
    print(f"mint - burn = {(mint - burn)/1e6:,.2f}   d(totalSupply) = {d_supply/1e6:,.2f}   match={mint - burn == d_supply}")

    labels = pd.read_csv(PROC / "labels_verified.csv")
    for a, name in labels.loc[labels.status == "verified", ["address", "name"]].values:
        net = df.loc[df["to"] == a, "value_int"].sum() - df.loc[df["from"] == a, "value_int"].sum()
        d_bal = balance_of(a, END_BLOCK) - balance_of(a, START_BLOCK - 1)
        print(f"  {name:32s} net inflow {net/1e6:>16,.0f}  d(balance) {d_bal/1e6:>16,.0f}  match={net == d_bal}")

    df.drop(columns=["value_raw", "value_int"]).to_parquet(PROC / "transfers.parquet", index=False)


if __name__ == "__main__":
    main()
