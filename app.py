import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Ranking Top-10 de Plataformas de Leilão – Brasil")

# =========================================================
# PESOS DO MODELO
# =========================================================

PESO_SEGURANCA = 0.4
PESO_CUSTO_BENEFICIO = 0.3
PESO_RECLAMACOES = 0.2
PESO_FEEDBACK = 0.1

# =========================================================
# BASE SIMULADA (MVP)
# Cada linha = plataforma + categoria
# =========================================================

def carregar_dados_leiloes():

    dados = [
        {
            "plataforma": "Superbid",
            "link": "https://www.superbid.net/",
            "categoria": "Carros",
            "preco_leilao": 38000,
            "preco_mercado": 52000,
            "score_seguranca": 9.2,
            "reclamacoes_pos_compra": 12,
            "score_feedback": 8.5
        },
        {
            "plataforma": "Receita Federal",
            "link": "https://www.gov.br/receitafederal/pt-br/assuntos/leiloes",
            "categoria": "Eletrônicos",
            "preco_leilao": 2100,
            "preco_mercado": 3900,
            "score_seguranca": 9.8,
            "reclamacoes_pos_compra": 2,
            "score_feedback": 9.3
        },
        {
            "plataforma": "Copart",
            "link": "https://www.copart.com.br/",
            "categoria": "Salvados",
            "preco_leilao": 14500,
            "preco_mercado": 28000,
            "score_seguranca": 8.6,
            "reclamacoes_pos_compra": 22,
            "score_feedback": 7.9
        },
        {
            "plataforma": "Zukerman Leilões",
            "link": "https://www.zukerman.com.br/",
            "categoria": "Imóveis",
            "preco_leilao": 310000,
            "preco_mercado": 470000,
            "score_seguranca": 9.0,
            "reclamacoes_pos_compra": 6,
            "score_feedback": 8.7
        },
        {
            "plataforma": "Sold Leilões",
            "link": "https://www.sold.com.br/",
            "categoria": "Motos",
            "preco_leilao": 7800,
            "preco_mercado": 13500,
            "score_seguranca": 8.3,
            "reclamacoes_pos_compra": 18,
            "score_feedback": 7.8
        }
        # aqui você pode estender com outras plataformas reais
    ]

    return pd.DataFrame(dados)

# =========================================================
# NORMALIZAÇÃO
# =========================================================

def calcular_desconto_percentual(preco_leilao, preco_mercado):
    if preco_mercado <= 0:
        return 0
    return (preco_mercado - preco_leilao) / preco_mercado * 100


def normalizar_reclamacoes(qtd, max_reclamacoes=50):
    return max(10 * (1 - min(qtd, max_reclamacoes) / max_reclamacoes), 0)


def normalizar_desconto(desconto, desconto_maximo_referencia=60):
    return max(10 * min(desconto, desconto_maximo_referencia) / desconto_maximo_referencia, 0)


# =========================================================
# CALCULA SCORE FINAL
# =========================================================

def calcular_score_final(linha):
    score_custo_beneficio = normalizar_desconto(linha["desconto_percentual"])
    score_reclamacoes = normalizar_reclamacoes(linha["reclamacoes_pos_compra"])

    score_final = (
        linha["score_seguranca"] * PESO_SEGURANCA +
        score_custo_beneficio * PESO_CUSTO_BENEFICIO +
        score_reclamacoes * PESO_RECLAMACOES +
        linha["score_feedback"] * PESO_FEEDBACK
    )

    return score_final

# =========================================================
# APP
# =========================================================

df = carregar_dados_leiloes()

df["desconto_percentual"] = df.apply(
    lambda x: calcular_desconto_percentual(x["preco_leilao"], x["preco_mercado"]),
    axis=1
)

df["score_reclamacoes"] = df["reclamacoes_pos_compra"].apply(normalizar_reclamacoes)
df["score_custo_beneficio"] = df["desconto_percentual"].apply(normalizar_desconto)
df["score_final"] = df.apply(calcular_score_final, axis=1)

# =========================================================
# FILTROS
# =========================================================

st.sidebar.header("Filtros")

categorias = sorted(df["categoria"].unique())
categoria_sel = st.sidebar.multiselect(
    "Categoria",
    categorias,
    default=categorias
)

df_filtrado = df[df["categoria"].isin(categoria_sel)].copy()

# =========================================================
# RANKING TOP-10
# =========================================================

df_ranked = (
    df_filtrado
    .sort_values(["categoria", "score_final"], ascending=[True, False])
    .groupby("categoria")
    .head(10)
    .reset_index(drop=True)
)

df_ranked["ranking_na_categoria"] = (
    df_ranked
    .groupby("categoria")["score_final"]
    .rank(ascending=False, method="dense")
    .astype(int)
)

# =========================================================
# EXIBIÇÃO
# =========================================================

st.subheader("Top-10 das plataformas de leilão (por categoria)")

st.caption(f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

tabela = df_ranked[[
    "categoria",
    "ranking_na_categoria",
    "plataforma",
    "link",
    "preco_leilao",
    "preco_mercado",
    "desconto_percentual",
    "score_seguranca",
    "reclamacoes_pos_compra",
    "score_reclamacoes",
    "score_custo_beneficio",
    "score_feedback",
    "score_final"
]]

st.dataframe(
    tabela.style.format({
        "preco_leilao": "R$ {:,.2f}",
        "preco_mercado": "R$ {:,.2f}",
        "desconto_percentual": "{:.2f}",
        "score_reclamacoes": "{:.2f}",
        "score_custo_beneficio": "{:.2f}",
        "score_feedback": "{:.2f}",
        "score_final": "{:.2f}"
    }),
    use_container_width=True
)

st.markdown("### Pesos do modelo")

st.write({
    "Segurança": PESO_SEGURANCA,
    "Custo-benefício": PESO_CUSTO_BENEFICIO,
    "Reclamações": PESO_RECLAMACOES,
    "Feedback": PESO_FEEDBACK
})

st.info(
    "Este ranking mostra até os 10 melhores leilões por categoria "
    "(imóveis, carros, motos, eletrônicos, salvados etc.)."
)
