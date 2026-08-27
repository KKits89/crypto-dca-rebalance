import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(layout="wide", page_title="Crypto DCA Pro Terminal", page_icon="⚡")

# --- CUSTOM PROFESSIONAL CSS (TERMINAL / FINTECH LOOK) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    h1, h2, h3, h4 {
        color: #f0f6fc !important;
        font-weight: 600;
        letter-spacing: -0.5px;
    }

    p, span, label, div {
        color: #e6e6e6;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0e1117;
        padding: 4px 0;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 4px;
        color: #8b949e;
        border: 1px solid #30363d;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border-color: #58a6ff !important;
    }

    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
    }

    .risk-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- ΑΥΤΟΜΑΤΗ ΑΝΑΝΕΩΣΗ ΑΝΑ 1 ΛΕΠΤΟ ---
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.title("⚡ Crypto DCA & Smart Terminal")

# --- GOOGLE SHEETS SETUP ---
def get_g_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("CryptoPortfolio").sheet1 
    return sheet

@st.cache_data(ttl=10)
def load_transactions_from_sheet():
    try:
        sheet = get_g_sheet()
        data_rows = sheet.get_all_records()
        
        if not data_rows:
            sheet.append_row(["Date", "Asset", "Amount", "USD_Cost"])
            return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])
            
        df = pd.DataFrame(data_rows)
        df.columns = [str(col).strip().capitalize() for col in df.columns]
        if 'Usd_cost' in df.columns and 'USD_Cost' not in df.columns:
            df.rename(columns={'Usd_cost': 'USD_Cost'}, inplace=True)
            
        for col in ['Amount', 'USD_Cost']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
            elif col.lower() in df.columns:
                df[col.lower()] = pd.to_numeric(df[col.lower()].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")
        return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])

def get_latest_transaction_date(df):
    if not df.empty:
        for col in df.columns:
            if 'date' in col.lower():
                valid_dates = df[col].dropna()
                if not valid_dates.empty:
                    return str(valid_dates.max())
    return "N/A"

# --- ΑΡΧΙΚΟ ΦΟΡΤΩΜΑ ΓΙΑ ΕΝΤΟΠΙΣΜΟ ASSETS ---
raw_df_initial = load_transactions_from_sheet()
unique_assets_in_sheet = []
if not raw_df_initial.empty:
    col_asset = next((c for c in raw_df_initial.columns if 'asset' in c.lower()), 'Asset')
    unique_assets_in_sheet = [str(x).upper().strip() for x in raw_df_initial[col_asset].unique() if str(x).strip() != '']

# Default slugs αν κάποιο asset δεν υπάρχει στα defaults
default_slugs = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ZEC": "zcash",
    "HYPE": "hyperliquid",
    "PUMP": "pump-fun"
}

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ (BUY / SELL) ---
st.sidebar.markdown("### ⚙️ Trade & Execution")

new_cash_to_invest = st.sidebar.number_input("Cash to Invest Today ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Target Allocation Weights (%)")
st.sidebar.caption("Ορίστε τα επιθυμητά ποσοστά βάρους για το DCA. Το άθροισμα πρέπει να είναι 100%.")

# Δυναμικά Sliders για κάθε asset που υπάρχει στο sheet
target_weights = {}
default_pct_split = 100.0 / len(unique_assets_in_sheet) if unique_assets_in_sheet else 100.0

for asset in unique_assets_in_sheet:
    # Προεπιλεγμένα ποσοστά για τα βασικά, μοιρασμένα τα υπόλοιπα
    fallback_defaults = {"BTC": 50.0, "ETH": 20.0, "SOL": 15.0, "ZEC": 5.0, "HYPE": 5.0, "PUMP": 5.0}
    def_val = fallback_defaults.get(asset, round(default_pct_split, 1))
    
    target_weights[asset] = st.sidebar.slider(f"{asset} Target %", 0.0, 100.0, float(def_val), 1.0, key=f"weight_{asset}")

total_weight_sum = sum(target_weights.values())
if abs(total_weight_sum - 100.0) > 0.01:
    st.sidebar.error(f"⚠️ Άθροισμα ποσοστών: {total_weight_sum:.1f}% (Πρέπει να είναι ακριβώς 100%)!")
