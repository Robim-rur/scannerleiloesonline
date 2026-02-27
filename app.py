import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("Scanner – Keltner + Slope + EMA 169 | Diário + filtro semanal EMA 169 | Long only")

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

ativos = sorted(set(acoes_100 + bdrs_fii))

# =====================================================
# PARÂMETROS
# =====================================================

ema_period = 169
keltner_period = 20
keltner_mult = 2
slope_period = 20

# =====================================================
# FUNÇÕES
# =====================================================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period=10):
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def linear_regression_slope(series, window):
    slopes = [np.nan] * window
    for i in range(window, len(series)):
        y = series[i-window:i].values
        x = np.arange(window)
        slope, _ = np.polyfit(x, y, 1)
        slopes.append(slope)
    return pd.Series(slopes, index=series.index)

# =====================================================
# PROCESSAMENTO
# =====================================================

resultado = []

progress = st.progress(0)
total = len(ativos)

for i, ticker in enumerate(ativos):

    try:
        # -----------------------
        # Diário
        # -----------------------
        df = yf.download(ticker, period="18mo", interval="1d", progress=False)

        if df.empty or len(df) < 220:
            continue

        df["EMA169"] = ema(df["Close"], ema_period)

        atr_k = atr(df, 10)

        df["KC_Middle"] = ema(df["Close"], keltner_period)
        df["KC_Upper"] = df["KC_Middle"] + keltner_mult * atr_k
        df["KC_Lower"] = df["KC_Middle"] - keltner_mult * atr_k

        df["Slope"] = linear_regression_slope(df["Close"], slope_period)

        d = df.iloc[-1]

        # -----------------------
        # Semanal
        # -----------------------
        dfw = yf.download(ticker, period="5y", interval="1wk", progress=False)

        if dfw.empty or len(dfw) < 180:
            continue

        dfw["EMA169"] = ema(dfw["Close"], ema_period)

        w = dfw.iloc[-1]

        # -----------------------
        # CONDIÇÕES
        # -----------------------

        cond_diario_ema = d["Close"] > d["EMA169"]
        cond_keltner = d["Close"] > d["KC_Middle"]
        cond_slope = d["Slope"] > 0

        cond_semanal = w["Close"] > w["EMA169"]

        if cond_diario_ema and cond_keltner and cond_slope and cond_semanal:

            resultado.append({
                "Ativo": ticker.replace(".SA",""),
                "Fechamento": round(d["Close"], 2),
                "EMA169 (D)": round(d["EMA169"], 2),
                "Keltner médio": round(d["KC_Middle"], 2),
                "Slope": round(d["Slope"], 5),
                "Fech. semanal": round(w["Close"], 2),
                "EMA169 (W)": round(w["EMA169"], 2)
            })

    except:
        pass

    progress.progress((i + 1) / total)

# =====================================================
# RESULTADO
# =====================================================

st.subheader("Ativos aprovados – Keltner + Slope + EMA169 (D) com filtro EMA169 (W)")

if len(resultado) == 0:
    st.warning("Nenhum ativo passou no setup hoje.")
else:
    df_res = pd.DataFrame(resultado).sort_values(by="Slope", ascending=False)
    st.dataframe(df_res, use_container_width=True)
