# Who Ran on USDC? Wallet-Level Evidence from the March 2023 Stablecoin Depeg

Reconstructs every USDC transfer on Ethereum (Mar 1–20, 2023; 1.92M transfers,
493k addresses) directly from blockchain event logs and studies who exited
USDC during the SVB-induced depeg. Research note: `paper/usdc_depeg.pdf`.

## Main findings

- **Redemptions and flight to DAI:** During March 10–13, $5.2 billion of USDC
  was burned, while issuance nearly stopped over the weekend. MakerDAO's Peg
  Stability Module received $2.1 billion in net USDC inflows.
- **The run broadened participation:** On March 11, the number of daily senders
  rose roughly fourfold, while the top 100 senders' share of outgoing volume
  fell from about 85% to 48%.
- **Smaller wallets moved more:** During the stress window, 63% of wallets
  holding $1,000–$10,000 had net outflows of at least half their starting
  balance, versus 36% of wallets holding over $10 million. The corresponding
  rates were about 2–3% in a placebo window one week earlier.
- **The gap persists in the comparison across windows:** The increase in net
  outflow as a share of starting balance was 17.7 percentage points lower for
  the largest wallets than for the smallest group (difference-in-differences
  estimate, robust standard error: 3.3 percentage points).
- **Most smaller-wallet outflows came before the price trough:** Wallets in
  the $10,000–$10 million groups moved out roughly half their combined balance,
  mostly between 18:00 UTC on March 10 and noon on March 11. The evidence is
  consistent with large holders having better access to redemption at par,
  but that explanation remains a hypothesis.

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

## Caveats
Addresses ≠ investors; net outflow ≠ sale; sample conditions on activity in the window;
CEX hot-wallet labels are unverified Etherscan tags. See Section 5 of the note.