else:
    st.sidebar.success(f"✅ Άθροισμα ποσοστών: 100.0%")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 New Order Entry")

latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.caption(f"📅 Last Transaction: **{latest_date}**")

tx_type = st.sidebar.radio("Order Type:", ["🟢 BUY", "🔴 SELL"], horizontal=True)

asset_input = st.sidebar.text_input("Coin Ticker", "BTC").upper().strip()
amount_input = st.sidebar.number_input("Amount", value=0.0, format="%.6f")
cost_input = st.sidebar.number_input("USD Total ($)", value=0.0, format="%.2f")

if st.sidebar.button("Execute Order"):
    if amount_input > 0 and cost_input > 0 and asset_input:
        t_date = datetime.now().strftime("%Y-%m-%d")
        
        final_amount = -amount_input if "SELL" in tx_type else amount_input
        final_cost = -cost_input if "SELL" in tx_type else cost_input
        
        try:
            sheet = get_g_sheet()
            sheet.append_row([t_date, asset_input, f"{final_amount:.8f}", f"{final_cost:.2f}"])
            st.cache_data.clear()
            st.sidebar.success("Order logged successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Execution Error: {e}")
    else:
        st.sidebar.error("Please fill valid coin, amount and USD cost (> 0).")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Risk & Undo Last")

