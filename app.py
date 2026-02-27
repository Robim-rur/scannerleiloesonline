import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Scanner – Keltner + Regressão (slope) + ATR%")
st.caption("Diário com confirmação semanal rígida | Long only | Apenas candle fechado")

# =====================================================
# LISTAS DE ATIVOS
# =====================================================

acoes_100 = [
    "RRRP3.SA","ALOS3.SA","ALPA4.SA","ABEV3.SA","ARZZ3.SA","ASAI3.SA","AZUL4.SA","B3SA3.SA","BBAS3.SA","BBDC3.SA",
    "BBDC4.SA","BBSE3.SA","BEEF3.SA","BPAC11.SA","BRAP4.SA","BRFS3.SA","BRKM5.SA","CCRO3.SA","CMIG4.SA","CMIN3.SA",
    "COGN3.SA","CPFE3.SA","CPLE6.SA","CRFB3.SA","CSAN3.SA","CSNA3.SA","CYRE3.SA","DXCO3.SA","EGIE3.SA","ELET3.SA",
    "ELET6.SA","EMBR3.SA","ENEV3.SA","ENGI11.SA","EQTL3.SA","EZTC3.SA","FLRY3.SA","GGBR4.SA","GOAU4.SA","GOLL4.SA",
    "HAPV3.SA","HYPE3.SA","ITSA4.SA","ITUB4.SA","JBSS3.SA","KLBN11.SA","LREN3.SA","LWSA3.SA","MGLU3.SA","MRFG3.SA",
    "MRVE3.SA","MULT3.SA","NTCO3.SA","PETR3.SA","PETR4.SA","PRIO3.SA","RADL3.SA","RAIL3.SA","RAIZ4.SA","RENT3.SA",
    "RECV3.SA","SANB11.SA","SBSP3.SA","SLCE3.SA","SMTO3.SA","SUZB3.SA","TAEE11.SA","TIMS3.SA","TOTS3.SA","TRPL4.SA",
    "UGPA3.SA","USIM5.SA","VALE3.SA","VIVT3.SA","VIVA3.SA","WEGE3.SA","YDUQ3.SA","AURE3.SA","BHIA3.SA","CASH3.SA",
    "CVCB3.SA","DIRR3.SA","ENAT3.SA","GMAT3.SA","IFCM3.SA","INTB3.SA","JHSF3.SA","KEPL3.SA","MOVI3.SA","ORVR3.SA",
    "PETZ3.SA","PLAS3.SA","POMO4.SA","POSI3.SA","RANI3.SA","RAPT4.SA","STBP3.SA","TEND3.SA","TUPY3.SA",
    "BRSR6.SA","CXSE3.SA"
]

bdrs_fii = [
    "AAPL34.SA","AMZO34.SA","GOGL34.SA","MSFT34.SA","TSLA34.SA","META34.SA","NFLX34.SA","NVDC34.SA","MELI34.SA",
    "BABA34.SA","DISB34.SA","PYPL34.SA","JNJB34.SA","PGCO34.SA","KOCH34.SA","VISA34.SA","WMTB34.SA","NIKE34.SA",
    "ADBE34.SA","AVGO34.SA","CSCO34.SA","COST34.SA","CVSH34.SA","GECO34.SA","GSGI34.SA","HDCO34.SA","INTC34.SA",
    "JPMC34.SA","MAEL34.SA","MCDP34.SA","MDLZ34.SA","MRCK34.SA","ORCL34.SA","PEP334.SA","PFIZ34.SA","PMIC34.SA",
    "QCOM34.SA","SBUX34.SA","TGTB34.SA","TMOS34.SA","TXN34.SA","UNHH34.SA","UPSB34.SA","VZUA34.SA",
    "ABTT34.SA","AMGN34.SA","AXPB34.SA","BAOO34.SA","CATP34.SA","HONB34.SA",
    "BOVA11.SA","IVVB11.SA","SMAL11.SA","HASH11.SA","GOLD11.SA","GARE11.SA","HGLG11.SA","XPLG11.SA","VILG11.SA",
    "BRCO11.SA","BTLG11.SA","XPML11.SA","VISC11.SA","HSML11.SA","MALL11.SA","KNRI11.SA","JSRE11.SA","PVBI11.SA",
    "HGRE11.SA","MXRF11.SA","KNCR11.SA","KNIP11.SA","CPTS11.SA","IRDM11.SA"
]

ativos = sorted(list(set(acoes_100 + bdrs_fii)))

# =====================================================
# FUNÇÕES
# =====================================================

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def atr(df, n=10):
    high = df["High"]
    low = df["Low"]
    close = df["Close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low - close).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(n).mean()

def linear_slope(series, window=20):
    slopes = [np.nan] * len(series)
    for i in range(window, len(series)):
        y = series.iloc[i-window:i].values
        x = np.arange(len(y))
        coef = np.polyfit(x, y, 1)[0]
        slopes[i] = coef
    return pd.Series(slopes, index=series.index)

def preparar_indicadores(df):

    df = df.copy()

    df["EMA20"] = ema(df["Close"], 20)
    df["ATR"] = atr(df, 10)

    df["KC_UP"] = df["EMA20"] + 2 * df["ATR"]
    df["KC_LO"] = df["EMA20"] - 2 * df["ATR"]

    df["SLOPE"] = linear_slope(df["Close"], 20)
    df["ATR_PCT"] = (df["ATR"] / df["Close"]) * 100

    return df

def sinal_setup(df):

    cond1 = df["Close"] > df["EMA20"]
    cond2 = df["Close"].shift(1) <= df["EMA20"].shift(1)
    cond3 = df["SLOPE"] > 0
    cond4 = (df["ATR_PCT"] > 1) & (df["ATR_PCT"] < 8)

    return cond1 & cond2 & cond3 & cond4

# =====================================================
# EXECUÇÃO
# =====================================================

st.write("Buscando sinais (diário + semanal rígido)...")

resultados = []

barra = st.progress(0)

for i, ticker in enumerate(ativos):

    barra.progress((i + 1) / len(ativos))

    try:

        df = yf.download(ticker, period="8y", interval="1d", progress=False)

        if df.empty or len(df) < 300:
            continue

        df.dropna(inplace=True)

        # Remove candle do dia em formação (para quem opera à noite/sábado)
        if df.index[-1].date() == datetime.today().date():
            df = df.iloc[:-1]

        # ======================
        # Diário
        # ======================

        daily = preparar_indicadores(df)
        sinal_diario = sinal_setup(daily)

        # ======================
        # Semanal (setup completo também)
        # ======================

        weekly = daily.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last"
        })

        weekly = preparar_indicadores(weekly)
        sinal_semanal = sinal_setup(weekly)

        # Alinha semanal ao diário
        sinal_semanal_alinhado = sinal_semanal.reindex(daily.index, method="ffill")

        # ======================
        # Sinal final
        # ======================

        sinal_final = sinal_diario & sinal_semanal_alinhado

        # verifica somente o último candle fechado
        if sinal_final.iloc[-1]:

            resultados.append({
                "Ativo": ticker,
                "Fechamento": round(daily["Close"].iloc[-1], 2),
                "Slope": round(daily["SLOPE"].iloc[-1], 5),
                "ATR%": round(daily["ATR_PCT"].iloc[-1], 2)
            })

    except Exception:
        continue

barra.empty()

if len(resultados) == 0:
    st.warning("Nenhum ativo gerou sinal com confirmação semanal rígida.")
    st.stop()

df_res = pd.DataFrame(resultados)

st.subheader("Ativos com sinal válido (diário + semanal rígido)")
st.dataframe(df_res, use_container_width=True)
