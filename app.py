import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote

st.set_page_config(layout="wide")
st.title("Ranking automático de leilões no Brasil – TOP 10 por categoria")

# =========================================================
# CONFIGURAÇÃO
# =========================================================

RESULTADOS_POR_BUSCA = 40
DELAY = 1.2

categorias_consultas = {
    "Imóveis": [
        "leilão de imóveis brasil",
        "leilão judicial imóvel brasil",
        "leilão extrajudicial imóvel brasil"
    ],
    "Veículos": [
        "leilão de carros brasil",
        "leilão de motos brasil",
        "leilão de veículos seguradora brasil"
    ],
    "Mercadorias": [
        "leilão de mercadorias apreendidas brasil",
        "leilão receita federal mercadorias",
        "leilão ferramentas eletrodomésticos brasil"
    ]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================================================
# FUNÇÕES DE COLETA
# =========================================================

def buscar_duckduckgo_html(consulta, max_itens=30):

    url = "https://html.duckduckgo.com/html/?q=" + quote(consulta)

    r = requests.post(url, headers=HEADERS, timeout=15)

    soup = BeautifulSoup(r.text, "html.parser")

    resultados = []

    for a in soup.select(".result__a"):
        titulo = a.get_text(strip=True)
        link = a.get("href")

        if link and titulo:
            resultados.append((titulo, link))

        if len(resultados) >= max_itens:
            break

    return resultados


def extrair_dominio(url):
    try:
        return re.findall(r"https?://([^/]+)", url)[0].lower()
    except:
        return ""


# =========================================================
# HEURÍSTICAS DE SCORE
# =========================================================

def score_seguranca_por_dominio(dominio):

    dominios_confiaveis = [
        "gov.br",
        "zukerman.com.br",
        "portalzukerman.com.br",
        "sodresantoro.com.br",
        "superbid.net",
        "copart.com.br",
        "leilaojudicial.com.br"
    ]

    for d in dominios_confiaveis:
        if d in dominio:
            return 1.0

    return 0.6


def gerar_scores(df):

    df["dominio"] = df["link"].apply(extrair_dominio)
    df["score_seguranca"] = df["dominio"].apply(score_seguranca_por_dominio)

    df["score_pos_compra"] = df["score_seguranca"]
    df["score_custo_beneficio"] = 0.5 + (df["score_seguranca"] * 0.5)

    df["score_titulo"] = df["titulo"].astype(str).apply(
        lambda x: min(len(x) / 80, 1)
    )

    df["score_final"] = (
        0.35 * df["score_seguranca"]
        + 0.30 * df["score_custo_beneficio"]
        + 0.20 * df["score_pos_compra"]
        + 0.15 * df["score_titulo"]
    )

    return df


# =========================================================
# EXECUÇÃO
# =========================================================

st.info("Buscando leilões públicos na internet. Aguarde alguns segundos...")

bases = []

for categoria, consultas in categorias_consultas.items():

    registros = []

    for consulta in consultas:

        try:
            resultados = buscar_duckduckgo_html(
                consulta,
                max_itens=RESULTADOS_POR_BUSCA
            )

            for titulo, link in resultados:
                registros.append({
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": link
                })

            time.sleep(DELAY)

        except Exception as e:
            st.warning(f"Falha na busca: {consulta}")

    df_cat = pd.DataFrame(registros)

    if df_cat.empty:
        st.warning(f"Nenhum resultado encontrado para {categoria}.")
        continue

    df_cat = df_cat.drop_duplicates(subset=["link"])
    df_cat = gerar_scores(df_cat)

    bases.append(df_cat)

if not bases:
    st.error("Não foi possível coletar resultados.")
    st.stop()

df = pd.concat(bases, ignore_index=True)

# =========================================================
# CONTAGEM REAL ANALISADA
# =========================================================

st.subheader("Quantidade de leilões analisados por categoria")

contagem = (
    df.groupby("categoria")["link"]
      .count()
      .reset_index(name="Quantidade analisada")
)

st.dataframe(contagem, use_container_width=True)

# =========================================================
# TOP 10 POR CATEGORIA
# =========================================================

st.subheader("TOP 10 melhores leilões por categoria")

for categoria in categorias_consultas.keys():

    st.markdown(f"### {categoria}")

    base_cat = df[df["categoria"] == categoria].copy()

    if base_cat.empty:
        st.info("Sem dados para esta categoria.")
        continue

    base_cat = base_cat.sort_values("score_final", ascending=False)

    top10 = base_cat.head(10).reset_index(drop=True)
    top10.insert(0, "Ranking", top10.index + 1)

    st.dataframe(
        top10[
            [
                "Ranking",
                "titulo",
                "link",
                "dominio",
                "score_seguranca",
                "score_custo_beneficio",
                "score_pos_compra",
                "score_final"
            ]
        ],
        use_container_width=True
    )

st.success("Ranking TOP-10 gerado com sucesso.")
