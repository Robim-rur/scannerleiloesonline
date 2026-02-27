import streamlit as st
import pandas as pd
import re

try:
    from duckduckgo_search import ddg
except Exception:
    st.error("Falha ao importar duckduckgo-search. Verifique o requirements.txt.")
    st.stop()

st.set_page_config(layout="wide")
st.title("Ranking automático de leilões no Brasil – TOP 10 por categoria")

# =========================================================
# CONFIGURAÇÃO
# =========================================================

RESULTADOS_POR_BUSCA = 50

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

# =========================================================
# FUNÇÕES
# =========================================================

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
        "leilaojudicial.com.br"
    ]

    for d in dominios_confiaveis:
        if d in dominio:
            return 1.0

    return 0.6


def buscar_leiloes_categoria(categoria, consultas):

    registros = []

    for consulta in consultas:
        try:
            resultados = ddg(
                consulta,
                region="br-pt",
                max_results=RESULTADOS_POR_BUSCA
            )

            if resultados is None:
                continue

            for r in resultados:
                registros.append({
                    "categoria": categoria,
                    "titulo": r.get("title", ""),
                    "link": r.get("href", "")
                })

        except Exception as e:
            st.warning(f"Falha na busca: {consulta}")

    df = pd.DataFrame(registros)

    if df.empty:
        return df

    df = df.dropna(subset=["link"])
    df = df.drop_duplicates(subset=["link"])

    return df


def gerar_scores(df):

    df["dominio"] = df["link"].apply(extrair_dominio)

    df["score_seguranca"] = df["dominio"].apply(score_seguranca_por_dominio)

    # proxies (não existem dados públicos reais de pós-venda e preço por lote)
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

st.info("Buscando leilões públicos na internet e analisando dezenas de resultados por categoria...")

bases = []

for categoria, consultas in categorias_consultas.items():

    base = buscar_leiloes_categoria(categoria, consultas)

    if base.empty:
        st.warning(f"Nenhum resultado encontrado para {categoria}.")
        continue

    base = gerar_scores(base)

    bases.append(base)

if not bases:
    st.error("Não foi possível obter resultados.")
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
# TOP 10 POR CATEGORIA (APENAS OS 10 MELHORES)
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

st.success("Ranking TOP-10 concluído.")
