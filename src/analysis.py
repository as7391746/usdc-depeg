"""Figures and tables for the USDC depeg note.

Inputs (data/processed): transfers.parquet, price_hourly.csv, balances.parquet,
codes.parquet, labels_verified.csv.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import FIG, PROC, TAB, ZERO

# Palette: categorical slots for venues, one-hue blue ramp for ordered size groups
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.6, "legend.frameon": False, "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

STRESS = (pd.Timestamp("2023-03-10", tz="UTC"), pd.Timestamp("2023-03-14", tz="UTC"))
PLACEBO = (pd.Timestamp("2023-03-03", tz="UTC"), pd.Timestamp("2023-03-07", tz="UTC"))
BACKSTOP = pd.Timestamp("2023-03-12 22:15", tz="UTC")  # Fed/Treasury/FDIC joint statement
SIZE_BINS = [1e3, 1e4, 1e5, 1e6, 1e7, np.inf]
SIZE_LABELS = ["$1k-10k", "$10k-100k", "$100k-1m", "$1m-10m", "$10m+"]
VENUES = {"maker_psm": "Maker PSM", "curve_3pool": "Curve 3pool", "uniswap": "Uniswap pools",
          "lending": "Aave/Compound", "cex": "Labeled CEX wallets"}
SWAP = ["maker_psm", "curve_3pool", "uniswap", "pool_stable", "pool_volatile"]  # USDC sold into a pool/PSM


def load():
    t = pd.read_parquet(PROC / "transfers.parquet")
    lab = pd.read_csv(PROC / "labels_verified.csv")
    cat = dict(zip(lab.address, lab.category))
    cp = pd.read_csv(PROC / "counterparties.csv")
    pools = cp[cp.kind.isin(["amm_pool", "curve_pool"])]
    STABLE = {"USDT", "DAI", "FRAX", "LUSD", "TUSD", "BUSD", "USDP", "GUSD"}
    for a, tok in pools[["address", "other_token"]].values:
        cat.setdefault(a, "pool_stable" if tok in STABLE else "pool_volatile")
    for a in cp.loc[cp.kind == "other_contract", "address"]:
        cat.setdefault(a, "other_contract")
    t["from_cat"] = t["from"].map(cat)
    t["to_cat"] = t["to"].map(cat)
    t["hour"] = t["time"].dt.floor("h")
    t["day"] = t["time"].dt.floor("D")
    price = pd.read_csv(PROC / "price_hourly.csv", parse_dates=["hour"])
    bal = pd.read_parquet(PROC / "balances.parquet")
    codes = pd.read_parquet(PROC / "codes.parquet")
    return t, lab, price, bal, codes


def shade(ax):
    ax.axvspan(*STRESS, color="#f2efe6", zorder=0, lw=0)
    ax.axvline(BACKSTOP, color=MUTED, lw=0.8, ls="--")
    ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 4, 7, 10, 13, 16, 19]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))


# ---------------------------------------------------------------- Figure 1
def fig_price_volume(t, price):
    vol = t[(t["from"] != ZERO) & (t["to"] != ZERO)].groupby("hour")["usdc"].sum() / 1e9
    fig, ax = plt.subplots(2, 1, figsize=(6.5, 4.2), sharex=True, height_ratios=[1, 1])
    ax[0].plot(price.hour, price.price, color=CAT[0])
    ax[0].set_ylabel("Chainlink USDC/USD")
    ax[0].axhline(1, color=MUTED, lw=0.6)
    lo = price.loc[price.price.idxmin()]
    ax[0].annotate(f"low {lo.price:.3f}\n{lo.hour:%b %d %H:00} UTC", (lo.hour, lo.price),
                   xytext=(-8, 6), textcoords="offset points", color=INK, fontsize=8, va="bottom", ha="right")
    ax[1].bar(vol.index, vol.values, width=1 / 24, color=CAT[0], lw=0)
    ax[1].set_ylabel("Transfer volume\n($bn per hour)")
    for a in ax:
        shade(a)
    ax[0].text(BACKSTOP, 0.06, " Fed/Treasury/FDIC\n backstop (Mar 12 22:15)", color=MUTED, fontsize=7, va="bottom",
               transform=ax[0].get_xaxis_transform())
    fig.savefig(FIG / "fig1_price_volume.png")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2
def fig_mint_burn(t):
    mint = t[t["from"] == ZERO].groupby("day")["usdc"].sum() / 1e9
    burn = t[t["to"] == ZERO].groupby("day")["usdc"].sum() / 1e9
    d = pd.DataFrame({"mint": mint, "burn": burn}).fillna(0)
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    ax.bar(d.index, d["mint"], width=0.8, color=CAT[0], label="Minted (issuance)", lw=0)
    ax.bar(d.index, -d["burn"], width=0.8, color=CAT[1], label="Burned (redemption)", lw=0)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_ylabel("$bn per day")
    shade(ax)
    ax.legend(loc="lower left", fontsize=8)
    fig.savefig(FIG / "fig2_mint_burn.png")
    plt.close(fig)
    return d


# ---------------------------------------------------------------- Figure 3
def venue_netflow(t, freq):
    rows = []
    for c in VENUES:
        inn = t[t.to_cat == c].groupby(freq)["usdc"].sum()
        out = t[t.from_cat == c].groupby(freq)["usdc"].sum()
        rows.append((inn.sub(out, fill_value=0)).rename(c))
    return pd.concat(rows, axis=1).fillna(0)


def fig_venues(t):
    h = venue_netflow(t, "hour").cumsum() / 1e9
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    for i, (c, name) in enumerate(VENUES.items()):
        ax.plot(h.index, h[c], color=CAT[i], label=name)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_ylabel("Cumulative net USDC inflow\nsince Mar 1 ($bn)")
    shade(ax)
    ax.legend(loc="upper left", fontsize=7)
    fig.savefig(FIG / "fig3_venue_flows.png")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 4
def concentration(t):
    w = t[t.from_cat.isna() & (t["from"] != ZERO)]
    out = []
    for day, g in w.groupby("day"):
        s = g.groupby("from")["usdc"].sum().sort_values(ascending=False)
        tot = s.sum()
        k = max(1, int(np.ceil(0.01 * len(s))))
        out.append({"day": day, "senders": len(s), "volume_bn": tot / 1e9,
                    "top10": s.iloc[:10].sum() / tot, "top100": s.iloc[:100].sum() / tot,
                    "top1pct": s.iloc[:k].sum() / tot})
    c = pd.DataFrame(out).set_index("day")
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    for i, (col, name) in enumerate([("top10", "Top 10 senders"), ("top100", "Top 100 senders"),
                                     ("top1pct", "Top 1% of senders")]):
        ax.plot(c.index, c[col], color=CAT[i], marker="o", ms=3, label=name)
    ax.set_ylabel("Share of daily outgoing\nvolume (unlabeled addresses)")
    ax.set_ylim(0, 1)
    shade(ax)
    ax.legend(loc="lower left", fontsize=7, ncol=3)
    fig.savefig(FIG / "fig4_concentration.png")
    plt.close(fig)
    return c


# ---------------------------------------------------------------- wallet sample
def wallet_flows(t, start, end, sample):
    w = t[(t.time >= start) & (t.time < end)]
    out = w.groupby("from")["usdc"].sum()
    inn = w.groupby("to")["usdc"].sum()
    exit_out = w[w.to_cat.isin(SWAP)].groupby("from")["usdc"].sum()
    f = pd.DataFrame(index=sample)
    f["outflow"] = out.reindex(sample).fillna(0)
    f["inflow"] = inn.reindex(sample).fillna(0)
    f["exit_out"] = exit_out.reindex(sample).fillna(0)
    return f


def build_wallets(t, lab, bal, codes):
    s = bal.merge(codes, on="address")
    s = s[~s.address.isin(lab.address)]
    s["size"] = pd.cut(s.bal_0303, SIZE_BINS, labels=SIZE_LABELS, right=False)
    rows = []
    for name, (a, b), balcol in [("placebo", PLACEBO, "bal_0303"), ("stress", STRESS, "bal_0310")]:
        f = wallet_flows(t, a, b, s.address.values)
        base = s.set_index("address")[balcol]
        f["net_out_share"] = ((f.outflow - f.inflow) / base).clip(lower=-1)
        f["exit_share"] = (f.exit_out / base).clip(upper=1)
        f["ran"] = (f.net_out_share >= 0.5).astype(int)
        f["window"] = name
        rows.append(f.reset_index(names="address"))
    p = pd.concat(rows).merge(s[["address", "size", "is_contract", "bal_0303"]], on="address")
    return s, p


def regressions(p):
    wide = p.pivot(index="address", columns="window", values=["net_out_share", "exit_share", "ran"])
    d = pd.DataFrame({k: wide[(k, "stress")] - wide[(k, "placebo")]
                      for k in ["net_out_share", "exit_share", "ran"]})
    meta = p.drop_duplicates("address").set_index("address")[["size", "is_contract"]]
    d = d.join(meta)
    d["size"] = d["size"].astype(str)
    d["contract"] = d.is_contract.astype(int)
    fits = {}
    for y in ["net_out_share", "exit_share", "ran"]:
        f = f"{y} ~ C(size, Treatment('$1k-10k'))"
        fits[(y, "all")] = smf.ols(f + " + contract", d).fit(cov_type="HC1")
        fits[(y, "eoa")] = smf.ols(f, d[d.contract == 0]).fit(cov_type="HC1")
    return d, fits


def reg_table(fits, d):
    order = SIZE_LABELS[1:]
    cols = [("net_out_share", "all"), ("net_out_share", "eoa"), ("exit_share", "all"),
            ("exit_share", "eoa"), ("ran", "all"), ("ran", "eoa")]
    lines = []
    for lvl in order:
        term = f"C(size, Treatment('$1k-10k'))[T.{lvl}]"
        b = [fits[c].params[term] for c in cols]
        se = [fits[c].bse[term] for c in cols]
        pv = [fits[c].pvalues[term] for c in cols]
        star = lambda q: "***" if q < .01 else "**" if q < .05 else "*" if q < .1 else ""
        lines.append(lvl.replace("$", r"\$") + " & " + " & ".join(f"{x:.3f}{star(q)}" for x, q in zip(b, pv)) + r" \\")
        lines.append(" & " + " & ".join(f"({x:.3f})" for x in se) + r" \\")
    lines.append(r"\midrule")
    lines.append("Constant (\\$1k-10k) & " + " & ".join(f"{fits[c].params['Intercept']:.3f}" for c in cols) + r" \\")
    lines.append("Contract control & Yes & -- & Yes & -- & Yes & -- \\\\")
    lines.append("Sample & All & EOA & All & EOA & All & EOA \\\\")
    lines.append("Observations & " + " & ".join(f"{int(fits[c].nobs):,}" for c in cols) + r" \\")
    (TAB / "table3_regressions.tex").write_text("\n".join(lines) + "\n\\bottomrule\n")
    summary = pd.DataFrame({f"{y}|{s}": fits[(y, s)].params for (y, s) in cols})
    summary.to_csv(TAB / "table3_regressions.csv")


# ---------------------------------------------------------------- Figure 5
def fig_timing(t, s, price):
    """Cumulative net outflow of each size group during the stress window,
    scaled by the group's aggregate Mar 10 balance."""
    w = t[(t.time >= STRESS[0]) & (t.time < STRESS[1])]
    grp = s.set_index("address")["size"]
    grp = grp[~s.set_index("address").is_contract]  # EOAs only
    out = w[w["from"].isin(grp.index)].assign(g=lambda x: x["from"].map(grp)).groupby(["hour", "g"], observed=True)["usdc"].sum()
    inn = w[w["to"].isin(grp.index)].assign(g=lambda x: x["to"].map(grp)).groupby(["hour", "g"], observed=True)["usdc"].sum()
    net = out.sub(inn, fill_value=0).unstack().fillna(0)
    net = net.reindex(pd.date_range(*STRESS, freq="h", inclusive="left")).fillna(0)
    base = s[~s.is_contract].groupby("size", observed=True)["bal_0310"].sum()
    cum = net.cumsum() / base
    fig, ax = plt.subplots(2, 1, figsize=(6.5, 4.4), sharex=True, height_ratios=[1, 2])
    pr = price[(price.hour >= STRESS[0]) & (price.hour < STRESS[1])]
    ax[0].plot(pr.hour, pr.price, color=MUTED)
    ax[0].set_ylabel("USDC/USD")
    for i, g in enumerate(SIZE_LABELS):
        ax[1].plot(cum.index, cum[g], color=RAMP[i], label=g)
    ax[1].axhline(0, color=MUTED, lw=0.6)
    ax[1].set_ylabel("Cumulative net outflow /\ngroup balance on Mar 10")
    ax[1].legend(title="Mar 3 balance (EOAs)", fontsize=7, title_fontsize=7, loc="upper left")
    for a in ax:
        a.axvline(BACKSTOP, color=MUTED, lw=0.8, ls="--")
        a.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:00"))
    fig.savefig(FIG / "fig5_timing_by_size.png")
    plt.close(fig)
    # hour at which each group reached 50% of its peak cumulative net outflow
    half = {g: cum[g].ge(0.5 * cum[g].max()).idxmax() for g in SIZE_LABELS}
    return cum, half


