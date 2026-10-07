"""
India Two-Wheeler EV Market Entry — Quantitative Model
========================================================
Builds a bottom-up TAM -> SAM -> SOM market sizing model, a 5-year revenue
forecast, and a two-lever sensitivity analysis (policy risk vs. execution risk).

All base assumptions are derived from real public data (Vahan/EVreporter
registration data, JMK Research, FADA) as documented in the accompanying
executive summary. Where a number required judgment (e.g. our hypothetical
entrant's obtainable market share), the reasoning is commented inline.

Run: python3 market_entry_model.py
Outputs: base_case.csv, sensitivity.csv, and 4 chart PNGs in /charts
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

os.makedirs("charts", exist_ok=True)

# ============================================================
# STEP 1: TAM — Total Addressable Market (all 2-wheelers, India)
# ============================================================
# Back-calculated from real registration data: e-2W sales were ~1.28M units
# in 2025 at ~6.3% penetration => total 2W market ~= 1.28M / 0.063 ~= 20.3M.
# This matches India's known position as the world's largest 2W market.
# Assumption: total 2W market is mature; grows at 3.5% CAGR (tracks
# population + income growth; EVs substitute ICE demand, don't expand the
# category).
TAM_2025 = 20.3  # million units
TAM_GROWTH = 0.035
YEARS = list(range(2026, 2033))

tam = {}
val = TAM_2025
for y in YEARS:
    val *= (1 + TAM_GROWTH)
    tam[y] = val

# ============================================================
# STEP 2: SAM — Serviceable Available Market (EV penetration curve)
# ============================================================
# Real data points: Jan 2026 = 6.6% penetration, Jul 2026 = 11.2%.
# Modeled as an S-curve decelerating toward a ~32% ceiling by 2032 —
# roughly consistent with the government's 30%-by-2030 EV ambition.
PENETRATION = {
    2026: 0.13, 2027: 0.17, 2028: 0.21, 2029: 0.25,
    2030: 0.28, 2031: 0.30, 2032: 0.32,
}
sam = {y: tam[y] * PENETRATION[y] for y in YEARS}

# ============================================================
# STEP 3: SOM — Our hypothetical entrant's obtainable share
# ============================================================
# Two-wheelers have NO import-first pathway (unlike cars' SPMEPCI scheme),
# so a foreign entrant must commit to local manufacturing/JV almost
# immediately. We assume ~18-24 months of setup (2026-27), first commercial
# sales in 2028. Share ramp is benchmarked well BELOW Hero Vida's real
# trajectory (0 -> 11% share in 2 years) because Vida launched on Hero's
# existing 6M+/yr dealer network; our JV-based entrant starts thinner.
COMMERCIAL_YEARS = [2028, 2029, 2030, 2031, 2032]
SHARE_RAMP = {2028: 0.005, 2029: 0.012, 2030: 0.020, 2031: 0.028, 2032: 0.035}
som_units = {y: sam[y] * SHARE_RAMP[y] for y in COMMERCIAL_YEARS}

# ============================================================
# STEP 4: Revenue model
# ============================================================
# ASP anchored at Rs 1,00,000 (mass-market e-2W range), drifting down ~2%/yr
# in real terms as battery costs fall and competitive pricing pressure rises.
ASP_2028 = 100000  # INR
ASP_DECLINE = 0.02
INR_PER_USD = 88

asp = {}
val = ASP_2028
for y in COMMERCIAL_YEARS:
    asp[y] = val
    val *= (1 - ASP_DECLINE)

def build_base_case():
    rows = []
    for y in COMMERCIAL_YEARS:
        units = som_units[y]
        revenue_inr_cr = units * 1e6 * asp[y] / 1e7
        revenue_usd_m = units * 1e6 * asp[y] / INR_PER_USD / 1e6
        rows.append({
            "Year": y, "TAM (M units)": round(tam[y], 2),
            "Penetration %": f"{PENETRATION[y]*100:.0f}%",
            "SAM (M units)": round(sam[y], 3),
            "Our share of SAM": f"{SHARE_RAMP[y]*100:.1f}%",
            "SOM (units)": round(units * 1e6),
            "ASP (Rs)": round(asp[y]),
            "Revenue (Rs Cr)": round(revenue_inr_cr, 1),
            "Revenue (USD M)": round(revenue_usd_m, 1),
        })
    return pd.DataFrame(rows)

# ============================================================
# STEP 5: Sensitivity analysis — Policy lever vs. Execution lever
# ============================================================
def run_scenario(penetration, share_ramp, label=""):
    sam_s = {y: tam[y] * penetration[y] for y in YEARS}
    som_s = {y: sam_s[y] * share_ramp[y] for y in COMMERCIAL_YEARS}
    val2 = ASP_2028
    asp_s = {}
    for y in COMMERCIAL_YEARS:
        asp_s[y] = val2
        val2 *= (1 - ASP_DECLINE)
    rev_cr = som_s[2032] * 1e6 * asp_s[2032] / 1e7
    rev_usd = som_s[2032] * 1e6 * asp_s[2032] / INR_PER_USD / 1e6
    return {
        "Scenario": label,
        "2032 Penetration": f"{penetration[2032]*100:.0f}%",
        "2032 Our Share of SAM": f"{share_ramp[2032]*100:.1f}%",
        "2032 Revenue (USD M)": round(rev_usd, 0),
    }

PEN_BULL = {2026:0.13,2027:0.19,2028:0.25,2029:0.29,2030:0.32,2031:0.34,2032:0.36}
PEN_BEAR = {2026:0.13,2027:0.15,2028:0.17,2029:0.19,2030:0.21,2031:0.23,2032:0.25}
SHARE_BULL = {2028:0.010,2029:0.022,2030:0.035,2031:0.048,2032:0.060}
SHARE_BEAR = {2028:0.002,2029:0.005,2030:0.008,2031:0.011,2032:0.015}

def build_sensitivity():
    results = [
        run_scenario(PENETRATION, SHARE_RAMP, "Base Case"),
        run_scenario(PEN_BULL, SHARE_RAMP, "Policy Bull (subsidy returns)"),
        run_scenario(PEN_BEAR, SHARE_RAMP, "Policy Bear (no subsidy + cost inflation)"),
        run_scenario(PENETRATION, SHARE_BULL, "Execution Bull (strong JV/distribution)"),
        run_scenario(PENETRATION, SHARE_BEAR, "Execution Bear (weak distribution)"),
        run_scenario(PEN_BULL, SHARE_BULL, "Full Bull (both favorable)"),
        run_scenario(PEN_BEAR, SHARE_BEAR, "Full Bear (both unfavorable)"),
    ]
    return pd.DataFrame(results)

# ============================================================
# STEP 6: Charts
# ============================================================
plt.rcParams.update({
    "font.family": "DejaVu Sans", "axes.edgecolor": "#444444",
    "axes.spines.top": False, "axes.spines.right": False,
})
NAVY, TEAL, GOLD, GREY, RED = "#1B2A4A", "#2E8B8B", "#C9A227", "#B0B0B0", "#B03A2E"

def chart_revenue():
    rev = [26.9, 77.8, 147.4, 224.2, 303.2]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.bar(COMMERCIAL_YEARS, rev, color=NAVY, width=0.55)
    for b, v in zip(bars, rev):
        ax.text(b.get_x()+b.get_width()/2, v+8, f"${v:.0f}M", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("Base-Case Revenue Forecast, Years 1-5", fontsize=12, fontweight="bold", loc="left")
    ax.set_ylabel("Revenue (USD Million)"); ax.set_ylim(0, 360)
    plt.tight_layout(); plt.savefig("charts/chart_revenue.png", dpi=200); plt.close()

def chart_competitive():
    players = ["TVS", "Bajaj", "Ather", "Hero (Vida)", "Ola Electric", "Others"]
    shares = [27.2, 22.9, 17.4, 10.9, 6.8, 14.8]
    colors = [NAVY, NAVY, TEAL, TEAL, RED, GREY]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.barh(players[::-1], shares[::-1], color=colors[::-1])
    for b, v in zip(bars, shares[::-1]):
        ax.text(v+0.5, b.get_y()+b.get_height()/2, f"{v:.1f}%", va="center", fontsize=10, fontweight="bold")
    ax.set_title("India E-2W Market Share, H1 2026", fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel("Market Share (%)"); ax.set_xlim(0, 32)
    plt.tight_layout(); plt.savefig("charts/chart_competitive.png", dpi=200); plt.close()

def chart_sensitivity():
    scenarios = ["Execution\nBear", "Policy\nBear", "Base\nCase", "Policy\nBull", "Execution\nBull"]
    values = [130, 237, 303, 341, 520]
    colors3 = [RED, "#D98880", NAVY, "#7FB3B3", TEAL]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.bar(scenarios, values, color=colors3, width=0.6)
    for b, v in zip(bars, values):
        ax.text(b.get_x()+b.get_width()/2, v+8, f"${v}M", ha="center", fontsize=10, fontweight="bold")
    ax.axhline(303, color=GREY, linestyle="--", linewidth=1)
    ax.set_title("Year-5 Revenue: Execution Risk vs. Policy Risk", fontsize=12, fontweight="bold", loc="left")
    ax.set_ylabel("2032 Revenue (USD Million)"); ax.set_ylim(0, 580)
    plt.tight_layout(); plt.savefig("charts/chart_sensitivity.png", dpi=200); plt.close()

def chart_funnel():
    labels = ["TAM\n(Total 2W market)", "SAM\n(E-2W addressable)", "SOM\n(Our obtainable share)"]
    vals = [tam[2032], sam[2032], som_units[2032]]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.bar(labels, vals, color=[GREY, TEAL, NAVY], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.5, f"{v:.2f}M units", ha="center", fontsize=10, fontweight="bold")
    ax.set_title("Market Sizing Funnel — 2032 Snapshot", fontsize=12, fontweight="bold", loc="left")
    ax.set_ylabel("Units (Millions)"); ax.set_ylim(0, 29)
    plt.tight_layout(); plt.savefig("charts/chart_funnel.png", dpi=200); plt.close()

if __name__ == "__main__":
    base_df = build_base_case()
    sens_df = build_sensitivity()
    base_df.to_csv("base_case.csv", index=False)
    sens_df.to_csv("sensitivity.csv", index=False)
    print("=== BASE CASE ===")
    print(base_df.to_string(index=False))
    print("\n=== SENSITIVITY ===")
    print(sens_df.to_string(index=False))
    chart_revenue(); chart_competitive(); chart_sensitivity(); chart_funnel()
    print("\nCharts saved to ./charts/")
