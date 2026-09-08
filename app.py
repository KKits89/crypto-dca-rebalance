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

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="DCA Portfolio Terminal")

# --- INSTITUTIONAL / CLEAN FINTECH UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        background-color: #09090b !important;
        color: #f4f4f5 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    #MainMenu, footer, header {visibility: hidden;}

    div[data-testid="stMetric"] {
        background-color: #121215 !important;
        border: 1px solid #27272a !important;
        padding: 16px 20px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] label {
        color: #71717a !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #fafafa !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    h1, h2, h3, h4 {
        color: #fafafa !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: transparent;
        padding: 0;
        border-bottom: 1px solid #27272a;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px 6px 0 0;
        color: #a1a1aa;
        border: 1px solid transparent;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.85rem;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f4f4f5;
        background-color: #18181b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #18181b !important;
        color: #ffffff !important;
        border-color: #27272a #27272a transparent #27272a !important;
        font-weight: 600;
    }

    .stButton>button, .stDownloadButton>button {
        background-color: #18181b !important;
        color: #f4f4f5 !important;
        border: 1px solid #27272a !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.9rem !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #27272a !important;
        border-color: #3f3f46 !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #0c0c0e !important;
        border-right: 1px solid #27272a !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #27272a;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #121215 !important;
        border: 1px solid #27272a !important;
        color: #f4f4f5 !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
    }

    span[data-baseweb="tag"] {
        background-color: #18181b !important;
        color: #e4e4e7 !important;
        border: 1px solid #27272a !important;
    }
    div.stSlider > div[data-baseweb="slider"] div[role="slider"] {
        background-color: #e4e4e7 !important;
        border-color: #ffffff !important;
    }
    div.stSlider > div[data-baseweb="slider"] div > div > div {
        background-color: #3f3f46 !important;
    }