if not raw_df_initial.empty:
    last_row = raw_df_initial.iloc[-1]
    st.sidebar.markdown(
        f"<div style='font-size: 12px; color: #8b949e; background: #161b22; padding: 8px; border-radius: 4px; border: 1px solid #30363d;'>"
        f"<b>Last Entry:</b> {last_row.get('Date', 'N/A')} | {last_row.get('Asset', 'N/A')}<br>"
        f"<b>Amt:</b> {last_row.get('Amount', 'N/A')} | <b>Cost:</b> ${last_row.get('USD_Cost', 'N/A')}"
        f"</div>", 
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("↩️ Revert Last Entry"):
        try:
            sheet = get_g_sheet()
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                row_to_delete = len(all_values)
                sheet.delete_rows(row_to_delete)
                st.cache_data.clear()
                st.sidebar.success("Last transaction reverted.")
                st.rerun()
            else:
                st.sidebar.warning("No transactions left to delete.")
        except Exception as e:
            st.sidebar.error(f"Error reverting: {e}")

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΟ GOOGLE SHEET ---
def load_portfolio():
    df = load_transactions_from_sheet()
    if df.empty:
        return {}
    
    col_asset = next((c for c in df.columns if 'asset' in c.lower()), 'Asset')
    col_amount = next((c for c in df.columns if 'amount' in c.lower()), 'Amount')
    col_cost = next((c for c in df.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    
    summary = df.groupby(col_asset).agg({col_amount: 'sum', col_cost: 'sum'}).to_dict('index')

    formatted_summary = {}
    for asset, data in summary.items():
        amt = float(data[col_amount])
        cst = float(data[col_cost])
        
        assigned_pct = target_weights.get(asset, 0.0) / 100.0
        
        formatted_summary[asset] = {
            'total_cost': cst,
            'amount': amt,
            'target_pct': assigned_pct,
            'cmc_slug': default_slugs.get(asset, asset.lower())
        }
            
    return formatted_summary

portfolio_data = load_portfolio()

@st.cache_data(ttl=25)
def get_cmc_prices(symbols_list):
    api_key = st.secrets["CMC_API_KEY"]
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    symbols_str = ",".join(symbols_list)
    
    parameters = {"symbol": symbols_str, "convert": "USD"}
    headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        prices = {}
        for sym in symbols_list:
            if sym in data.get("data", {}):
                prices[sym] = data["data"][sym]["quote"]["USD"]["price"]
        return prices
    except Exception as e:
        return {}

@st.cache_data(ttl=300)
def get_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1")
        data = res.json()
        return int(data["data"][0]["value"]), data["data"][0]["value_classification"]
    except:
        return 50, "Neutral"

all_symbols = list(portfolio_data.keys())
cmc_prices = get_cmc_prices(all_symbols) if all_symbols else {}
fng_value, fng_label = get_fear_and_greed()

def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_new_avg(old_cost, old_amount, new_money, current_price):
    if old_amount <= 0:
        return current_price
    if new_money <= 0 or current_price <= 0:
        return old_cost / old_amount if old_amount > 0 else 0
    new_amount = new_money / current_price
    return (old_cost + new_money) / (old_amount + new_amount)

def compute_smart_score(stats, fng):
    sc = 50
    if stats['rsi'] < 30:
        sc += 25
    elif stats['rsi'] < 42:
        sc += 15
    elif stats['rsi'] > 68:
        sc -= 25
        
    if stats['price'] <= stats['bb_lower']:
        sc += 20
        
    if fng < 30:
        sc += 15
    elif fng > 75:
        sc -= 15
        
    return max(0, min(100, sc))

try:
    eur_ticker = yf.Ticker("EURUSD=X")
    eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
    usd_to_eur = 1.0 / eur_rate
except:
    usd_to_eur = 0.92

current_values = {}
total_current_portfolio = 0
total_invested_cost = sum(d["total_cost"] for d in portfolio_data.values() if d["amount"] > 0) if portfolio_data else 0

for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue 
        
    price = cmc_prices.get(asset, data["total_cost"] / data["amount"] if data["amount"] > 0 else 0)
    
    rsi = 50.0
    sma_50 = price
    bb_lower = price * 0.95
    
    try:
        if asset == "HYPE":
            ticker_str = "HYPE32196-USD"
        else:
            ticker_str = f"{asset}-USD"
            
        hist = yf.Ticker(ticker_str).history(period="100d")
        if hist.empty or len(hist) < 15:
            hist = yf.Ticker(asset).history(period="100d")
            
        if not hist.empty and len(hist) >= 50:
            sma_50 = hist['Close'].tail(50).mean()
        else:
            sma_50 = price
            
        if not hist.empty and len(hist) >= 20:
            rolling_mean = hist['Close'].rolling(window=20).mean().iloc[-1]
            rolling_std = hist['Close'].rolling(window=20).std().iloc[-1]
            bb_lower = rolling_mean - (2 * rolling_std)
        else:
            bb_lower = price * 0.92

        if not hist.empty and len(hist) >= 15:
            rsi_series = get_rsi(hist['Close'])
            if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]):
                rsi = float(rsi_series.iloc[-1])
            else:
                raise Exception("Empty RSI series")
        else:
            raise Exception("Not enough history for RSI")
            
    except:
        avg_p = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else price
        if avg_p > 0:
            price_diff_pct = ((price - avg_p) / avg_p) * 100
            rsi = max(15.0, min(85.0, 50.0 - (price_diff_pct * 1.5)))
        else:
            rsi = 50.0

    val = data["amount"] * price
    avg_price = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else 0
    pnl_usd = val - data["total_cost"]
    pnl_pct = (pnl_usd / data["total_cost"]) * 100 if data["total_cost"] > 0 else 0
    is_healthy_dip = price >= sma_50

    temp_stats = {
        "price": price,
        "avg_price": avg_price,
        "current_val": val,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "sma_50": sma_50,
        "bb_lower": bb_lower,
        "rsi": rsi,
        "is_healthy_dip": is_healthy_dip
    }
    temp_stats["score"] = compute_smart_score(temp_stats, fng_value)

    current_values[asset] = temp_stats
    total_current_portfolio += val

new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur
total_pnl_usd = total_current_portfolio - total_invested_cost
pnl_eur = total_pnl_usd * usd_to_eur
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100 if total_invested_cost > 0 else 0

strict_allocations = {}
for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values())
if total_strict_weight == 0:
    total_strict_weight = 1.0

# --- SMART BUY WEIGHTS (ΣΥΝΔΕΣΗ ΜΕ ΤΟ SMART SCORE) ---
smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    if data["amount"] <= 0:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    
    score = current_values[asset]["score"]
    score_multiplier = max(0.1, score / 50.0)
    
    smart_weight = base_need * score_multiplier
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

