import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Crypto DCA Dashboard", layout="wide")

st.title("🤖 Crypto DCA & Smart Buy Dashboard")

# Έλεγχος και αυτόματη δημιουργία transactions.csv αν δεν υπάρχει
history_csv = "transactions.csv"
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

# Φόρτωση δεδομένων
df = pd.read_csv(history_csv)
st.subheader("📊 Τρέχουσες Συναλλαγές (transactions.csv)")
st.dataframe(df, use_container_width=True)

# Input ποσού
new_cash_to_invest = st.number_input("Συμπλήρωσε το ποσό που θέλεις να επενδύσεις σήμερα ($):", min_value=0.0, value=50.0, step=10.0)

if st.button("Εκτέλεση Υπολογισμού"):
    st.success(f"Το ποσό των ${new_cash_to_invest} καταχωρήθηκε προς ανάλυση!")