</style>
""", unsafe_allow_html=True)

# Auto-refresh every 60s
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.markdown("## Portfolio Terminal")

# --- GOOGLE SHEETS & CACHED API HELPERS ---
def get_g_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("CryptoPortfolio").sheet1 
    return sheet

@st.cache_data(ttl=15)
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
        st.error(f"Google Sheet Connection Error: {e}")
        return pd.DataFrame(columns=["Date", "Asset", "Amount", "USD_Cost"])

@st.cache_data(ttl=60)
def get_cmc_prices(symbols_list):
    if not symbols_list:
        return {}
    api_key = st.secrets.get("CMC_API_KEY", "")
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    try:
        response = requests.get(
            url, 
            headers={"Accepts": "application/json", "X-CMC_PRO_API_KEY": api_key}, 
            params={"symbol": ",".join(symbols_list), "convert": "USD"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json().get("data", {})
            return {sym: data[sym]["quote"]["USD"]["price"] for sym in symbols_list if sym in data}
    except Exception:
        pass
    return {}

@st.cache_data(ttl=300)
def get_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        data = res.json()
        return int(data["data"][0]["value"]), data["data"][0]["value_classification"]
    except Exception:
        return 50, "Neutral"

@st.cache_data(ttl=300)
def fetch_asset_technicals(asset):
    ticker_str = "HYPE32196-USD" if asset == "HYPE" else f"{asset}-USD"
    try:
        hist = yf.Ticker(ticker_str).history(period="100d")
        if hist.empty or len(hist) < 15:
            hist = yf.Ticker(f"{asset}-USD").history(period="100d")
        return hist
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_eur_rate():
    try:
        eur_ticker = yf.Ticker("EURUSD=X")
        eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
        return 1.0 / eur_rate
    except Exception:
        return 0.92

# --- LOAD DATA ONCE ---
raw_df_initial = load_transactions_from_sheet()

def get_latest_transaction_date(df):
    if not df.empty:
        for col in df.columns:
            if 'date' in col.lower():
                valid_dates = df[col].dropna()
                if not valid_dates.empty:
                    return str(valid_dates.max())
    return "N/A"

unique_assets_in_sheet = []
if not raw_df_initial.empty:
    col_asset = next((c for c in raw_df_initial.columns if 'asset' in c.lower()), 'Asset')
    unique_assets_in_sheet = [str(x).upper().strip() for x in raw_df_initial[col_asset].unique() if str(x).strip() != '']

default_slugs = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", 
    "ZEC": "zcash", "HYPE": "hyperliquid", "PUMP": "pump-fun"
}

# --- SIDEBAR: EXECUTION & CONTROL ---
st.sidebar.markdown("### Execution Panel")

new_cash_to_invest = st.sidebar.number_input("Cash to Invest ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### Transaction Entry")

latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.caption(f"Last Transaction: {latest_date}")

action_mode = st.sidebar.radio("Entry Type:", ["Standard Trade", "External Loss / Write-off"], horizontal=False)

if "Standard" in action_mode:
    tx_type = st.sidebar.radio("Direction:", ["BUY", "SELL"], horizontal=True)
    asset_input = st.sidebar.text_input("Asset Ticker", "BTC").upper().strip()
    amount_input = st.sidebar.number_input("Amount", value=0.0, format="%.6f")
    cost_input = st.sidebar.number_input("USD Total ($)", value=0.0, format="%.2f")

    if st.sidebar.button("Submit Trade"):
        if amount_input > 0 and cost_input > 0 and asset_input:
            t_date = datetime.now().strftime("%Y-%m-%d")
            final_amount = -amount_input if "SELL" in tx_type else amount_input
            final_cost = -cost_input if "SELL" in tx_type else cost_input
            
            try:
                sheet = get_g_sheet()
                sheet.append_row([t_date, asset_input, f"{final_amount:.8f}", f"{final_cost:.2f}"])
                st.cache_data.clear()
                st.sidebar.success("Transaction logged.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Execution Error: {e}")
        else:
            st.sidebar.error("Provide valid asset, amount, and cost.")
else:
    burn_asset = st.sidebar.text_input("Asset Ticker", "BTC").upper().strip()
    burn_amount = st.sidebar.number_input("Amount to Remove", value=0.0, format="%.6f")
    burn_cost_lost = st.sidebar.number_input("Cost Basis Write-off ($)", value=0.0, format="%.2f")

    if st.sidebar.button("Log Write-off"):
        if burn_amount > 0 and burn_cost_lost > 0 and burn_asset:
            t_date = datetime.now().strftime("%Y-%m-%d")
            try:
                sheet = get_g_sheet()
                sheet.append_row([t_date, burn_asset, f"-{burn_amount:.8f}", f"-{burn_cost_lost:.2f}"])
                st.cache_data.clear()
                st.sidebar.success("Write-off logged.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Ledger Management")

if not raw_df_initial.empty:
    last_row = raw_df_initial.iloc[-1]
    st.sidebar.markdown(
        f"<div style='font-size: 11px; color: #a1a1aa; background: #121215; padding: 10px; border-radius: 6px; border: 1px solid #27272a;'>"
        f"<b>Last Row:</b> {last_row.get('Date', 'N/A')} | {last_row.get('Asset', 'N/A')}<br>"
        f"<b>Amt:</b> {last_row.get('Amount', 'N/A')} | <b>Cost:</b> ${last_row.get('USD_Cost', 'N/A')}"
        f"</div>", 
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("Undo Last Entry"):
        try:
            sheet = get_g_sheet()
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                sheet.delete_rows(len(all_values))
                st.cache_data.clear()
                st.sidebar.success("Last entry removed.")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# --- TARGET ALLOCATION SETUP ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Target Weights Setup")

default_dca_selection = [ast for ast in unique_assets_in_sheet if ast != "PUMP"]
active_dca_assets = st.sidebar.multiselect(
    "Active DCA Assets:", 
    options=unique_assets_in_sheet, 
    default=default_dca_selection
)

# Fetch prices ONCE for the entire application
cmc_prices = get_cmc_prices(unique_assets_in_sheet)

# Compute current balances for slider initialization
portfolio_data = {}
temp_portfolio_vals = {}
if not raw_df_initial.empty:
    c_asset = next((c for c in raw_df_initial.columns if 'asset' in c.lower()), 'Asset')
    c_amount = next((c for c in raw_df_initial.columns if 'amount' in c.lower()), 'Amount')
    c_cost = next((c for c in raw_df_initial.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    
    summary = raw_df_initial.groupby(c_asset).agg({c_amount: 'sum', c_cost: 'sum'}).to_dict('index')
    
    for ast, dat in summary.items():
        amt = float(dat[c_amount])
        cst = float(dat[c_cost])
        portfolio_data[ast] = {
            'total_cost': cst,
            'amount': amt,
            'is_dca': ast in active_dca_assets,
            'cmc_slug': default_slugs.get(ast, ast.lower())
        }
        if amt > 1e-5:
            p = cmc_prices.get(ast, cst / amt if amt > 0 else 0)
            temp_portfolio_vals[ast] = amt * p

tot_dca_val_temp = sum(temp_portfolio_vals.get(ast, 0.0) for ast in active_dca_assets)

target_weights = {}
for asset in active_dca_assets:
    val = temp_portfolio_vals.get(asset, 0.0)
    auto_pct = (val / tot_dca_val_temp * 100.0) if tot_dca_val_temp > 0 else (100.0 / len(active_dca_assets) if active_dca_assets else 0.0)
    
    key = f"weight_{asset}"
    if key not in st.session_state:
        st.session_state[key] = float(round(auto_pct, 1))
        
    target_weights[asset] = st.sidebar.slider(f"{asset} Target %", 0.0, 100.0, key=key)

for asset in portfolio_data:
    portfolio_data[asset]['target_pct'] = (target_weights.get(asset, 0.0) / 100.0) if asset in active_dca_assets else 0.0

total_weight_sum = sum(target_weights.values())
if active_dca_assets and abs(total_weight_sum - 100.0) > 0.01:
    st.sidebar.caption(f"Warning: Sum is {total_weight_sum:.1f}% (Must equal 100%)")

# --- INDICATORS & CORE ENGINE ---
fng_value, fng_label = get_fear_and_greed()
usd_to_eur = get_eur_rate()

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
    if stats['rsi'] < 30: sc += 25
    elif stats['rsi'] < 42: sc += 15
    elif stats['rsi'] > 68: sc -= 25
    if stats['price'] <= stats['bb_lower']: sc += 20
    if fng < 30: sc += 15
    elif fng > 75: sc -= 15
    return max(0, min(100, sc))

current_values = {}
total_current_portfolio = 0.0
total_active_cost = 0.0
total_realized_pnl = 0.0

for asset, data in portfolio_data.items():
    amt = data["amount"]
    cst = data["total_cost"]
    
    if abs(amt) < 1e-5:
        total_realized_pnl -= cst
        continue 
        
    price = cmc_prices.get(asset, cst / amt if amt > 0 else 0)
    rsi, sma_50, bb_lower = 50.0, price, price * 0.95
    
    hist = fetch_asset_technicals(asset)
    if not hist.empty:
        if len(hist) >= 50:
            sma_50 = hist['Close'].tail(50).mean()
        if len(hist) >= 20:
            rm = hist['Close'].rolling(window=20).mean().iloc[-1]
            rsd = hist['Close'].rolling(window=20).std().iloc[-1]
            bb_lower = rm - (2 * rsd)
        if len(hist) >= 15:
            rsi_series = get_rsi(hist['Close'])
            if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]):
                rsi = float(rsi_series.iloc[-1])

    val = amt * price
    avg_price = (cst / amt) if amt > 0 else 0
    pnl_usd = val - cst
    pnl_pct = (pnl_usd / cst) * 100 if cst > 0 else 0

    temp_stats = {
        "price": price, "avg_price": avg_price, "current_val": val,
        "pnl_usd": pnl_usd, "pnl_pct": pnl_pct, "sma_50": sma_50,
        "bb_lower": bb_lower, "rsi": rsi
    }
    temp_stats["score"] = compute_smart_score(temp_stats, fng_value)

    current_values[asset] = temp_stats
    total_current_portfolio += val
    total_active_cost += cst

total_invested_cost = total_active_cost
new_total_portfolio = total_current_portfolio + new_cash_to_invest
tot_eur = total_current_portfolio * usd_to_eur

total_unrealized_pnl = total_current_portfolio - total_active_cost
total_pnl_usd = total_unrealized_pnl + total_realized_pnl
pnl_eur = total_pnl_usd * usd_to_eur
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100 if total_invested_cost > 0 else 0

# Allocations
strict_allocations = {}
for asset, data in portfolio_data.items():
    if data["amount"] <= 1e-5 or not data["is_dca"] or asset not in current_values:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    strict_allocations[asset] = max(0, ideal_val - cur_val)

total_strict_weight = sum(strict_allocations.values()) or 1.0

smart_allocations = {}
total_smart_weight = 0
for asset, data in portfolio_data.items():
    if data["amount"] <= 1e-5 or not data["is_dca"] or asset not in current_values:
        continue
    cur_val = current_values[asset]["current_val"]
    ideal_val = new_total_portfolio * data["target_pct"]
    base_need = max(0, ideal_val - cur_val)
    score = current_values[asset]["score"]
    smart_weight = base_need * max(0.1, score / 50.0)
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

total_smart_weight = total_smart_weight or 1.0

# --- MAIN NAVIGATION TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Analytics", "Ledgers & Export", "Smart Advisor", "Risk & Exit Laddering"
])

# --- TAB 1: OVERVIEW ---
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Portfolio Value", f"${total_current_portfolio:,.2f}", f"€{tot_eur:,.2f}")
    c2.metric("Net Realized & Unrealized PnL", f"${total_pnl_usd:+,.2f}", f"{total_pnl_pct:+.2f}% ({pnl_eur:+,.2f}€)")
    c3.metric("Allocatable Cash", f"${new_cash_to_invest:,.2f}")

    st.markdown("---")
    st.markdown("##### Portfolio Positions & Allocation Matrix")

    table_data = []
    for asset, data in portfolio_data.items():
        if data["amount"] <= 1e-5 or asset not in current_values:
            continue
        stats = current_values[asset]
        
        if data["is_dca"]:
            strict_buy = new_cash_to_invest * (strict_allocations.get(asset, 0) / total_strict_weight)
            smart_buy = new_cash_to_invest * (smart_allocations.get(asset, 0) / total_smart_weight)
            new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
            strict_str = f"${strict_buy:.2f}"
            smart_str = f"${smart_buy:.2f}"
            new_avg_str = f"${new_avg:.2f}"
        else:
            strict_str = "N/A (External)"
            smart_str = "N/A (External)"
            new_avg_str = f"${stats['avg_price']:.2f}"

        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"
        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Coin": cmc_url,
            "Asset": asset,
            "Invested_Numeric": data['total_cost'],
            "Holdings": f"{data['amount']:.6f} (${data['total_cost']:.2f})",
            "Avg Price": f"${stats['avg_price']:.2f}",
            "New Avg": new_avg_str,
            "Current Price": f"${stats['price']:.2f}",
            "RSI (14)": f"{stats['rsi']:.1f}",
            "PnL": pnl_str,
            "Strict Buy": strict_str,
            "Smart Buy": smart_str
        })

    df_metrics = pd.DataFrame(table_data)
    if not df_metrics.empty:
        df_metrics = df_metrics.sort_values(by="Invested_Numeric", ascending=False).drop(columns=["Invested_Numeric"])
        df_metrics.index = range(1, len(df_metrics) + 1)
    
    st.dataframe(
        df_metrics,
        width='stretch',
        column_config={
            "Coin": st.column_config.LinkColumn("Coin Link", display_text=r"https://coinmarketcap.com/currencies/(.*?)/"),
            "Asset": None
        }
    )

# --- TAB 2: ANALYTICS ---
with tab2:
    st.markdown("##### Historical Performance Timeline")
    if not raw_df_initial.empty:
        try:
            date_col = next((c for c in raw_df_initial.columns if 'date' in c.lower()), None)
            cost_col = next((c for c in raw_df_initial.columns if 'cost' in c.lower() or 'usd' in c.lower()), None)
            
            if date_col and cost_col:
                raw_tx_df = raw_df_initial.copy()
                raw_tx_df[date_col] = pd.to_datetime(raw_tx_df[date_col])
                daily_costs = raw_tx_df.groupby(date_col)[cost_col].sum().reset_index().sort_values(by=date_col)
                daily_costs['Cumulative_Cost'] = daily_costs[cost_col].cumsum()
                
                full_calendar = pd.date_range(start=daily_costs[date_col].min(), end=pd.to_datetime(datetime.now().strftime("%Y-%m-%d")))
                timeline_df = pd.merge(pd.DataFrame({date_col: full_calendar}), daily_costs[[date_col, 'Cumulative_Cost']], on=date_col, how='left')
                timeline_df['Cumulative_Cost'] = timeline_df['Cumulative_Cost'].ffill().fillna(0)
                
                days_count = len(timeline_df)
                cost_start = timeline_df['Cumulative_Cost'].iloc[0] if days_count > 0 else 1
                timeline_df['Portfolio_Value'] = np.linspace(cost_start, total_current_portfolio, days_count)

                fig_timeline = go.Figure()
                fig_timeline.add_trace(go.Scatter(x=timeline_df[date_col], y=timeline_df['Cumulative_Cost'], mode='lines', name='Basis Cost ($)', line=dict(color='#71717a', width=1.5)))
                fig_timeline.add_trace(go.Scatter(x=timeline_df[date_col], y=timeline_df['Portfolio_Value'], mode='lines', name='Market Value ($)', line=dict(color='#3b82f6', width=2), fill='tonexty', fillcolor='rgba(59, 130, 246, 0.05)'))
                fig_timeline.update_layout(paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5", hovermode="x unified", xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
                st.plotly_chart(fig_timeline, width='stretch')
        except Exception:
            pass

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if current_values:
            fig_pie = px.pie(names=list(current_values.keys()), values=[info["current_val"] for info in current_values.values()], title="Asset Share", hole=0.45)
            fig_pie.update_layout(paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5")
            st.plotly_chart(fig_pie, width='stretch')
        
    with col_chart2:
        if current_values:
            assets_list = list(current_values.keys())
            pnl_vals = [info["pnl_usd"] for info in current_values.values()]
            colors = ['#10b981' if v >= 0 else '#ef4444' for v in pnl_vals]
            fig_bar = go.Figure(data=[go.Bar(x=assets_list, y=pnl_vals, marker_color=colors)])
            fig_bar.update_layout(title="Net PnL per Asset ($)", paper_bgcolor="#09090b", plot_bgcolor="#121215", font_color="#f4f4f5", xaxis=dict(gridcolor='#27272a'), yaxis=dict(gridcolor='#27272a'))
            st.plotly_chart(fig_bar, width='stretch')

# --- TAB 3: LEDGERS & EXPORT ---
with tab3:
    st.markdown("##### Raw Transaction Ledger & Data Export")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if not raw_df_initial.empty:
            csv_ledger = raw_df_initial.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Transaction Ledger (CSV)",
                data=csv_ledger,
                file_name=f"crypto_ledger_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col_exp2:
        if not df_metrics.empty:
            csv_summary = df_metrics.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Portfolio Summary (CSV)",
                data=csv_summary,
                file_name=f"portfolio_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    st.markdown("---")
    if not raw_df_initial.empty:
        display_df = raw_df_initial.copy()
        display_df.index = display_df.index + 1
        st.dataframe(display_df, width='stretch')

# --- TAB 4: SMART ADVISOR ---
with tab4:
    col_adv_1, col_adv_2 = st.columns(2)
    with col_adv_1:
        st.markdown("##### Smart DCA Engine")
        st.caption(f"Fear & Greed Index: {fng_value}/100 ({fng_label})")
        selected_dca_asset = st.selectbox("Select Asset to Evaluate:", list(current_values.keys()) if current_values else ["BTC"])
        
        if selected_dca_asset and selected_dca_asset in current_values:
            stats = current_values[selected_dca_asset]
            score = stats["score"]
            st.markdown(f"#### Score: `{score} / 100`")
            if score >= 70:
                st.success("Strong Accumulation Zone (High Dip Potential)")
            elif score >= 45:
                st.info("Neutral Market Conditions (Standard DCA)")
            else:
                st.warning("Overbought / Hold Cash Zone")
                    
    with col_adv_2:
        st.markdown("##### Target Profit Extractor")
        target_profit_goal = st.number_input("Desired Profit Extraction ($)", value=200.0, step=50.0)
        if total_pnl_usd > 0:
            profitable_assets = {k: v for k, v in current_values.items() if v["pnl_usd"] > 0}
            if profitable_assets:
                total_prof_sum = sum(v["pnl_usd"] for v in profitable_assets.values())
                extract_data = []
                for asset, stats in profitable_assets.items():
                    dollar_to_pull = target_profit_goal * (stats["pnl_usd"] / total_prof_sum)
                    amount_to_sell = dollar_to_pull / stats["price"] if stats["price"] > 0 else 0
                    holding_amt = portfolio_data[asset]["amount"]
                    pct_of_holding = (amount_to_sell / holding_amt * 100) if holding_amt > 0 else 0
                    
                    extract_data.append({
                        "Asset": asset,
                        "Sell Amount": f"{amount_to_sell:.6f} {asset}",
                        "% of Holding": f"{pct_of_holding:.1f}%",
                        "Cash Proceeds": f"${dollar_to_pull:,.2f}"
                    })
                st.table(pd.DataFrame(extract_data))

# --- TAB 5: RISK & TAKE-PROFIT LADDERING ---
with tab5:
    st.markdown("##### Take-Profit Laddering Strategy")
    st.caption("Ορίστε σταδιακά επίπεδα πωλήσεων (Laddering) για να κλειδώνετε κέρδη με βάση το πλάνο σας.")

    active_assets_list = [a for a in current_values.keys() if current_values[a]["current_val"] > 0]
    
    if active_assets_list:
        tp_asset = st.selectbox("Select Asset for Take-Profit Plan:", active_assets_list)
        asset_stats = current_values[tp_asset]
        current_holdings = portfolio_data[tp_asset]["amount"]
        current_price = asset_stats["price"]
        
        col_l1, col_l2, col_l3 = st.columns(3)
        
        with col_l1:
            st.markdown("**Tier 1**")
            tp1_gain = st.number_input("Target 1 Gain %", value=30.0, step=5.0, key="tp1_g")
            tp1_sell_pct = st.number_input("Sell % of Holdings (T1)", value=25.0, step=5.0, key="tp1_s")
            
        with col_l2:
            st.markdown("**Tier 2**")
            tp2_gain = st.number_input("Target 2 Gain %", value=70.0, step=5.0, key="tp2_g")
            tp2_sell_pct = st.number_input("Sell % of Holdings (T2)", value=35.0, step=5.0, key="tp2_s")

        with col_l3:
            st.markdown("**Tier 3**")
            tp3_gain = st.number_input("Target 3 Gain %", value=150.0, step=10.0, key="tp3_g")
            tp3_sell_pct = st.number_input("Sell % of Holdings (T3)", value=40.0, step=5.0, key="tp3_s")

        ladders = [
            ("Tier 1", tp1_gain, tp1_sell_pct),
            ("Tier 2", tp2_gain, tp2_sell_pct),
            ("Tier 3", tp3_gain, tp3_sell_pct)
        ]
        
        ladder_results = []
        rem_coins = current_holdings
        
        for name, gain, sell_p in ladders:
            target_p = current_price * (1 + gain / 100.0)
            coins_to_sell = current_holdings * (sell_p / 100.0)
            usd_proceeds = coins_to_sell * target_p
            rem_coins -= coins_to_sell
            
            ladder_results.append({
                "Level": name,
                "Target Price ($)": f"${target_p:,.2f} (+{gain:.0f}%)",
                "Coins to Sell": f"{coins_to_sell:.6f} {tp_asset}",
                "Cash Out ($)": f"${usd_proceeds:,.2f}",
                "Remaining Balance": f"{max(0, rem_coins):.6f} {tp_asset}"
            })
            
        st.markdown("###### Laddering Execution Schedule")
        st.table(pd.DataFrame(ladder_results))

    st.markdown("---")
    st.markdown("##### Standard Stop Loss & Take Profit Thresholds")
    calc_basis = st.radio("Basis:", ["Current Price", "Average Cost"], horizontal=True)
    
    for asset, data in portfolio_data.items():
        if data["amount"] <= 1e-5 or asset not in current_values:
            continue
        stats = current_values[asset]
        base_price = stats['price'] if "Current" in calc_basis else stats['avg_price']
        
        c_left, c_mid, c_right = st.columns([1.2, 2.4, 2.4])
        with c_left:
            st.markdown(f"**{asset}** | Price: `${stats['price']:,.2f}`")
        with c_mid:
            sl_pct = st.slider(f"SL % {asset}", -50.0, -1.0, -10.0, step=1.0, key=f"sl_{asset}", label_visibility="collapsed")
            sl_price = base_price * (1 + sl_pct / 100.0)
            st.markdown(f"SL: `${sl_price:,.2f}` ({sl_pct}%)")
        with c_right:
            tp_pct = st.slider(f"TP % {asset}", 5.0, 300.0, 50.0, step=5.0, key=f"tp_{asset}", label_visibility="collapsed")
            tp_price = base_price * (1 + tp_pct / 100.0)
            st.markdown(f"TP: `${tp_price:,.2f}` (+{tp_pct}%)")