if total_smart_weight == 0:
    total_smart_weight = 1.0

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Dashboard", 
    "📈 Performance Charts", 
    "📋 Ledger & Trades", 
    "🛠 Smart Advisor & Profit Engine",
    "🛡️ Risk & Exit Strategy"
])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Coin Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    col2.metric("Total Net PnL", f"${total_pnl_usd:+,.2f}", f"{total_pnl_pct:+.2f}% ({pnl_eur:+,.2f}€)")
    col3.metric("Allocatable Cash", f"${new_cash_to_invest:,.2f}")

    if abs(total_weight_sum - 100.0) > 0.01:
        st.warning(f"⚠️ Προσοχή: Τα ποσοστά στόχευσης στη sidebar αθροίζουν σε {total_weight_sum:.1f}% αντί για 100%. Τα ποσά Smart/Strict Buy ενδέχεται να μην κατανεμηθούν σωστά.")

    st.markdown("---")
    st.markdown("### 📊 Coin Allocation & Execution Matrix")

    table_data = []
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        strict_share = strict_allocations.get(asset, 0) / total_strict_weight
        strict_buy = new_cash_to_invest * strict_share
        smart_share = smart_allocations.get(asset, 0) / total_smart_weight
        smart_buy = new_cash_to_invest * smart_share
        
        new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"

        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Coin": cmc_url,
            "Name": asset,
            "Target %": f"{data['target_pct']*100:.1f}%",
            "Amount": f"{data['amount']:.6f} ({data['total_cost']:.2f}$)",
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
    if not df_metrics.empty:
        df_metrics.index = df_metrics.index + 1
    
    st.dataframe(
        df_metrics,
        width='stretch',
        column_config={
            "Coin": st.column_config.LinkColumn(
                "Coin Link",
                help="Open CoinMarketCap",
                display_text=r"https://coinmarketcap.com/currencies/(.*?)/"
            ),
            "Name": None
        }
    )