# ---------------------------------------------------------------- tables
def period_table(t, mb):
    t2 = t.assign(period=pd.cut(t.time, [pd.Timestamp("2023-03-01", tz="UTC"), pd.Timestamp("2023-03-10", tz="UTC"),
                                          STRESS[1], pd.Timestamp("2023-03-21", tz="UTC")],
                                labels=["Pre (Mar 1-9)", "Stress (Mar 10-13)", "Post (Mar 14-20)"], right=False))
    rows = []
    for p, g in t2.groupby("period", observed=True):
        days = g.day.nunique()
        mbp = mb.loc[g.day.unique()]
        nf = {c: (g.loc[g.to_cat == c, "usdc"].sum() - g.loc[g.from_cat == c, "usdc"].sum()) / 1e9 for c in VENUES}
        rows.append({"Period": p, "Days": days, "Transfers / day": len(g) / days,
                     "Volume / day ($bn)": g.usdc.sum() / 1e9 / days,
                     "Active addresses / day": g.groupby("day").apply(lambda x: pd.unique(pd.concat([x["from"], x["to"]])).size).mean(),
                     "Minted ($bn)": mbp["mint"].sum(), "Burned ($bn)": mbp["burn"].sum(),
                     **{f"Net to {VENUES[c]} ($bn)": nf[c] for c in VENUES}})
    tab = pd.DataFrame(rows).set_index("Period").T
    tab.to_csv(TAB / "table1_periods.csv")
    fmt = lambda v: f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"
    lines = [k.replace("$", r"\$").replace("/", "/") + " & " + " & ".join(fmt(v) for v in r) + r" \\" for k, r in tab.iterrows()]
    (TAB / "table1_periods.tex").write_text("\n".join(lines) + "\n\\bottomrule\n")
    return tab


