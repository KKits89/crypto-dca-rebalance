import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
from datetime import datetime

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(layout="wide", page_title="Crypto DCA Pro Dashboard")

st.title("🚀 Crypto DCA & Smart Buy Pro Dashboard")

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ ---
st.sidebar.title("🤖 DCA Settings")
new_cash_to_invest = st.sidebar.number_input("Cash to Invest Today ($)", value=50.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📝 Add New Transaction")
asset_input = st.sidebar.text_input("Asset (π.χ. BTC)", "BTC").upper()
amount_input = st.sidebar.number_input("Amount Bought", value=0.0, format="%.6f")
cost_input = st.sidebar.number_input("USD Cost ($)", value=0.0, format="%.2f")

history_csv = "transactions.csv"

if st.sidebar.button("Save Transaction"):
    if amount_input > 0 and cost_input > 0:
        t_date = datetime.now().strftime("%Y-%m-%d")
        new_row = pd.DataFrame([[t_date, asset_input, amount_input, cost_input]], columns=['Date', 'Asset', 'Amount', 'USD_Cost'])
        
        if not os.path.exists(history_csv):
            new_row.to_csv(history_csv, index=False)
        else:
            new_row.to_csv(history_csv, mode='a', header=False, index=False)
        st.sidebar.success(f"Καταγράφηκε: {amount_input} {asset_input}!")
    else:
        st.sidebar.error("Συμπλήρωσε ποσό και κόστος μεγαλύτερο από 0.")

# --- ΑΥΤΟΜΑΤΗ ΔΗΜΙΟΥΡΓΙΑ CSV ΑΝ ΔΕΝ ΥΠΑΡΧΕΙ ---
if not os.path.exists(history_csv):
    initial_csv_content = """Date,Asset,Amount,USD_Cost
2026-08-12,BTC,0.0201469,1377.33
2026-08-12,ETH,0.258,442.73
2026-08-12,SOL,4.5566,323.13
2026-08-12,ZEC,0.2061,104.18
2026-08-12,HYPE,3.17,192.48
"""
    with open(history_csv, "w") as f:
        f.write(initial_csv_content)

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΟ CSV ---
def load_portfolio():
    df = pd.read_csv(history_csv)
    summary = df.groupby('Asset').agg({'Amount': 'sum', 'USD_Cost': 'sum'}).to_dict('index')

    settings = {
        "BTC": {"ticker": "BTC-USD", "target_pct": 0.55, "type": "live"},
        "ETH": {"ticker": "ETH-USD", "target_pct": 0.20, "type": "live"},
        "SOL": {"ticker": "SOL-USD", "multiplier": 1.0, "target_pct": 0.15, "type": "auto"},
        "ZEC": {"ticker": "ZEC-USD", "target_pct": 0.05, "type": "live"},
        "HYPE": {"ticker": "HYPE32196-USD", "target_pct": 0.05, "type": "live"}
    }

    for asset, data in summary.items():
        if asset in settings:
            data.update(settings[asset])
            data['total_cost'] = data.pop('USD_Cost')
            data['amount'] = data.pop('Amount')
    return summary

portfolio_data = load_portfolio()

# Συνάρτηση υπολογισμού RSI
def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Λήψη ισοτιμίας USD σε EUR
try:
    eur_ticker = yf.Ticker("EURUSD=X")
    eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
    usd_to_eur = 1.0 / eur_rate
except:
    usd_to_eur = 0.92

current_values = {}
total_current_portfolio = 0
total_invested_cost = sum(d["total_cost"] for d in portfolio_data.values())

for asset, data in portfolio_data.items():
    try:
        hist = yf.Ticker(data["ticker"]).history(period="100d")
        price = hist['Close'].iloc[-1] * data.get("multiplier", 1.0)
        sma_50 = hist['Close'].tail(50).mean() * data.get("multiplier", 1.0) if len(hist) >= 50 else price
        rsi = get_rsi(hist['Close']).iloc[-1] if len(hist) >= 15 else 50.0
    except:
        price = data["total_cost"] / data["amount"]
        sma_50 = price
        rsi = 50.0

    val = data["amount"] * price
    avg_price = data["total_cost"] / data["amount"]
    pnl_usd = val - data["total_cost"]
    pnl_pct = (pnl_usd / data["total_cost"]) * 100
    is_healthy_dip = price >= sma_50

    current_values[asset] = {
        "price": price,
        "avg_price": avg_price,
        "current_val": val,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "sma_50": sma_50,
        "rsi": rsi,
        "is_healthy_dip": is_healthy_dip
    }
    total_current_portfolio += val

new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur
total_pnl_usd = total_current_portfolio - total_invested_cost
pnl_eur = total_pnl_usd * usd_to_eur
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100

# --- STRICT & SMART MODES ---
strict_allocations = {}
for asset, data in portfolio_data.items():
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values())
if total_strict_weight == 0:
    total_strict_weight = 1.0

smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    pnl = current_values[asset]["pnl_usd"]
    stats = current_values[asset]

    if pnl < 0 and stats["is_healthy_dip"]:
        base_bonus = min(abs(pnl) / total_current_portfolio * 2, 0.5)
        rsi_multiplier = 1.3 if stats["rsi"] < 40 else 1.0
        pnl_weight = 1.0 + (base_bonus * rsi_multiplier)
    else:
        pnl_weight = 1.0

    smart_weight = base_need * pnl_weight
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

if total_smart_weight == 0:
    total_smart_weight = 1.0

# --- ΔΗΜΙΟΥΡΓΙΑ TABS ΓΙΑ ΩΡΑΙΟΤΕΡΟ UI ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Smart Buy", "📈 Interactive Charts", "📋 Transactions History"])

with tab1:
    # --- TOP METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    col2.metric("Total PnL", f"${total_pnl_usd:+,.2f}", f"{total_pnl_pct:+.2f}% ({pnl_eur:+,.2f}€)")
    col3.metric("New Cash Allocation", f"${new_cash_to_invest:,.2f}")

    st.markdown("---")
    st.subheader("📊 Execution Plan & Metrics Table")

    table_data = []
    for asset, data in portfolio_data.items():
        stats = current_values[asset]
        strict_share = strict_allocations[asset] / total_strict_weight
        strict_buy = new_cash_to_invest * strict_share
        smart_share = smart_allocations[asset] / total_smart_weight
        smart_buy = new_cash_to_invest * smart_share
        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"

        table_data.append({
            "Asset": asset,
            "Avg Price": f"${stats['avg_price']:.2f}",
            "Curr Price": f"${stats['price']:.2f}",
            "SMA 50": f"${stats['sma_50']:.2f}",
            "RSI": f"{stats['rsi']:.1f}",
            "PnL": pnl_str,
            "Strict Buy": f"${strict_buy:.2f}",
            "Smart Buy": f"${smart_buy:.2f}"
        })

    df_metrics = pd.DataFrame(table_data)
    df_metrics.index = df_metrics.index + 1
    st.dataframe(df_metrics, use_container_width=True)

with tab2:
    st.subheader("📈 Interactive Portfolio Charts (Plotly)")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_pie = px.pie(
            names=list(current_values.keys()),
            values=[info["current_val"] for info in current_values.values()],
            title="Portfolio Distribution",
            hole=0.4
        )
        fig_pie.update_layout(paper_bgcolor="#1e1e1e", font_color="white")
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart2:
        assets_list = list(current_values.keys())
        pnl_values = [info["pnl_usd"] for info in current_values.values()]
        colors = ['#2ecc71' if v >= 0 else '#ff4757' for v in pnl_values]
        
        fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=pnl_values, marker_color=colors)])
        fig_bar.update_layout(
            title="PnL per Coin ($)",
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#1e1e1e",
            font_color="white"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.subheader("📋 Raw Transactions File")
    if os.path.exists(history_csv):
        raw_df = pd.read_csv(history_csv)
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, use_container_width=True)
