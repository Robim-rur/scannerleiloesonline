import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(layout="wide")

st.title("Ranking de Leilões – Brasil")
st.caption("Top 10 por modalidade – classificação risco x retorno")

ARQUIVO = "dados_leiloes.csv"

# =====================================================
# PESOS DO MODELO
# =====================================================

PESO_SEGURANCA = 0.40
PESO_CUSTO_BENEFICIO = 0.30
PESO_RECLAMACOES = 0.20
PESO_FEEDBACK = 0.10


# =====================================================
# CRIA CSV DE EXEMPLO SE NÃO EXISTIR
# =====================================================

def criar_csv_exemplo():

    dados = [
        ["Plataforma Teste 1", "https://exemplo.com", "Veículos", 38000, 52000, 9.0, 10, 8.5],
        ["Plataforma Teste 2", "https://exemplo.com", "Veículos", 41000, 54000, 8.7, 12, 8.0],
        ["Plataforma Teste 3", "https://exemplo.com", "Imóveis", 280000, 380000, 9.3, 4, 8.8],
        ["Plataforma Teste 4", "https://exemplo.com", "Imóveis", 310000, 420000, 9.1, 6, 8.6],
        ["Plataforma Teste 5", "https://exemplo.com", "Mercadorias", 1200, 2400, 8.5, 8, 7.9],
        ["Plataforma Teste 6", "https://exemplo.com", "Mercadorias", 900, 1800, 8.2, 11, 7.5],
    ]

    colunas = [
        "plataforma",
        "link",
        "categoria",
        "preco_leilao",
        "preco_mercado",
        "score_seguranca",
        "reclamacoes_pos_compra",
        "score_feedback"
    ]

    df = pd.DataFrame(dados, columns=colunas)
    df.to_csv(ARQUIVO, index=False, encoding="utf-8")


# =====================================================
# GARANTE QUE O CSV EXISTA
# =====================================================

if not os.path.exists(ARQUIVO):
    criar_csv_exemplo()
    st.warning(
        "Arquivo dados_leiloes.csv não existia. "
        "Um arquivo de exemplo foi criado automaticamente na pasta do projeto. "
        "Depois substitua o conteúdo pelos seus leilões reais."
    )


# =====================================================
# CARREGAMENTO
# =====================================================

@st.cache_data
def carregar_base():
    return pd.read_csv(ARQUIVO)


try:
    df = carregar_base()
except Exception as e:
    st.error("Falha ao abrir o arquivo dados_leiloes.csv")
    st.write(e)
    st.stop()


# =====================================================
# VALIDAÇÃO DE COLUNAS
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

faltando = [c for c in colunas_obrigatorias if c not in df.columns]

if faltando:
    st.error("Colunas obrigatórias ausentes no CSV:")
    st.write(faltando)
    st.stop()


# =====================================================
# LIMPEZA BÁSICA
# =====================================================

df = df.copy()

df["categoria"] = df["categoria"].astype(str).str.strip()

mapa = {
    "Veiculos": "Veículos",
    "veiculos": "Veículos",
    "veículo": "Veículos",
    "veiculo": "Veículos",
    "imovel": "Imóveis",
    "imoveis": "Imóveis",
    "mercadoria": "Mercadorias",
    "mercadorias": "Mercadorias"
}

df["categoria"] = df["categoria"].replace(mapa)


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
    f"Atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
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
# RESUMO
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

st.markdown("### Pesos do modelo")

st.write({
    "Segurança": PESO_SEGURANCA,
    "Custo-benefício": PESO_CUSTO_BENEFICIO,
    "Reclamações pós-compra": PESO_RECLAMACOES,
    "Feedback": PESO_FEEDBACK
})

st.info(
    "Cada linha do CSV representa um leilão (lote). "
    "O ranking é sempre relativo dentro da própria modalidade."
)