def means_table(p):
    m = p.groupby(["size", "window"], observed=True)[["net_out_share", "exit_share", "ran"]].mean().unstack()
    n = p[p.window == "stress"].groupby("size", observed=True).size()
    m.to_csv(TAB / "table2_means.csv")
    lines = []
    for g in SIZE_LABELS:
        r = m.loc[g]
        lines.append(g.replace("$", r"\$") + f" & {n[g]:,} & " + " & ".join(
            f"{r[(v, w)]:.3f}" for v in ["net_out_share", "exit_share", "ran"] for w in ["placebo", "stress"]) + r" \\")
    (TAB / "table2_means.tex").write_text("\n".join(lines) + "\n\\bottomrule\n")
    return m, n


DEST = {"pool_stable": "AMM pool vs. stablecoin", "uniswap": "Uniswap (hand-labeled)",
        "pool_volatile": "AMM pool vs. volatile token", "curve_3pool": "Curve 3pool", "maker_psm": "Maker PSM",
        "cex": "Labeled CEX wallet", "lending": "Aave/Compound", "other_contract": "Other contract (routers etc.)",
        "unclassified": "Unclassified address"}


def destination_table(t, s):
    """Where did sample EOAs send USDC during the stress window? Shares of each
    size group's gross outflow by destination type."""
    w = t[(t.time >= STRESS[0]) & (t.time < STRESS[1])]
    eoa = s[~s.is_contract].set_index("address")["size"]
    w = w[w["from"].isin(eoa.index)].assign(g=lambda x: x["from"].map(eoa),
                                            dest=lambda x: x.to_cat.fillna("unclassified"))
    tab = w.pivot_table(index="dest", columns="g", values="usdc", aggfunc="sum", observed=True).fillna(0)
    tab = (tab / tab.sum()).reindex(list(DEST)).fillna(0)
    tab.index = [DEST[k] for k in tab.index]
    tab.to_csv(TAB / "table4_destinations.csv")
    lines = [k + " & " + " & ".join(f"{v:.3f}" for v in r) + r" \\" for k, r in tab.iterrows()]
    (TAB / "table4_destinations.tex").write_text("\n".join(lines) + "\n\\bottomrule\n")
    return tab


