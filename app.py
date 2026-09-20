import xml.etree.ElementTree as ET
import re
import urllib.request
import pandas as pd
import streamlit as st
import spacy

# Ładowanie polskiego modelu językowego pobranego przez requirements.txt
@st.cache_resource
def load_nlp():
    return spacy.load("pl_core_news_sm")

nlp = load_nlp()

st.set_page_config(
    page_title="SEO Internal Link Finder",
    page_icon="🔍",
    layout="wide"
)

st.title("🔗 Generator Linkowania Wewnętrznego")
st.caption("Dopasowuje adresy URL z sitemapy na podstawie słów kluczowych i odmiany języka polskiego.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Dane wejściowe")
    sitemap_input = st.text_input("Adres Sitemapy XML:", placeholder="https://twojadomena.pl/sitemap.xml")
    text_input = st.text_area("Tekst do analizy:", height=300, placeholder="Wklej tutaj treść artykułu...")
    analyze_btn = st.button("🚀 Uruchom analizę SEO", type="primary")


def fetch_and_parse_xml(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        xml_data = response.read()
    return ET.fromstring(xml_data)


def get_urls_from_sitemap(url, visited=None):
    if visited is None:
        visited = set()

    if url in visited:
        return []
    visited.add(url)

    urls = []
    try:
        root = fetch_and_parse_xml(url)
    except Exception:
        return urls

    sub_sitemaps = []
    page_urls = []

    for elem in root.iter():
        if elem.tag.endswith('loc') and elem.text:
            loc = elem.text.strip()
            if loc.endswith('.xml') or 'sitemap' in loc.lower():
                sub_sitemaps.append(loc)
            else:
                page_urls.append(loc)

    urls.extend(page_urls)

    for sub_url in sub_sitemaps:
        if sub_url not in visited:
            urls.extend(get_urls_from_sitemap(sub_url, visited))

    return list(dict.fromkeys(urls))


def get_lemmas(text_or_phrase):
    doc = nlp(text_or_phrase.lower())
    return [token.lemma_ for token in doc if not token.is_punct and not token.is_stop and len(token.lemma_) > 2]


def suggest_internal_links(text, urls):
    suggestions = []

    text_doc = nlp(text)
    text_lemmas = {token.lemma_.lower(): token.text for token in text_doc if not token.is_punct}

    ignored_words = {"kontakt", "o-nas", "home", "polityka-prywatnosci", "kategoria", "tag"}

    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        
        if not slug or slug in ignored_words:
            continue

        slug_words = slug.replace("-", " ").split()
        
        for word in slug_words:
            word_lemmas = get_lemmas(word)
            if not word_lemmas:
                continue
            
            lemma = word_lemmas[0]

            if lemma in text_lemmas:
                matched_word_in_text = text_lemmas[lemma]
                
                suggestions.append({
                    "Słowo w tekście": matched_word_in_text,
                    "Forma podstawowa": lemma,
                    "Dopasowane słowo z URL": word,
                    "Docelowy URL": url
                })

    df_result = pd.DataFrame(suggestions)
    if not df_result.empty:
        df_result = df_result.drop_duplicates(subset=["Słowo w tekście", "Docelowy URL"])
    
    return df_result


with col2:
    st.subheader("2. Wyniki analizy")
    if analyze_btn:
        if not sitemap_input or not text_input:
            st.error("⚠️ Proszę podać adres sitemapy oraz wkleić tekst.")
        else:
            with st.spinner("Przeszukiwanie sitemapy i analiza powiązań słownych..."):
                try:
                    urls = get_urls_from_sitemap(sitemap_input)
                    results_df = suggest_internal_links(text_input, urls)

                    st.success(f"Pobrano łącznie {len(urls)} adresów z sitemapy.")

                    if not results_df.empty:
                        st.dataframe(results_df, use_container_width=True)

                        csv_data = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Pobierz raport CSV",
                            data=csv_data,
                            file_name="linkowanie_wewnetrzne.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("Nie znaleziono pasujących fraz.")
                except Exception as e:
                    st.error(f"❌ Błąd: {e}")
