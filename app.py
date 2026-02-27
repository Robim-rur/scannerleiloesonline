import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("Scanner Swing Trade – Ranking por Probabilidade (Gain antes do Loss)")
st.caption("Setup: Keltner Channel + Regressão Linear (slope) + ATR% | Diário com confirmação no semanal | Long only")

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

ativos = acoes_100 + bdrs_fii

# =====================================================
# INDICADORES
# =====================================================

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def atr(df, n=20):
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - df["Close"].shift()).abs()
    tr3 = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def keltner(df, ema_period=20, atr_period=20, mult=2):
    mid = ema(df["Close"], ema_period)
    at = atr(df, atr_period)
    upper = mid + mult * at
    lower = mid - mult * at
    return mid, upper, lower

def linreg_slope(series, n=40):
    y = series.values[-n:]
    x = np.arange(n)
    if len(y) < n:
        return np.nan
    slope, _ = np.polyfit(x, y, 1)
    return slope

# =====================================================
# CONFIRMAÇÃO SEMANAL
# =====================================================

def slope_semanal(ticker):

    dfw = yf.download(ticker, period="18mo", interval="1wk", progress=False)

    if len(dfw) < 60:
        return False

    slope = linreg_slope(dfw["Close"], 40)

    return slope > 0

# =====================================================
# SIMULAÇÃO GAIN x LOSS
# =====================================================

def simular_probabilidade(df, sinais, gain, loss):

    ganhos = 0
    perdas = 0

    for i in sinais:

        entrada = df["Close"].iloc[i]
        alvo = entrada * (1 + gain)
        stop = entrada * (1 - loss)

        for j in range(i + 1, len(df)):

            maximo = df["High"].iloc[j]
            minimo = df["Low"].iloc[j]

            bate_gain = maximo >= alvo
            bate_loss = minimo <= stop

            if bate_gain and not bate_loss:
                ganhos += 1
                break

            if bate_loss and not bate_gain:
                perdas += 1
                break

            if bate_gain and bate_loss:
                perdas += 1
                break

    total = ganhos + perdas

    if total == 0:
        return np.nan, 0

    return ganhos / total, total

# =====================================================
# PROCESSAMENTO
# =====================================================

resultados = []

with st.spinner("Processando ativos..."):

    for ticker in ativos:

        try:

            df = yf.download(ticker, period="5y", interval="1d", progress=False)

            if len(df) < 300:
                continue

            mid, upper, lower = keltner(df)
            df["kc_mid"] = mid
            df["kc_upper"] = upper

            df["atr"] = atr(df, 20)
            df["atr_pct"] = df["atr"] / df["Close"]

            slopes = []
            for i in range(len(df)):
                if i < 40:
                    slopes.append(np.nan)
                else:
                    slopes.append(linreg_slope(df["Close"].iloc[i-40:i], 40))

            df["slope"] = slopes

            # Setup:
            # slope > 0
            # fechamento rompe banda superior
            # ATR% mínimo

            sinais = df[
                (df["slope"] > 0) &
                (df["Close"] > df["kc_upper"]) &
                (df["atr_pct"] > 0.012)
            ].index

            if len(sinais) < 10:
                continue

            if not slope_semanal(ticker):
                continue

            if ticker in acoes_100:
                gain = 0.08
                loss = 0.05
                classe = "Ação"
            else:
                gain = 0.06
                loss = 0.04
                classe = "BDR / ETF / FII"

            idx = [df.index.get_loc(i) for i in sinais]

            prob, amostras = simular_probabilidade(df, idx, gain, loss)

            if pd.isna(prob):
                continue

            resultados.append({
                "Ativo": ticker.replace(".SA",""),
                "Classe": classe,
                "Prob_Gain_antes_Loss": prob * 100,
                "Amostras": amostras,
                "Gain_%": gain * 100,
                "Loss_%": loss * 100
            })

        except:
            pass

# =====================================================
# RESULTADO
# =====================================================

st.subheader("Ranking – maior probabilidade histórica de gain antes do loss")

if len(resultados) == 0:

    st.warning("Nenhum ativo gerou amostras suficientes para o setup.")

else:

    df_res = pd.DataFrame(resultados)

    df_res = df_res.sort_values(
        by=["Prob_Gain_antes_Loss","Amostras"],
        ascending=[False, False]
    )

    df_res["Prob_Gain_antes_Loss"] = df_res["Prob_Gain_antes_Loss"].round(2)

    st.dataframe(df_res, use_container_width=True)

    st.caption("Probabilidade calculada por simulação histórica de primeiro toque (gain x loss).")