with tab2:
    st.markdown("### 📈 Historical Valuation & Metrics")
    
    raw_tx_df = load_transactions_from_sheet()
    if not raw_tx_df.empty:
        try:
            date_col = next((c for c in raw_tx_df.columns if 'date' in c.lower()), None)
            cost_col = next((c for c in raw_tx_df.columns if 'cost' in c.lower() or 'usd' in c.lower()), None)
            
            if date_col and cost_col:
                raw_tx_df[date_col] = pd.to_datetime(raw_tx_df[date_col])
                daily_costs = raw_tx_df.groupby(date_col)[cost_col].sum().reset_index()
                daily_costs = daily_costs.sort_values(by=date_col)
                daily_costs['Cumulative_Cost'] = daily_costs[cost_col].cumsum()
                
                min_date = daily_costs[date_col].min()
                max_date = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
                
                full_calendar = pd.date_range(start=min_date, end=max_date)
                calendar_df = pd.DataFrame({date_col: full_calendar})
                
                timeline_df = pd.merge(calendar_df, daily_costs[[date_col, 'Cumulative_Cost']], on=date_col, how='left')
                timeline_df['Cumulative_Cost'] = timeline_df['Cumulative_Cost'].ffill().fillna(0)
                
                days_count = len(timeline_df)
                if days_count > 1:
                    cost_start = timeline_df['Cumulative_Cost'].iloc[0]
                    timeline_df['Portfolio_Value'] = np.linspace(cost_start if cost_start > 0 else 1, total_current_portfolio, days_count)
                else:
                    timeline_df['Portfolio_Value'] = [total_current_portfolio]

                fig_timeline = go.Figure()
                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df[date_col], y=timeline_df['Cumulative_Cost'],
                    mode='lines', name='Invested Cost ($)', line=dict(color='#8b949e', width=2)
                ))
                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df[date_col], y=timeline_df['Portfolio_Value'],
                    mode='lines', name='Portfolio Value ($)', line=dict(color='#58a6ff', width=2.5),
                    fill='tonexty', fillcolor='rgba(88, 166, 255, 0.05)'
                ))
                fig_timeline.update_layout(
                    title="Portfolio Valuation vs Basis Cost",
                    xaxis_title="", yaxis_title="USD ($)",
                    paper_bgcolor="#0e1117", plot_bgcolor="#161b22", font_color="#e6e6e6",
                    hovermode="x unified",
                    xaxis=dict(type='date', gridcolor='#484f58', gridwidth=1.5, griddash='dash'),
                    yaxis=dict(gridcolor='#484f58', gridwidth=1.5, griddash='dash')
                )
                st.plotly_chart(fig_timeline, width='stretch')
        except Exception as e:
            st.info(f"Timeline chart notice: {e}")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if current_values:
            brand_colors = {"BTC": "#F7931A", "ETH": "#627EEA", "SOL": "#9945FF", "HYPE": "#4EEDCC", "ZEC": "#F4B728", "PUMP": "#FF2D55"}
            assets_in_pie = list(current_values.keys())
            fig_pie = px.pie(
                names=assets_in_pie, values=[info["current_val"] for info in current_values.values()],
                title="Coin Share Distribution", hole=0.5, color=assets_in_pie, color_discrete_map=brand_colors
            )
            fig_pie.update_layout(paper_bgcolor="#0e1117", font_color="#e6e6e6", legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363d"))
            st.plotly_chart(fig_pie, width='stretch')
        
    with col_chart2:
        if current_values:
            assets_list = list(current_values.keys())
            pnl_values = [info["pnl_usd"] for info in current_values.values()]
            colors = ['#238636' if v >= 0 else '#da3633' for v in pnl_values]
            fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=pnl_values, marker_color=colors)])
            fig_bar.update_layout(
                title="PnL Breakdown per Coin ($)",
                paper_bgcolor="#0e1117", plot_bgcolor="#161b22", font_color="#e6e6e6",
                xaxis=dict(gridcolor='#484f58', gridwidth=1.5, griddash='dash'),
                yaxis=dict(gridcolor='#484f58', gridwidth=1.5, griddash='dash')
            )
            st.plotly_chart(fig_bar, width='stretch')

with tab3:
    st.markdown("### 📋 Transaction Ledgers")
    raw_df = load_transactions_from_sheet()
    if not raw_df.empty:
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, width='stretch')
    else:
        st.info("No recorded transactions.")

