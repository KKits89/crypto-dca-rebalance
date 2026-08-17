import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(layout="wide", page_title="Crypto DCA Pro Dashboard")

st.title("🚀 Crypto DCA & Smart Buy Pro Dashboard")

# --- DATABASE SETUP (SQLITE) ---
DB_FILE = "portfolio.db"
HISTORY_CSV = "transactions.csv"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            asset TEXT,
            amount REAL,
            usd_cost REAL
        )
    ''')
    conn.commit()
    
    # Αν η βάση είναι άδειη αλλά υπάρχει το παλιό CSV, κάνε migration αυτόματα!
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    if count == 0 and os.path.exists(HISTORY_CSV):
        try:
            df_old = pd.read_csv(HISTORY_CSV)
            for _, row in df_old.iterrows():
                cursor.execute(
                    "INSERT INTO transactions (date, asset, amount, usd_cost) VALUES (?, ?, ?, ?)",
                    (row['Date'], row['Asset'], row['Amount'], row['USD_Cost'])
                )
            conn.commit()
        except:
            pass
            
    # Αν η βάση είναι εντελώς άδειη και δεν υπάρχει CSV, βάλε τα αρχικά δεδομένα
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        initial_data = [
            ("2026-08-12", "BTC", 0.0201469, 1377.33),
            ("2026-08-12", "ETH", 0.258, 442.73),
            ("2026-08-12", "SOL", 4.5566, 323.13),
            ("2026-08-12", "ZEC", 0.2061, 104.18),
            ("2026-08-12", "HYPE", 3.17, 192.48)
        ]
        cursor.executemany("INSERT INTO transactions (date, asset, amount, usd_cost) VALUES (?, ?, ?, ?)", initial_data)
        conn.commit()
        
    conn.close()

init_db()

# Συνάρτηση ανάκτησης τελευταίας ημερομηνίας
def get_latest_transaction_date():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM transactions")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res and res[0] else "Καμία"

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ ---
st.sidebar.title("🤖 DCA Settings")

new_cash_to_invest = st.sidebar.number_input("Cash to Invest Today ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📝 Add New Transaction")

latest_date = get_latest_transaction_date()
st.sidebar.info(f"📅 Τελευταία συναλλαγή: **{latest_date}**")

asset_input = st.sidebar.text_input("Asset (π.χ. BTC)", "BTC").upper()
amount_input = st.sidebar.number_input("Amount Bought", value=0.0, format="%.6f")
cost_input = st.sidebar.number_input("USD Cost ($)", value=0.0, format="%.2f")

if st.sidebar.button("Save Transaction"):
    if amount_input > 0 and cost_input > 0:
        t_date = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (date, asset, amount, usd_cost) VALUES (?, ?, ?, ?)",
                       (t_date, asset_input, amount_input, cost_input))
        conn.commit()
        conn.close()
        st.sidebar.success(f"Καταγράφηκε στη βάση: {amount_input} {asset_input}!")
        st.rerun()
    else:
        st.sidebar.error("Συμπλήρωσε ποσό και κόστος μεγαλύτερο από 0.")

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΗ ΒΑΣΗ ---
def load_portfolio():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    
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

# Νέα συνάρτηση υπολογισμού New Average Price
def calculate_new_avg(old_cost, old_amount, new_money, current_price):
    if new_money <= 0 or current_price <= 0:
        return old_cost / old_amount if old_amount > 0 else 0
    new_amount = new_money / current_price
    return (old_cost + new_money) / (old_amount + new_amount)

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

# --- ΔΗΜΙΟΥΡΓΙΑ TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard & Smart Buy", "📈 Interactive Charts", "📋 Transactions History", "🛠 Pro Simulator"])

with tab1:
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
        
        # Υπολογισμός New Avg Price με βάση το Smart Buy
        new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
        diff_avg = new_avg - stats['avg_price']
        
        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"

        table_data.append({
            "Asset": asset,
            "Avg Price": f"${stats['avg_price']:.2f}",
            "New Avg": f"${new_avg:.2f}",
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
    st.subheader("📋 Transactions History (SQLite Database)")
    conn = sqlite3.connect(DB_FILE)
    raw_df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    if not raw_df.empty:
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, use_container_width=True)
    else:
        st.info("Δεν υπάρχουν αποθηκευμένες συναλλαγές.")

with tab4:
    st.subheader("🛠 Pro Simulator: Dynamic Rebalancing")
    st.markdown("Πειραματίσου με τα ποσοστά στόχου και δες πώς αλλάζει το Average Price σου!")
    
    sim_cash = st.number_input("Simulation Cash ($)", value=100.0, step=10.0, key="sim_cash")
    
    new_targets = {}
    col_s1, col_s2 = st.columns(2)
    
    # Sliders για τα ποσοστά
    for asset, data in portfolio_data.items():
        new_targets[asset] = col_s1.slider(
            f"Target % for {asset}", 
            0.0, 1.0, float(data.get("target_pct", 0.1)), key=f"slider_{asset}"
        )
        
    if st.button("Run Simulation"):
        sim_results = []
        for asset, data in portfolio_data.items():
            stats = current_values[asset]
            simulated_buy = sim_cash * new_targets[asset]
            old_avg = stats['avg_price']
            new_avg = calculate_new_avg(data['total_cost'], data['amount'], simulated_buy, stats['price'])
            
            sim_results.append({
                "Asset": asset,
                "Old Avg": f"${old_avg:.2f}",
                "Simulated Buy": f"${simulated_buy:.2f}",
                "New Avg Price": f"${new_avg:.2f}"
            })
        col_s2.table(pd.DataFrame(sim_results))
        col_s2.success("Το simulation ολοκληρώθηκε επιτυχώς!")
