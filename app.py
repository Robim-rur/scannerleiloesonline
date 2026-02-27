import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(layout="wide")

st.title("Ranking de Leilões – Brasil")
st.caption("Top 10 por modalidade | Classificação por risco x retorno")

# =====================================================
# PESOS DO MODELO
# =====================================================

PESO_SEGURANCA = 0.40
PESO_CUSTO_BENEFICIO = 0.30
PESO_RECLAMACOES = 0.20
PESO_FEEDBACK = 0.10

# =====================================================
# CARREGAMENTO
# =====================================================

ARQUIVO = "dados_leiloes.csv"

@st.cache_data
def carregar_base():
    return pd.read_csv(ARQUIVO)

if not os.path.exists(ARQUIVO):
    st.error(
        "Arquivo dados_leiloes.csv não encontrado na pasta do projeto.\n\n"
        "Ele deve estar na mesma pasta do app.py."
    )
    st.stop()

try:
    df = carregar_base()
except Exception as e:
    st.error("Erro ao abrir dados_leiloes.csv")
    st.write(e)
    st.stop()

# =====================================================
# VALIDAÇÃO DAS COLUNAS
# =====================================================

colunas_obrigatorias = [
    "plataforma",
    "link",
    "categoria",
    "preco_leilao",
    "preco_mercado",
    "score_seguranca",
    "reclamacoes_pos_compra",
    "score_feedback"
]

faltantes = [c for c in colunas_obrigatorias if c not in df.columns]

if len(faltantes) > 0:
    st.error("Colunas obrigatórias ausentes:")
    st.write(faltantes)
    st.stop()

# =====================================================
# LIMPEZA BÁSICA
# =====================================================

df = df.copy()

df["categoria"] = df["categoria"].astype(str).str.strip()

# Padronização simples (evita erro de escrita)
mapa_categorias = {
    "Veiculos": "Veículos",
    "veiculos": "Veículos",
    "veículo": "Veículos",
    "veiculo": "Veículos",
    "imovel": "Imóveis",
    "imoveis": "Imóveis",
    "mercadoria": "Mercadorias",
    "mercadorias": "Mercadorias"
}

df["categoria"] = df["categoria"].replace(mapa_categorias)

# =====================================================
# FUNÇÕES ECONÔMICAS
# =====================================================

def calcular_desconto(preco_leilao, preco_mercado):
    try:
        preco_leilao = float(preco_leilao)
        preco_mercado = float(preco_mercado)
    except:
        return 0.0

    if preco_mercado <= 0:
        return 0.0

    return (preco_mercado - preco_leilao) / preco_mercado * 100.0


def normalizar_desconto(desconto, referencia=60.0):
    if desconto <= 0:
        return 0.0
    score = (desconto / referencia) * 10.0
    return max(0.0, min(score, 10.0))


def normalizar_reclamacoes(qtd, max_ref=50):
    try:
        qtd = float(qtd)
    except:
        qtd = max_ref

    score = 10.0 * (1.0 - min(qtd, max_ref) / max_ref)
    return max(0.0, score)


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
# FILTROS
# =====================================================

st.sidebar.header("Filtros")

categorias = sorted(df["categoria"].dropna().unique().tolist())

categorias_sel = st.sidebar.multiselect(
    "Modalidades",
    categorias,
    default=categorias
)

df = df[df["categoria"].isin(categorias_sel)].copy()

# =====================================================
# RANKING
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

# =====================================================
# TOP 10 POR MODALIDADE
# =====================================================

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
    f"Atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  "
    f"Total de leilões analisados: {len(df)}"
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
# RESUMO DE AMOSTRA
# =====================================================

st.subheader("Quantidade de leilões analisados por modalidade")

resumo = (
    df.groupby("categoria")
      .size()
      .reset_index(name="qtde_leiloes")
)

st.dataframe(resumo, use_container_width=True)

# =====================================================
# INFORMAÇÕES DO MODELO
# =====================================================

st.markdown("### Pesos do modelo de classificação")

st.write({
    "Segurança da plataforma": PESO_SEGURANCA,
    "Custo-benefício (desconto real)": PESO_CUSTO_BENEFICIO,
    "Reclamações pós-compra": PESO_RECLAMACOES,
    "Feedback dos usuários": PESO_FEEDBACK
})

st.info(
    "Cada linha representa um leilão (lote). "
    "O ranking é sempre relativo dentro da própria modalidade "
    "(Veículos, Imóveis ou Mercadorias)."
)
