import streamlit as st
import pandas as pd
import re
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")

st.title("Scanner de Leilões no Brasil – Ranking por Categoria")

categorias = {
    "Imóveis": [
        "leilão de imóveis extrajudicial site leilão Brasil",
        "leilão de imóveis caixa site leilão",
        "leilão judicial de imóveis site oficial"
    ],
    "Veículos": [
        "leilão de carros site oficial leilão Brasil",
        "leilão de veículos recuperados site leilão",
        "leilão de motos site leilão Brasil"
    ],
    "Mercadorias": [
        "leilão de mercadorias ferramentas eletrodomésticos site leilão",
        "leilão de bens diversos eletrônicos site leilão Brasil",
        "leilão de produtos apreendidos mercadorias site leilão"
    ]
}


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


def buscar_links(categoria, consultas, minimo=30):
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
                        "categoria": categoria,
                        "titulo": r.get("title"),
                        "link": r.get("href"),
                        "descricao": r.get("body")
                    })

            except Exception as e:
                st.warning(f"Falha na busca: {consulta}")

    df = pd.DataFrame(resultados)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["link"])

    return df.head(minimo * 2)


def classificar_leiloes(df):
    if df.empty:
        return df

    df["preco_encontrado"] = df["descricao"].apply(extrair_preco)

    df["score"] = 0

    # Critérios simples e objetivos (proxy de qualidade)
    df["score"] += df["titulo"].str.len().fillna(0).apply(lambda x: min(x, 60)) * 0.05
    df["score"] += df["descricao"].str.len().fillna(0).apply(lambda x: min(x, 300)) * 0.01

    # bônus se aparenta ser site institucional de leilão
    df["score"] += df["link"].str.contains(
        "leil|judicial|caixa|oficial|banco|recupera|alien",
        case=False,
        na=False
    ).astype(int) * 3

    # leve penalidade se parecer marketplace comum
    df["score"] -= df["link"].str.contains(
        "mercado|olx|amazon|shopee",
        case=False,
        na=False
    ).astype(int) * 5

    return df.sort_values("score", ascending=False)


st.info("Buscando leilões públicos na internet. Aguarde alguns segundos...")

resultado_final = {}

for categoria, consultas in categorias.items():

    st.subheader(f"Categoria: {categoria}")

    base = buscar_links(categoria, consultas, minimo=30)

    if base.empty:
        st.error(f"Nenhum resultado encontrado para {categoria}.")
        continue

    base_classificada = classificar_leiloes(base)

    # Garante análise mínima de 30 registros (quando houver)
    analisados = base_classificada.head(30)

    top10 = analisados.head(10)

    resultado_final[categoria] = top10

    st.caption(f"Total analisado: {len(analisados)} leilões")

    tabela = top10[["titulo", "link", "score"]].copy()
    tabela["score"] = tabela["score"].round(2)

    st.dataframe(
        tabela,
        use_container_width=True
    )


if not resultado_final:
    st.warning(
        "Não foi possível coletar resultados no momento. "
        "Isso normalmente ocorre por bloqueio temporário do buscador."
    )
