import streamlit as st
import pandas as pd
import re

# ---------------------------------------------------------
# Tentativa compatível de import da lib DuckDuckGo
# ---------------------------------------------------------

try:
    from duckduckgo_search import DDGS
except Exception as e:
    st.error(
        "A biblioteca duckduckgo-search não está instalada.\n\n"
        "Confirme que o arquivo requirements.txt contém:\n"
        "duckduckgo-search==5.3.1\n\n"
        "Depois faça novo deploy no Streamlit Cloud."
    )
    st.stop()

st.set_page_config(layout="wide")
st.title("Ranking automático de leilões no Brasil – TOP 10 por categoria")

# ---------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------

MIN_ANALISE = 30
MAX_RESULTADOS_POR_BUSCA = 80

categorias_consultas = {
    "Imóveis": [
        "leilão de imóveis brasil site:leilao",
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
        "leilão receita federal mercadorias brasil",
        "leilão ferramentas eletrodomésticos brasil"
    ]
}

# ---------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------

def extrair_dominio(url):
    try:
        return re.findall(r"https?://([^/]+)", url)[0].lower()
    except:
        return ""


def score_seguranca_por_dominio(dominio):

    dominios_confiaveis = [
        "gov.br",
        "zukerman.com.br",
        "portalzukerman.com.br",
        "sodresantoro.com.br",
        "superbid.net",
        "copart.com.br",
        "leilaojudicial.com.br",
    ]

    for d in dominios_confiaveis:
        if d in dominio:
            return 1.0

    return 0.6


def buscar_leiloes(categoria, consultas):

    registros = []

    with DDGS() as ddgs:
        for consulta in consultas:

            resultados = ddgs.text(
                consulta,
                max_results=MAX_RESULTADOS_POR_BUSCA,
                safesearch="Off",
                region="br-pt"
            )

            for r in resultados:
                registros.append({
                    "categoria": categoria,
                    "titulo": r.get("title", ""),
                    "link": r.get("href", "")
                })

    df = pd.DataFrame(registros)
    df = df.dropna(subset=["link"])
    df = df.drop_duplicates(subset=["link"])

    return df


def gerar_scores(df):

    df["dominio"] = df["link"].apply(extrair_dominio)

    df["score_seguranca"] = df["dominio"].apply(score_seguranca_por_dominio)

    # proxy simples de pós-compra (mesmo domínio confiável)
    df["score_pos_compra"] = df["score_seguranca"]

    # proxy de custo-benefício (heurística pública)
    df["score_custo_beneficio"] = 0.5 + (df["score_seguranca"] * 0.5)

    # qualidade do anúncio (título mais informativo)
    df["score_titulo"] = df["titulo"].astype(str).apply(lambda x: min(len(x) / 80, 1))

    df["score_final"] = (
          0.35 * df["score_seguranca"]
        + 0.30 * df["score_custo_beneficio"]
        + 0.20 * df["score_pos_compra"]
        + 0.15 * df["score_titulo"]
    )

    return df


# ---------------------------------------------------------
# EXECUÇÃO
# ---------------------------------------------------------

st.info("Buscando leilões públicos na internet e analisando aproximadamente 30 por categoria...")

bases = []

for categoria, consultas in categorias_consultas.items():

    base = buscar_leiloes(categoria, consultas)

    if base.empty:
        st.warning(f"Nenhum resultado encontrado para {categoria}.")
        continue

    base = gerar_scores(base)
    bases.append(base)

if not bases:
    st.error("Não foi possível obter resultados de nenhuma categoria.")
    st.stop()

df = pd.concat(bases, ignore_index=True)

# ---------------------------------------------------------
# CONTAGEM REAL ANALISADA
# ---------------------------------------------------------

st.subheader("Quantidade de leilões analisados por categoria")

contagem = (
    df.groupby("categoria")["link"]
      .count()
      .reset_index(name="Quantidade analisada")
)

st.dataframe(contagem, use_container_width=True)

# ---------------------------------------------------------
# TOP 10 POR CATEGORIA (APENAS OS 10 MELHORES)
# ---------------------------------------------------------

st.subheader("TOP 10 melhores leilões por categoria")

for categoria in categorias_consultas.keys():

    st.markdown(f"### {categoria}")

    base_cat = df[df["categoria"] == categoria].copy()

    if base_cat.empty:
        st.info("Sem dados para esta categoria.")
        continue

    base_cat = base_cat.sort_values("score_final", ascending=False)

    # Aqui acontece exatamente o que você pediu:
    # analisa tudo que encontrou (>=30 quando possível)
    # e exibe somente os 10 melhores

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

st.success("Ranking final gerado.")
