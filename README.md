# Who Ran on USDC? Wallet-Level Evidence from the March 2023 Stablecoin Depeg

Reconstructs every USDC transfer on Ethereum (Mar 1–20, 2023; 1.92M transfers,
493k addresses) directly from blockchain event logs and studies who exited
USDC during the SVB-induced depeg. Research note: `paper/usdc_depeg.pdf`.

## Data (all pulled from the chain via a public RPC, no API keys)
| Step | Script | Output |
|---|---|---|
| USDC `Transfer` logs, 1,423 × 100-block `eth_getLogs` calls | `fetch_transfers.py` | `data/raw/transfers/` |
| Merge + validation (mint − burn = Δ`totalSupply()`; venue net flow = Δ`balanceOf()`, exact to the cent) | `build_transfers.py` | `transfers.parquet` |
| Hourly Chainlink USDC/USD price | `fetch_price.py` | `price_hourly.csv` |
| Balances of all addresses at Mar 3 & Mar 10 (Multicall3, hand ABI-encoded) | `fetch_balances.py` | `balances.parquet` |
| EOA vs contract (`eth_getCode`) | `fetch_codes.py` | `codes.parquet` |
| Protocol labels verified on-chain (`token0()`, `gem()`, `underlying()` …) | `verify_labels.py` | `labels_verified.csv` |
| Rule-based AMM pool detection for top 400 counterparties | `classify_counterparties.py` | `counterparties.csv` |
| Figures, tables, DiD regressions | `analysis.py` | `output/` |

Run everything: `./run_all.sh`. Requires Python 3 with pandas, pyarrow,
requests, matplotlib, statsmodels; `pdflatex` for the note.

## Main findings
- $5.2bn burned during Mar 10–13; minting ~0 over the weekend; $2.1bn net inflow into the Maker PSM.
- Activity broadened: senders ×4 on Mar 11; top-100 sender share of volume fell from ~85% to 48%.
- Smaller holders ran more: 63% of $1k–10k wallets moved out ≥50% of balance vs 36% of $10m+ wallets
  (placebo window one week earlier: 2–3%). DiD coefficient for $10m+ vs $1k–10k: −0.18 (s.e. 0.03).

## Caveats
Addresses ≠ investors; net outflow ≠ sale; sample conditions on activity in the window;
CEX hot-wallet labels are unverified Etherscan tags. See Section 5 of the note.