def main():
    t, lab, price, bal, codes = load()
    price["hour"] = pd.to_datetime(price.hour, utc=True)
    fig_price_volume(t, price)
    mb = fig_mint_burn(t)
    fig_venues(t)
    conc = concentration(t)
    conc.to_csv(TAB / "concentration_daily.csv")
    s, p = build_wallets(t, lab, bal, codes)
    cum, half = fig_timing(t, s, price)
    tab1 = period_table(t, mb)
    dest = destination_table(t, s)
    m, n = means_table(p)
    d, fits = regressions(p)
    reg_table(fits, d)

    pd.set_option("display.width", 200, "display.float_format", "{:,.3f}".format)
    print(tab1.to_string(), "\n")
    print(dest.to_string(), "\n")
    print(mb.to_string(), "\n")
    print(conc, "\n")
    print(m, "\n", n, "\n")
    for k, f in fits.items():
        print(k, f.params.round(3).to_dict(), "\n   se", f.bse.round(3).to_dict())
    print("\nhalf-way hour by group:", {g: str(h) for g, h in half.items()})
    print("peak cumulative net outflow share:", cum.max().round(3).to_dict())
    print("final cumulative net outflow share:", cum.iloc[-1].round(3).to_dict())
    print("contract share by group:", s.groupby("size", observed=True).is_contract.mean().round(3).to_dict())


if __name__ == "__main__":
    main()
