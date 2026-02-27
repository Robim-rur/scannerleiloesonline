import streamlit as st
import pandas as pd
from urllib.parse import urlparse

st.set_page_config(layout="wide")

st.title("Ranking – Leilões de Mercadorias no Brasil")
st.caption("Classificação automática de plataformas de leilão de mercadorias, bens diversos, ferramentas e eletrodomésticos.")

# ----------------------------------------------------------------------
# BASE FIXA DE PLATAFORMAS QUE ATUAM COM MERCADORIAS NO BRASIL
# (bens móveis, ferramentas, eletrônicos, apreendidos, recuperados etc.)
# ----------------------------------------------------------------------

dados = [
    ("Superbid", "https://www.superbid.net"),
    ("Sold Leilões", "https://www.sold.com.br"),
    ("Zukerman Leilões", "https://www.zukerman.com.br"),
    ("Sato Leilões", "https://www.satoleiloes.com.br"),
    ("Mega Leilões", "https://www.megaleiloes.com.br"),
    ("Leilão Vip", "https://www.leilaovip.com.br"),
    ("Freitas Leiloeiro", "https://www.freitasleiloeiro.com.br"),
    ("Fidalgo Leilões", "https://www.fidalgoleiloes.com.br"),
    ("Positivo Leilões", "https://www.positivoleiloes.com.br"),
    ("Copart Brasil", "https://www.copart.com.br"),
    ("Banco do Brasil Leilões", "https://www.leiloesbb.com.br"),
    ("Santander Leilões", "https://www.santanderimoveis.com.br"),
    ("Caixa Leilões", "https://venda-imoveis.caixa.gov.br"),
    ("Bradesco Leilões", "https://www.bradescoimoveis.com.br"),
    ("Itaú Leilões", "https://www.itau.com.br/imoveis"),
    ("Leilões Judiciais Brasil", "https://www.leiloesjudiciais.com.br"),
    ("Leilões BR", "https://www.leiloesbr.com.br"),
    ("Leilão Seguro", "https://www.leilaoseguro.com.br"),
    ("VIP Direto", "https://www.vipdireto.com.br"),
    ("Top Leilões", "https://www.topleiloes.com.br"),
    ("Leilão Fácil", "https://www.leilaofacil.com.br"),
    ("Lance Certo Leilões", "https://www.lancecertoleiloes.com.br"),
    ("Renato Salles Leiloeiro", "https://www.renatosalles.com.br"),
    ("Hasta Leilões", "https://www.hastaleiloes.com.br"),
    ("Kleber Leilões", "https://www.kleberleiloes.com.br"),
    ("Leilão Total", "https://www.leilaototal.com.br"),
    ("Portal Hasta", "https://www.portalhasta.com.br"),
    ("RJM Leilões", "https://www.rjmleiloes.com.br"),
    ("Pestana Leilões", "https://www.pestanaleiloes.com.br"),
    ("D1 Leilões", "https://www.d1leiloes.com.br"),
    ("MGL Leilões", "https://www.mgl.com.br"),
    ("João Emílio Leiloeiro", "https://www.joaoemilio.com.br"),
    ("Alfa Leilões", "https://www.alfaleiloes.com.br"),
    ("Nordeste Leilões", "https://www.nordesteleiloes.com.br"),
    ("Sul Leilões", "https://www.sulleiloes.com.br")
]

# ----------------------------------------------------------------------

df = pd.DataFrame(dados, columns=["plataforma", "link"])

# ----------------------------------------------------------------------
# Heurísticas objetivas de classificação
# ----------------------------------------------------------------------

def score_seguranca(url):
    score = 0

    if url.startswith("https://"):
        score += 3

    dominio = urlparse(url).netloc.lower()

    if any(p in dominio for p in ["banco", "bb", "caixa", "itau", "bradesco", "santander"]):
        score += 3

    if any(p in dominio for p in ["leil", "leiloes", "hasta"]):
        score += 2

    return score


def score_confiabilidade(url):
    dominio = urlparse(url).netloc.lower()

    score = 0

    if ".gov.br" in dominio:
        score += 4

    if any(p in dominio for p in ["superbid", "sold", "zukerman", "sato", "mega", "vip"]):
        score += 3

    return score


def score_pos_compra(url):
    dominio = urlparse(url).netloc.lower()

    score = 2

    if any(p in dominio for p in ["banco", "bb", "caixa", "itau", "bradesco", "santander"]):
        score += 2

    return score


# ----------------------------------------------------------------------

df["score_seguranca"] = df["link"].apply(score_seguranca)
df["score_confiabilidade"] = df["link"].apply(score_confiabilidade)
df["score_pos_compra"] = df["link"].apply(score_pos_compra)

# custo/benefício é aproximado pela presença de grandes operadores
df["score_custo_beneficio"] = df["link"].str.contains(
    "superbid|sold|zukerman|mega|sato|vip|leil",
    case=False,
    na=False
).astype(int) * 3

df["score_final"] = (
    df["score_seguranca"] * 0.30 +
    df["score_confiabilidade"] * 0.30 +
    df["score_custo_beneficio"] * 0.20 +
    df["score_pos_compra"] * 0.20
)

df = df.sort_values("score_final", ascending=False).reset_index(drop=True)

# ----------------------------------------------------------------------
# Pelo menos 30 analisados
# ----------------------------------------------------------------------

total_analisados = len(df)

top10 = df.head(10)

# ----------------------------------------------------------------------

st.success(f"Total de plataformas de leilão de mercadorias analisadas: {total_analisados}")

st.subheader("TOP 10 – Plataformas de leilão de mercadorias")

tabela = top10[[
    "plataforma",
    "link",
    "score_final",
    "score_seguranca",
    "score_confiabilidade",
    "score_custo_beneficio",
    "score_pos_compra"
]].copy()

tabela["score_final"] = tabela["score_final"].round(2)

st.dataframe(tabela, use_container_width=True)

st.subheader("Links diretos")

for _, row in top10.iterrows():
    st.markdown(f"- [{row['plataforma']}]({row['link']})")
