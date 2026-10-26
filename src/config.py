"""Shared constants for the USDC depeg project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
TAB = ROOT / "output" / "tables"

RPC_URL = "https://eth.drpc.org"

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x0000000000000000000000000000000000000000"
USDC_DECIMALS = 6

# Sample window: 2023-03-01 00:00 UTC to 2023-03-21 00:00 UTC (exclusive).
# Block numbers found by binary search on block timestamps.
START_BLOCK = 16730072
END_BLOCK = 16872312  # inclusive (last block before 2023-03-21 00:00 UTC)
CHUNK = 100           # free-tier eth_getLogs range limit

# Chainlink USDC/USD price feed (proxy)
CHAINLINK_USDC_USD = "0x8fffffd4afb6115b954bd326cbe7b4ba576818f6"

# Period definitions (UTC dates)
PRE = ("2023-03-01", "2023-03-07")     # baseline, before SVB news
STRESS = ("2023-03-10", "2023-03-13")  # SVB failure -> repeg
POST = ("2023-03-14", "2023-03-20")
