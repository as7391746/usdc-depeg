#!/bin/sh
# Full pipeline: raw RPC data -> validated tables -> figures -> PDF (~30 min on a free RPC).
set -e
cd "$(dirname "$0")/src"
python3 fetch_transfers.py          # USDC Transfer logs, Mar 1-20 2023
python3 verify_labels.py            # on-chain check of protocol labels
python3 build_transfers.py          # merge + exact supply/balance reconciliation
python3 fetch_price.py              # hourly Chainlink USDC/USD
python3 fetch_balances.py           # balances at Mar 3 / Mar 10 via Multicall3
python3 fetch_codes.py              # EOA vs contract
python3 classify_counterparties.py  # rule-based AMM pool detection
python3 analysis.py                 # figures + tables
cd ../paper && pdflatex -interaction=nonstopmode usdc_depeg.tex >/dev/null && pdflatex -interaction=nonstopmode usdc_depeg.tex >/dev/null
