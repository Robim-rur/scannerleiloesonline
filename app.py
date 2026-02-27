import streamlit as st
import pandas as pd
import re
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")
st.title("Ranking Automático de Leilões no Brasil (TOP-10)")

# ---------------------------------------------------
# CONFIGURAÇÃO DE BUSCAS
# ---------------------------------------------------

QUANTIDADE_POR_CONSULTA = 100

categorias_consultas = {
    "Imóveis": [
        "leilão de imóveis site:leiloes",
        "leilão judicial imóvel",
        "leilão extrajudicial imóvel em Brasil"
    ],
    "Veículos": [
        "leilão de carros em Brasil",
        "leilão de motos em Brasil",
        "leilão de veículos seguradora Brasil"
    ],
    "Mercadorias": [
        "leilão de mercadorias apreendidas Brasil",
        "leilão da receita federal mercadorias",
        "leilão de ferramentas e eletrodomésticos Brasil"
    ]
}

# ---------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------

# heurística de segurança simples por domínio
def score_seguranca_por_dominio(url):
    dominios_fortes = [
        "gov.br",
        "zukerman.com.br",
        "sodresantoro.com.br",
        "copart.com.br",
        "superbid.net",
        "portalzukerman.com.br",
        "leilaojudicial.com.br"
    ]
    for d in dominios_fortes:
        if d in url:
            return 0.9
    return 0.6

def extrair_dominio(url):
    try:
        dominio = re.findall(r"https?://([^/]+)", url)[0]
        return dominio
    except:
        return ""

def buscar_leiloes(categoria, consultas):
    resultados = []
    with DDGS() as ddgs:
        for q in consultas:
            buscas = ddgs.text(q, max_results=QUANTIDADE_POR_CONSULTA)
            for item in buscas:
                resultados.append({
                    "categoria": categoria,
                    "titulo": item.get("title"),
                    "link": item.get("href")
                })
    df = pd.DataFrame(resultados).drop_duplicates(subset=["link"])
    return df

def gerar_scores(df):
    df["dominio"] = df["link"].apply(extrair_dominio)
    df["score_seguranca"] = df["link"].apply(score_seguranca_por_dominio)

    # heurística de custo-benefício vista como proxy (mesmo peso de segurança)
    df["score_custo_beneficio"] = df["score_seguranca"] * 0.8

    # heurística de reputação do título (proxy simples)
    df["score_titulo"] = df["titulo"].apply(lambda x: len(str(x)))

    # score final combina heurísticas
    df["score_final"] = (
          0.35 * df["score_seguranca"]
        + 0.30 * df["score_custo_beneficio"]
        + 0.20 * df["score_titulo"]
        + 0.15 * df["score_seguranca"]
    )

    return df

# ---------------------------------------------------
# EXECUÇÃO
# ---------------------------------------------------

st.info("Buscando leilões automaticamente na web... isso pode levar alguns segundos.")

todos_os_resultados = []

for cat, consultas in categorias_consultas.items():
    base_cat = buscar_leiloes(cat, consultas)

    if len(base_cat) == 0:
        st.warning(f"{cat}: nenhum leilão encontrado.")
        continue

    base_cat = gerar_scores(base_cat)
    todos_os_resultados.append(base_cat)

if not todos_os_resultados:
    st.error("Nenhum resultado de leilão encontrado.")
    st.stop()

df_geral = pd.concat(todos_os_resultados, ignore_index=True)

# ---------------------------------------------------
# RANKING E EXIBIÇÃO TOP-10
# ---------------------------------------------------

for categoria in categorias_consultas.keys():

    st.subheader(f"🔎 TOP-10 – {categoria}")

    subset = df_geral[df_geral["categoria"] == categoria]

    if subset.empty:
        st.write("Nenhum resultado encontrado nesta categoria.")
        continue

    ranking_ordenado = (
        subset.sort_values("score_final", ascending=False)
              .head(10)
              .reset_index(drop=True)
    )

    ranking_ordenado.insert(0, "Rank", ranking_ordenado.index + 1)

    st.dataframe(
        ranking_ordenado[[
            "Rank",
            "titulo",
            "link",
            "dominio",
            "score_final"
        ]],
        use_container_width=True
    )

st.success("Ranking TOP-10 concluído!")