with tab4:
    st.markdown("### 🧠 Smart Advisor & Profit Engine")
    
    col_adv_1, col_adv_2 = st.columns(2)
    
    with col_adv_1:
        st.markdown("#### 🤖 Smart DCA Timing & Scoring Engine")
        st.caption(f"Global Market Sentiment (Fear & Greed): **{fng_value}/100 ({fng_label})**")
        
        selected_dca_asset = st.selectbox("Select Coin to Evaluate for DCA:", list(current_values.keys()))
        test_dca_amount = st.number_input("Amount to Put ($)", value=100.0, step=10.0, key="smart_dca_amt")
        
        if selected_dca_asset and selected_dca_asset in current_values:
            stats = current_values[selected_dca_asset]
            score = stats["score"]
            reasons = []
            
            if stats['rsi'] < 30:
                reasons.append("🟢 RSI is Extreme Oversold (<30)")
            elif stats['rsi'] < 42:
                reasons.append("🟢 RSI is in Healthy Dip zone (30-42)")
            elif stats['rsi'] > 68:
                reasons.append("🔴 RSI is Overbought (>68)")
            else:
                reasons.append("🟡 RSI is Neutral")
                
            if stats['price'] <= stats['bb_lower']:
                reasons.append("🟢 Price breached Lower Bollinger Band (Statistical Dip)")
            else:
                reasons.append("🟡 Price is safely within bands")
                
            if fng_value < 30:
                reasons.append("🟢 Market is in Fear/Panic (Great for accumulation)")
            elif fng_value > 75:
                reasons.append("🔴 Market is in Extreme Greed")
            
            st.markdown(f"### Score Result: **{score} / 100**")
            
            if score >= 70:
                st.success("🟢 **STRONG BUY SIGNAL:** Εξαιρετική ευκαιρία! Η στατιστική και η τεχνική ανάλυση δείχνουν τοπικό πάτος. Βάλτα **όλα** τώρα.")
            elif score >= 45:
                st.warning("🟡 **BALANCED DCA (DCA σε δόσεις):** Η αγορά είναι ουδέτερη. Καλύτερα να βάλεις τα μισά τώρα και τα υπόλοιπα αργότερα.")
            else:
                st.error("🔴 **HOLD CASH / OVERBOUGHT:** Αποφυγή αγοράς τώρα. Η τιμή είναι ψηλά ή η τάση είναι επικίνδυνη.")
                
            with st.expander("🔍 View Technical Breakdown"):
                for r in reasons:
                    st.markdown(f"- {r}")
                    
    with col_adv_2:
        st.markdown("#### 🎯 Target Profit Extractor (Take Profit)")
        st.caption(f"Total Portfolio Net PnL: **${total_pnl_usd:+,.2f}**")
        
        target_profit_goal = st.number_input("Desired Net Profit to Extract ($)", value=200.0, step=50.0, key="target_profit_goal")
        
        if total_pnl_usd > 0:
            if target_profit_goal > total_pnl_usd:
                st.warning(f"⚠️ Ο στόχος σου (${target_profit_goal}) είναι μεγαλύτερος από το συνολικό τρέχον κέρδος σου (${total_pnl_usd:,.2f}).")
            else:
                st.markdown("##### Προτεινόμενη εκτέλεση για κατοχύρωση κέρδους:")
                
                profitable_assets = {k: v for k, v in current_values.items() if v["pnl_usd"] > 0}
                
                if profitable_assets:
                    total_prof_sum = sum(v["pnl_usd"] for v in profitable_assets.values())
                    
                    extract_data = []
                    for asset, stats in profitable_assets.items():
                        weight = stats["pnl_usd"] / total_prof_sum
                        dollar_to_pull = target_profit_goal * weight
                        amount_to_sell = dollar_to_pull / stats["price"]
                        
                        total_holding_amount = portfolio_data[asset]["amount"]
                        pct_of_holding = (amount_to_sell / total_holding_amount) * 100 if total_holding_amount > 0 else 0
                        
                        extract_data.append({
                            "Coin": asset,
                            "Sell Amount": f"{amount_to_sell:.6f} {asset}",
                            "% of Holding": f"{pct_of_holding:.1f}%",
                            "Est. Cash Back": f"${dollar_to_pull:,.2f}",
                            "Current Price": f"${stats['price']:,.2f}"
                        })
                        
                    st.table(pd.DataFrame(extract_data))
                    st.info("💡 Σου δείχνει ακριβώς πόσο ποσοστό (%) από τη θέση κάθε coin πρέπει να πουλήσεις για να πιάσεις καθαρό κέρδος τον στόχο σου.")
                else:
                    st.warning("Δεν υπάρχουν κερδοφόρα coins αυτή τη στιγμή για πώληση.")
        else:
            st.error("Το συνολικό χαρτοφυλάκιο είναι σε αρνητικό PnL, οπότε δεν υπάρχει κέρδος προς κατοχύρωση.")

