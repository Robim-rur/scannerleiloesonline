import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("Scanner – Golden Cross semanal (evento) | Probabilidade de +20% antes de -10%")

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
# PARÂMETROS DO ESTUDO
# =====================================================

GAIN = 0.20
LOSS = 0.10

# =====================================================
# FUNÇÕES
# =====================================================

def ema(series, p):
    return series.ewm(span=p, adjust=False).mean()

def proximo_pregao(df_daily, data_evento):
    futuros = df_daily[df_daily.index > data_evento]
    if len(futuros) == 0:
        return None
    return futuros.index[0]

def simular_trade(df_daily, data_entrada, preco_entrada):

    alvo = preco_entrada * (1 + GAIN)
    stop = preco_entrada * (1 - LOSS)

    sub = df_daily[df_daily.index >= data_entrada]

    for i, row in sub.iterrows():

        if row["Low"] <= stop:
            dias = (i - data_entrada).days
            return "loss", dias

        if row["High"] >= alvo:
            dias = (i - data_entrada).days
            return "gain", dias

    return None, None


# =====================================================
# PROCESSAMENTO
# =====================================================

resultado = []
progress = st.progress(0)

for idx, ticker in enumerate(ativos):

    try:
        dfw = yf.download(ticker, period="15y", interval="1wk", progress=False)
        dfd = yf.download(ticker, period="15y", interval="1d", progress=False)

        if dfw.empty or dfd.empty:
            continue

        # remove candle semanal em formação
        dfw = dfw.iloc[:-1]

        dfw["EMA50"] = ema(dfw["Close"], 50)
        dfw["EMA200"] = ema(dfw["Close"], 200)

        eventos = []

        for i in range(1, len(dfw)):
            ant = dfw.iloc[i - 1]
            atual = dfw.iloc[i]

            if ant["EMA50"] <= ant["EMA200"] and atual["EMA50"] > atual["EMA200"]:
                eventos.append(dfw.index[i])

        if len(eventos) < 3:
            continue

        ganhos = 0
        perdas = 0
        tempos = []

        for data_evt in eventos:

            prox = proximo_pregao(dfd, data_evt)
            if prox is None:
                continue

            preco_entrada = float(dfd.loc[prox]["Open"])

            resultado_trade, dias = simular_trade(
                dfd, prox, preco_entrada
            )

            if resultado_trade == "gain":
                ganhos += 1
                tempos.append(dias)

            elif resultado_trade == "loss":
                perdas += 1
                tempos.append(dias)

        total = ganhos + perdas

        if total < 3:
            continue

        prob = ganhos / total
        expect = (prob * GAIN) - ((1 - prob) * LOSS)

        # -------------------------------------------------
        # evento precisa ter ocorrido na ÚLTIMA semana fechada
        # -------------------------------------------------

        pen = dfw.iloc[-2]
        ult = dfw.iloc[-1]

        evento_atual = pen["EMA50"] <= pen["EMA200"] and ult["EMA50"] > ult["EMA200"]

        if not evento_atual:
            continue

        data_evento_atual = dfw.index[-1]

        prox = proximo_pregao(dfd, data_evento_atual)
        if prox is None:
            continue

        entrada_atual = float(dfd.loc[prox]["Open"])

        resultado.append({
            "Ativo": ticker.replace(".SA",""),
            "Entrada": round(entrada_atual, 2),
            "Data do evento": data_evento_atual.date(),
            "Probabilidade gain antes do loss (%)": round(prob * 100, 2),
            "Amostras": total,
            "Expectância": round(expect * 100, 2),
            "Tempo médio até desfecho (dias)": round(np.mean(tempos), 1)
        })

    except:
        pass

    progress.progress((idx + 1) / len(ativos))


# =====================================================
# SAÍDA
# =====================================================

st.subheader("Golden Cross semanal (evento) – Ranking")

if len(resultado) == 0:
    st.warning("Nenhum ativo com Golden Cross semanal como evento no último fechamento.")
else:
    df_res = pd.DataFrame(resultado)
    df_res = df_res.sort_values(
        by="Probabilidade gain antes do loss (%)",
        ascending=False
    )
    st.dataframe(df_res, use_container_width=True)
