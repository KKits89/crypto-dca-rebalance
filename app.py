import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

# --- ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ ---
st.set_page_config(layout="wide", page_title="Crypto DCA Pro Dashboard")

# --- ΑΥΤΟΜΑΤΗ ΑΝΑΝΕΩΣΗ ΑΝΑ 30 ΔΕΥΤΕΡΟΛΕΠΤΑ ---
st_autorefresh(interval=30 * 1000, key="datarefresh")

st.title("🚀 Crypto DCA & Smart Buy Pro Dashboard")

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
    return "Καμία"

# --- SIDEBAR: ΡΥΘΜΙΣΕΙΣ & ΚΑΤΑΧΩΡΗΣΗ ---
st.sidebar.title("🤖 DCA Settings")

new_cash_to_invest = st.sidebar.number_input("Cash to Invest Today ($)", value=0.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📝 Add New Transaction")

raw_df_initial = load_transactions_from_sheet()
latest_date = get_latest_transaction_date(raw_df_initial)
st.sidebar.info(f"📅 Τελευταία συναλλαγή: **{latest_date}**")

asset_input = st.sidebar.text_input("Asset (π.χ. BTC ή XRP)", "BTC").upper().strip()
amount_input = st.sidebar.number_input("Amount Bought", value=0.0, format="%.6f")
cost_input = st.sidebar.number_input("USD Cost ($)", value=0.0, format="%.2f")

if st.sidebar.button("Save Transaction"):
    if amount_input > 0 and cost_input > 0 and asset_input:
        t_date = datetime.now().strftime("%Y-%m-%d")
        try:
            sheet = get_g_sheet()
            sheet.append_row([t_date, asset_input, amount_input, cost_input])
            st.cache_data.clear()  # Καθαρισμός cache για άμεση ανάγνωση
            st.sidebar.success(f"Καταγράφηκε επιτυχώς στο Google Sheet: {amount_input} {asset_input}!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Σφάλμα αποθήκευσης: {e}")
    else:
        st.sidebar.error("Συμπλήρωσε νόμισμα, ποσό και κόστος μεγαλύτερο από 0.")

# --- ΔΙΚΛΕΙΔΑ ΑΣΦΑΛΕΙΑΣ: ΕΜΦΑΝΙΣΗ & UNDO ΤΕΛΕΥΤΑΙΑΣ ΕΓΓΡΑΦΗΣ ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Safety Check / Undo")

raw_df_check = load_transactions_from_sheet()

if not raw_df_check.empty:
    last_row = raw_df_check.iloc[-1]
    st.sidebar.markdown(
        f"**Τελευταία καταχώρηση στη βάση:**\n"
        f"- Ημ/νία: `{last_row.get('Date', 'N/A')}`\n"
        f"- Νόμισμα: `{last_row.get('Asset', 'N/A')}`\n"
        f"- Ποσό: `{last_row.get('Amount', 'N/A')}`\n"
        f"- Κόστος: `${last_row.get('USD_Cost', 'N/A')}`"
    )
    
    if st.sidebar.button("🗑️ Διαγραφή Τελευταίας (Undo)"):
        try:
            sheet = get_g_sheet()
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                row_to_delete = len(all_values)
                sheet.delete_rows(row_to_delete)
                st.cache_data.clear()  # Καθαρισμός cache
                st.sidebar.success("Η τελευταία συναλλαγή διαγράφηκε επιτυχώς!")
                st.rerun()
            else:
                st.sidebar.warning("Δεν υπάρχουν άλλες συναλλαγές για διαγραφή (έμειναν τα headers).")
        except Exception as e:
            st.sidebar.error(f"Σφάλμα κατά τη διαγραφή: {e}")

# --- ΔΙΑΒΑΣΜΑ ΠΟΡΤΟΦΟΛΙΟΥ ΑΠΟ ΤΟ GOOGLE SHEET ---
def load_portfolio():
    df = load_transactions_from_sheet()
    if df.empty:
        return {}
    
    col_asset = next((c for c in df.columns if 'asset' in c.lower()), 'Asset')
    col_amount = next((c for c in df.columns if 'amount' in c.lower()), 'Amount')
    col_cost = next((c for c in df.columns if 'cost' in c.lower() or 'usd' in c.lower()), 'USD_Cost')
    
    summary = df.groupby(col_asset).agg({col_amount: 'sum', col_cost: 'sum'}).to_dict('index')

    default_settings = {
        "BTC": {"target_pct": 0.55, "cmc_slug": "bitcoin"},
        "ETH": {"target_pct": 0.20, "cmc_slug": "ethereum"},
        "SOL": {"target_pct": 0.15, "cmc_slug": "solana"},
        "ZEC": {"target_pct": 0.05, "cmc_slug": "zcash"},
        "HYPE": {"target_pct": 0.05, "cmc_slug": "hyperliquid"}
    }

    formatted_summary = {}
    for asset, data in summary.items():
        formatted_summary[asset] = {
            'total_cost': data[col_cost],
            'amount': data[col_amount]
        }
        if asset in default_settings:
            formatted_summary[asset].update(default_settings[asset])
        else:
            formatted_summary[asset]['target_pct'] = 0.0
            formatted_summary[asset]['cmc_slug'] = asset.lower()
            
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

all_symbols = list(portfolio_data.keys())
cmc_prices = get_cmc_prices(all_symbols) if all_symbols else {}

def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_new_avg(old_cost, old_amount, new_money, current_price):
    if new_money <= 0 or current_price <= 0:
        return old_cost / old_amount if old_amount > 0 else 0
    new_amount = new_money / current_price
    return (old_cost + new_money) / (old_amount + new_amount)

try:
    eur_ticker = yf.Ticker("EURUSD=X")
    eur_rate = eur_ticker.history(period="1d")['Close'].iloc[-1]
    usd_to_eur = 1.0 / eur_rate
except:
    usd_to_eur = 0.92

current_values = {}
total_current_portfolio = 0
total_invested_cost = sum(d["total_cost"] for d in portfolio_data.values()) if portfolio_data else 0

for asset, data in portfolio_data.items():
    price = cmc_prices.get(asset, data["total_cost"] / data["amount"] if data["amount"] > 0 else 0)
    
    try:
        hist = yf.Ticker(f"{asset}-USD").history(period="100d")
        sma_50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else price
        rsi = get_rsi(hist['Close']).iloc[-1] if len(hist) >= 15 else 50.0
    except:
        sma_50 = price
        rsi = 50.0

    val = data["amount"] * price
    avg_price = (data["total_cost"] / data["amount"]) if data["amount"] > 0 else 0
    pnl_usd = val - data["total_cost"]
    pnl_pct = (pnl_usd / data["total_cost"]) * 100 if data["total_cost"] > 0 else 0
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
total_pnl_pct = (total_pnl_usd / total_invested_cost) * 100 if total_invested_cost > 0 else 0

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
        base_bonus = min(abs(pnl) / total_current_portfolio * 2, 0.5) if total_current_portfolio > 0 else 0
        rsi_multiplier = 1.3 if stats["rsi"] < 40 else 1.0
        pnl_weight = 1.0 + (base_bonus * rsi_multiplier)
    else:
        pnl_weight = 1.0

    smart_weight = base_need * pnl_weight
    smart_allocations[asset] = smart_weight
    total_smart_weight += smart_weight

if total_smart_weight == 0:
    total_smart_weight = 1.0

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
        
        new_avg = calculate_new_avg(data['total_cost'], data['amount'], smart_buy, stats['price'])
        pnl_str = f"{stats['pnl_usd']:+.2f}$ ({stats['pnl_pct']:+.2f}%)"

        slug = data.get("cmc_slug", asset.lower())
        cmc_url = f"https://coinmarketcap.com/currencies/{slug}/"

        table_data.append({
            "Asset": cmc_url,
            "Name": asset,
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
            "Asset": st.column_config.LinkColumn(
                "Asset",
                help="Κλικ για τα γραφήματα στο CoinMarketCap",
                display_text=r"https://coinmarketcap.com/currencies/(.*?)/"
            ),
            "Name": None
        }
    )

with tab2:
    st.subheader("📈 Interactive Portfolio Charts (Plotly)")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if current_values:
            fig_pie = px.pie(
                names=list(current_values.keys()),
                values=[info["current_val"] for info in current_values.values()],
                title="Portfolio Distribution",
                hole=0.4
            )
            fig_pie.update_layout(paper_bgcolor="#1e1e1e", font_color="white")
            st.plotly_chart(fig_pie, width='stretch')
        else:
            st.info("Δεν υπάρχουν δεδομένα για γράφημα.")
        
    with col_chart2:
        if current_values:
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
            st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("Δεν υπάρχουν δεδομένα για γράφημα.")

with tab3:
    st.subheader("📋 Transactions History (Google Sheet)")
    raw_df = load_transactions_from_sheet()
    if not raw_df.empty:
        raw_df.index = raw_df.index + 1
        st.dataframe(raw_df, width='stretch')
    else:
        st.info("Δεν υπάρχουν αποθηκευμένες συναλλαγές.")

with tab4:
    st.subheader("🛠 Pro Simulator: Dynamic Rebalancing")
    st.markdown("Πειραματίσου με τα ποσοστά στόχου και δες πώς αλλάζει το Average Price σου!")
    
    sim_cash = st.number_input("Simulation Cash ($)", value=100.0, step=10.0, key="sim_cash")
    
    new_targets = {}
    col_s1, col_s2 = st.columns(2)
    
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
