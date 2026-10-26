"""Minimal JSON-RPC helpers with retries."""
import time

import requests

from config import RPC_URL

_session = requests.Session()


def rpc(method, params, tries=8):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    for k in range(tries):
        try:
            r = _session.post(RPC_URL, json=payload, timeout=90).json()
            if "result" in r:
                return r["result"]
        except Exception:
            pass
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{method} failed: {params}")


def eth_call(to, data, block="latest"):
    return rpc("eth_call", [{"to": to, "data": data}, block if isinstance(block, str) else hex(block)])
