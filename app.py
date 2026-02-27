import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Ranking de Leilões Online - Brasil", layout="wide")

st.title("Ranking de Leilões Online – Classificação por Categoria")

# ============================================================
# CAMINHO GARANTIDO NA MESMA PASTA DO app.py
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "dados_leiloes.csv"

# ============================================================
# CRIA CSV DE EXEMPLO SE NÃO EXISTIR
# ============================================================

def criar_csv_exemplo(caminho):
    dados = [
        # ---------------- IMÓVEIS ----------------
        ["Zukerman", "https://exemplo.com/imovel1", "Imóveis", 180000, 230000, 8.5, 12, 8.0],
        ["Mega Leilões", "https://exemplo.com/imovel2", "Imóveis", 210000, 260000, 9.0, 9, 8.6],
        ["Leilão Santander", "https://exemplo.com/imovel3", "Imóveis", 195000, 250000, 8.8, 7, 8.4],

        # ---------------- VEÍCULOS ----------------
        ["Sodré Santoro", "https://exemplo.com/carro1", "Veículos", 42000, 52000, 8.9, 18, 8.1],
        ["Copart", "https://exemplo.com/carro2", "Veículos", 38000, 50000, 8.3, 22, 7.8],
        ["Superbid", "https://exemplo.com/moto1", "Veículos", 12000, 17000, 8.6, 10, 8.2],

        # ---------------- MERCADORIAS ----------------
        ["Receita Federal", "https://exemplo.com/mercadoria1", "Mercadorias", 4500, 8500, 9.2, 5, 8.7],
        ["Sold Leilões", "https://exemplo.com/mercadoria2", "Mercadorias", 2800, 6000, 8.4, 11, 7.9],
        ["Leilão Judicial Brasil", "https://exemplo.com/mercadoria3", "Mercadorias", 1500, 4000, 8.0, 14, 7.5],
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
    df.to_csv(caminho, index=False, encoding="utf-8-sig")


if not CSV_PATH.exists():
    criar_csv_exemplo(CSV_PATH)
    st.warning(
        "Arquivo dados_leiloes.csv não existia. "
        "Um arquivo de exemplo foi criado automaticamente na pasta do projeto.\n\n"
        "Depois substitua o conteúdo pelos seus leilões reais."
    )

# ============================================================
# CARREGAMENTO
# ============================================================

try:
    df = pd.read_csv(CSV_PATH)
except Exception as e:
    st.error(f"Erro ao carregar dados_leiloes.csv: {e}")
    st.stop()

# ============================================================
# VALIDAÇÃO DE COLUNAS
# ============================================================

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

faltando = [c for c in colunas_necessarias if c not in df.columns]

if faltando:
    st.error(f"Colunas obrigatórias ausentes no CSV: {faltando}")
    st.stop()

# ============================================================
# LIMPEZA E NORMALIZAÇÃO
# ============================================================

df["categoria"] = df["categoria"].astype(str).str.strip()

df["preco_leilao"] = pd.to_numeric(df["preco_leilao"], errors="coerce")
df["preco_mercado"] = pd.to_numeric(df["preco_mercado"], errors="coerce")
df["score_seguranca"] = pd.to_numeric(df["score_seguranca"], errors="coerce")
df["reclamacoes_pos_compra"] = pd.to_numeric(df["reclamacoes_pos_compra"], errors="coerce")
df["score_feedback"] = pd.to_numeric(df["score_feedback"], errors="coerce")

df = df.dropna()

# ============================================================
# MÉTRICAS DO MODELO
# ============================================================

# custo-benefício
df["beneficio"] = (df["preco_mercado"] - df["preco_leilao"]) / df["preco_mercado"]

# inversão de reclamações
df["reclamacoes_invertido"] = 1 / (1 + df["reclamacoes_pos_compra"])

# normalização simples
def normalizar(col):
    return (col - col.min()) / (col.max() - col.min()) if col.max() != col.min() else 0.5

df["n_beneficio"] = normalizar(df["beneficio"])
df["n_seguranca"] = normalizar(df["score_seguranca"])
df["n_feedback"] = normalizar(df["score_feedback"])
df["n_reclamacoes"] = normalizar(df["reclamacoes_invertido"])

# ============================================================
# SCORE FINAL
# ============================================================

df["score_final"] = (
      0.35 * df["n_seguranca"]
    + 0.30 * df["n_beneficio"]
    + 0.20 * df["n_reclamacoes"]
    + 0.15 * df["n_feedback"]
)

# ============================================================
# CONTADOR DE LEILÕES POR CATEGORIA
# ============================================================

st.subheader("Quantidade de leilões analisados por categoria")

contagem = df["categoria"].value_counts().reset_index()
contagem.columns = ["Categoria", "Quantidade"]

st.dataframe(contagem, use_container_width=True)

# ============================================================
# FILTRO DE CATEGORIAS VÁLIDAS
# ============================================================

categorias_validas = ["Imóveis", "Veículos", "Mercadorias"]

df = df[df["categoria"].isin(categorias_validas)]

# ============================================================
# RANKING TOP 10 POR CATEGORIA
# ============================================================

st.subheader("Ranking TOP 10 por categoria")

for categoria in categorias_validas:

    st.markdown(f"## {categoria}")

    base = df[df["categoria"] == categoria].copy()

    if base.empty:
        st.info("Nenhum leilão encontrado para esta categoria.")
        continue

    ranking = (
        base
        .sort_values("score_final", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    ranking.insert(0, "Ranking", ranking.index + 1)

    st.dataframe(
        ranking[
            [
                "Ranking",
                "plataforma",
                "link",
                "preco_leilao",
                "preco_mercado",
                "score_seguranca",
                "reclamacoes_pos_compra",
                "score_feedback",
                "beneficio",
                "score_final"
            ]
        ],
        use_container_width=True
    )

# ============================================================
# ALERTA DE AMOSTRA
# ============================================================

st.info(
    "Para obter rankings confiáveis, recomenda-se no mínimo 30 leilões por categoria.\n"
    "O número efetivamente analisado aparece na tabela de contagem acima."
)
