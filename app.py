import streamlit as st
import pandas as pd
import re
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")

st.title("Ranking de Leilões de Mercadorias – Brasil")

st.caption("Categoria analisada: mercadorias diversas (ferramentas, eletrodomésticos, eletrônicos, bens móveis em geral)")

consultas = [
    "leilão de mercadorias ferramentas eletrodomésticos site leilão Brasil",
    "leilão de bens diversos eletrônicos ferramentas site leilão",
    "leilão de produtos apreendidos mercadorias site oficial leilão",
    "leilão de equipamentos ferramentas industriais site leilão",
    "leilão de bens móveis mercadorias site leilão Brasil"
]


def extrair_preco(texto):
    if not texto:
        return None

    texto = texto.replace(".", "").replace(",", ".")
    valores = re.findall(r'R\$ ?\d+\.?\d*', texto)

    if not valores:
        return None

    try:
        return float(valores[0].replace("R$", "").strip())
    except:
        return None


def buscar_leiloes_mercadorias(minimo=30):

    resultados = []

    with DDGS() as ddgs:
        for consulta in consultas:
            try:
                achados = ddgs.text(
                    consulta,
                    region="br-pt",
                    safesearch="moderate",
                    max_results=50
                )

                for r in achados:
                    resultados.append({
                        "titulo": r.get("title"),
                        "link": r.get("href"),
                        "descricao": r.get("body")
                    })

            except Exception:
                pass

    if not resultados:
        return pd.DataFrame()

    df = pd.DataFrame(resultados)

    df = df.drop_duplicates(subset=["link"])

    # tenta garantir pelo menos 30 analisados
    return df.head(minimo * 2)


def classificar(df):

    df["preco_encontrado"] = df["descricao"].apply(extrair_preco)

    df["score"] = 0.0

    # qualidade de título
    df["score"] += df["titulo"].fillna("").str.len().apply(lambda x: min(x, 80)) * 0.04

    # qualidade de descrição
    df["score"] += df["descricao"].fillna("").str.len().apply(lambda x: min(x, 400)) * 0.01

    # bônus para portais típicos de leilão
    df["score"] += df["link"].str.contains(
        "leil|judicial|oficial|banco|caixa|alien|recupera|patrimonio|apreendid",
        case=False,
        na=False
    ).astype(int) * 3.0

    # penalidade para marketplaces comuns
    df["score"] -= df["link"].str.contains(
        "mercadolivre|olx|amazon|shopee|magazineluiza|casasbahia|americanas",
        case=False,
        na=False
    ).astype(int) * 6.0

    # pequeno bônus se existir valor no texto
    df["score"] += df["preco_encontrado"].notna().astype(int) * 1.0

    return df.sort_values("score", ascending=False)


st.info("Buscando leilões de mercadorias no Brasil. Aguarde...")

base = buscar_leiloes_mercadorias(minimo=30)

if base.empty:

    st.error("Não foi possível coletar resultados no momento.")

else:

    base_classificada = classificar(base)

    analisados = base_classificada.head(30)

    top10 = analisados.head(10)

    st.subheader("Resultado final – TOP 10 leilões de mercadorias")

    st.caption(f"Total de leilões analisados: {len(analisados)}")

    tabela = top10[["titulo", "link", "score"]].copy()
    tabela["score"] = tabela["score"].round(2)

    st.dataframe(tabela, use_container_width=True)

    st.subheader("Links diretos dos 10 melhores")

    for i, row in top10.iterrows():
        st.markdown(f"- [{row['titulo']}]({row['link']})")
