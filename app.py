import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("Ranking de Leilões – Brasil")
st.caption("Classificação econômica por modalidade (Top 10 de cada categoria)")

# =====================================================
# PESOS DO MODELO
# =====================================================

PESO_SEGURANCA = 0.40
PESO_CUSTO_BENEFICIO = 0.30
PESO_RECLAMACOES = 0.20
PESO_FEEDBACK = 0.10

# =====================================================
# CARREGAMENTO DA BASE
# =====================================================

@st.cache_data
def carregar_base():
    return pd.read_csv("dados_leiloes.csv")

# =====================================================
# FUNÇÕES ECONÔMICAS
# =====================================================

def calcular_desconto(preco_leilao, preco_mercado):
    if preco_mercado <= 0:
        return 0
    return (preco_mercado - preco_leilao) / preco_mercado * 100


def normalizar_desconto(desconto, ref=60):
    return max(0, min(10, (desconto / ref) * 10))


def normalizar_reclamacoes(qtd, max_ref=50):
    score = 10 * (1 - min(qtd, max_ref) / max_ref)
    return max(0, score)


def calcular_score_final(linha):

    score_cb = normalizar_desconto(linha["desconto_percentual"])
    score_rec = normalizar_reclamacoes(linha["reclamacoes_pos_compra"])

    return (
        linha["score_seguranca"] * PESO_SEGURANCA +
        score_cb * PESO_CUSTO_BENEFICIO +
        score_rec * PESO_RECLAMACOES +
        linha["score_feedback"] * PESO_FEEDBACK
    )

# =====================================================
# APP
# =====================================================

try:
    df = carregar_base()
except Exception as e:
    st.error("Erro ao carregar dados_leiloes.csv")
    st.stop()

colunas_necessarias = [
    "plataforma",
    "link",
    "categoria",
    "preco_leilao",
    "preco_mercado",
    "score_seguranca",
    "reclamacoes_pos_compra",
    "score_feedback"
]

for c in colunas_necessarias:
    if c not in df.columns:
        st.error(f"Coluna obrigatória ausente: {c}")
        st.stop()

# =====================================================
# PADRONIZAÇÃO DE CATEGORIAS
# =====================================================

df["categoria"] = df["categoria"].str.strip()

# =====================================================
# CÁLCULOS
# =====================================================

df["desconto_percentual"] = df.apply(
    lambda x: calcular_desconto(x["preco_leilao"], x["preco_mercado"]),
    axis=1
)

df["score_custo_beneficio"] = df["desconto_percentual"].apply(normalizar_desconto)
df["score_reclamacoes"] = df["reclamacoes_pos_compra"].apply(normalizar_reclamacoes)

df["score_final"] = df.apply(calcular_score_final, axis=1)

# =====================================================
# FILTRO DE CATEGORIA
# =====================================================

st.sidebar.header("Filtros")

categorias = sorted(df["categoria"].unique().tolist())

categorias_sel = st.sidebar.multiselect(
    "Modalidades",
    categorias,
    default=categorias
)

df = df[df["categoria"].isin(categorias_sel)].copy()

# =====================================================
# RANKING E TOP 10
# =====================================================

df = df.sort_values(
    ["categoria", "score_final"],
    ascending=[True, False]
)

df["ranking"] = (
    df.groupby("categoria")["score_final"]
      .rank(method="dense", ascending=False)
      .astype(int)
)

df_top10 = (
    df.sort_values(["categoria", "ranking"])
      .groupby("categoria", group_keys=False)
      .head(10)
)

# =====================================================
# EXIBIÇÃO
# =====================================================

st.subheader("Top 10 melhores leilões por modalidade")

st.caption(
    f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
    f"Total de registros analisados: {len(df)}"
)

tabela = df_top10[
    [
        "categoria",
        "ranking",
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
    ]
]

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

# =====================================================
# RESUMO POR CATEGORIA
# =====================================================

st.subheader("Quantidade de leilões analisados por modalidade")

resumo = (
    df.groupby("categoria")
      .size()
      .reset_index(name="qtde_leiloes")
)

st.dataframe(resumo, use_container_width=True)

st.info(
    "O ranking é sempre relativo dentro da própria modalidade "
    "(veículos, imóveis, mercadorias etc.)."
)

st.markdown("### Pesos do modelo")

st.write({
    "Segurança": PESO_SEGURANCA,
    "Custo-benefício": PESO_CUSTO_BENEFICIO,
    "Reclamações pós-compra": PESO_RECLAMACOES,
    "Feedback dos usuários": PESO_FEEDBACK
})