with tab5:
    st.markdown("### 🛡️ Risk & Exit Strategy Terminal")
    calc_basis = st.radio("Calculation Basis:", ["Current Price (Dynamic)", "Average Cost (Static)"], horizontal=True)
    
    st.markdown("---")
    
    risk_table_data = []
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 0:
            continue
        stats = current_values[asset]
        curr_p = stats['price']
        avg_p = stats['avg_price']
        total_amt = data['amount']
        total_cst = data['total_cost']
        
        base_price = curr_p if "Current" in calc_basis else avg_p
        basis_label = "Current Price" if "Current" in calc_basis else "Avg Cost"
        
        with st.container():
            st.markdown(f"""
                <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <h3 style="margin-top: 0; color: #58a6ff; margin-bottom: 12px;">🪙 {asset}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            c_left, c_mid, c_right = st.columns([1.2, 2.4, 2.4])
            
            with c_left:
                st.markdown(f"**Current Price:** `${curr_p:,.2f}`")
                st.markdown(f"**Avg Cost:** `${avg_p:,.2f}`")
                st.markdown(f"**Holdings:** `{total_amt:.4f}`")
                
            with c_mid:
                st.markdown(f"🔻 **Stop Loss** ({basis_label})")
                sl_pct = st.slider(f"SL %", -50.0, -1.0, -10.0, step=1.0, key=f"sl_{asset}", label_visibility="collapsed")
                sl_price = base_price * (1 + sl_pct / 100.0)
                
                sl_portfolio_value = total_amt * sl_price
                sl_pnl_usd = sl_portfolio_value - total_cst
                sl_pnl_pct = (sl_pnl_usd / total_cst) * 100 if total_cst > 0 else 0
                
                st.markdown(f"Target: <span style='color: #ff7b72; font-weight: bold;'>${sl_price:,.2f} ({sl_pct}%)</span>", unsafe_allow_html=True)
                st.markdown(f"Est. PnL: **`${sl_pnl_usd:+,.2f}` (`{sl_pnl_pct:+.2f}%`)**")
                
            with c_right:
                st.markdown(f"🎯 **Take Profit** ({basis_label})")
                tp_pct = st.slider(f"TP %", 5.0, 300.0, 50.0, step=5.0, key=f"tp_{asset}", label_visibility="collapsed")
                tp_price = base_price * (1 + tp_pct / 100.0)
                
                tp_portfolio_value = total_amt * tp_price
                tp_pnl_usd = tp_portfolio_value - total_cst
                tp_pnl_pct = (tp_pnl_usd / total_cst) * 100 if total_cst > 0 else 0
                
                st.markdown(f"Target: <span style='color: #3fb950; font-weight: bold;'>${tp_price:,.2f} (+{tp_pct}%)</span>", unsafe_allow_html=True)
                st.markdown(f"Est. PnL: **`${tp_pnl_usd:+,.2f}` (`{tp_pnl_pct:+.2f}%`)**")
            
            if curr_p <= sl_price:
                status = "🚨 STOP LOSS TRIGGERED"
            elif curr_p >= tp_price:
                status = "🎯 TAKE PROFIT REACHED"
            else:
                status = "🟢 ACTIVE"
                
            distance_to_sl_pct = ((curr_p - sl_price) / curr_p) * 100 if sl_price < curr_p else 0.0
                
            st.markdown(f"<div style='margin-top: 10px; font-size: 13px; color: #8b949e;'>Status: <b>{status}</b> | Distance to SL: <b>{distance_to_sl_pct:.1f}%</b></div>", unsafe_allow_html=True)
            st.markdown("---")
            
            risk_table_data.append({
                "Coin": asset,
                "Basis": basis_label,
                "Current Price": f"${curr_p:,.2f}",
                "Stop Loss Target": f"${sl_price:,.2f} ({sl_pct}%)",
                "SL PnL ($)": f"${sl_pnl_usd:+,.2f} ({sl_pnl_pct:+.2f}%)",
                "Take Profit Target": f"${tp_price:,.2f} (+{tp_pct}%)",
                "TP PnL ($)": f"${tp_pnl_usd:+,.2f} ({tp_pnl_pct:+.2f}%)",
                "Status": status
            })

    st.markdown("#### 🚨 Risk Alerts Summary")
    df_risk = pd.DataFrame(risk_table_data)
    if not df_risk.empty:
        for idx, row in df_risk.iterrows():
            if "TRIGGERED" in row["Status"]:
                st.error(f"🚨 **{row['Coin']}** — {row['Status']} at {row['Stop Loss Target']} | Est PnL: {row['SL PnL ($)']}")
            elif "REACHED" in row["Status"]:
                st.success(f"🎯 **{row['Coin']}** — {row['Status']} at {row['Take Profit Target']} | Est PnL: {row['TP PnL ($)']}")
                
        with st.expander("View Full Risk Parameters Matrix"):
            df_risk.index = df_risk.index + 1
            st.dataframe(df_risk, width='stretch')
