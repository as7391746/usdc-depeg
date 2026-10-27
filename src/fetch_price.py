"""Hourly Chainlink USDC/USD price, read via latestRoundData() at the first
block of each UTC hour (block numbers taken from the transfer data)."""
import pandas as pd

from config import CHAINLINK_USDC_USD, PROC
from rpc import eth_call


def main():
    t = pd.read_parquet(PROC / "transfers.parquet", columns=["block", "time"])
    t["hour"] = t["time"].dt.floor("h")
    hours = t.groupby("hour")["block"].min().reset_index()
    prices = []
    for b in hours["block"]:
        res = eth_call(CHAINLINK_USDC_USD, "0xfeaf968c", int(b))
        prices.append(int(res[66:130], 16) / 1e8)  # second word = answer
    hours["price"] = prices
    hours.to_csv(PROC / "price_hourly.csv", index=False)
    print(hours.loc[hours.price.idxmin()], len(hours))


if __name__ == "__main__":
    main()
