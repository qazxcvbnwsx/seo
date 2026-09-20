import xml.etree.ElementTree as ET
import re
import urllib.request
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SEO Internal Link Finder",
    page_icon="🔍",
    layout="wide"
)

st.title("🔗 Generator Linkowania Wewnętrznego")
st.caption("Automatycznie dopasowuj adresy URL z sitemapy XML do fraz w Twoim artykule.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Dane wejściowe")
    sitemap_input = st.text_input("Adres Sitemapy XML:", placeholder="https://twojadomena.pl/sitemap.xml")
    text_input = st.text_area("Tekst do analizy:", height=300, placeholder="Wklej tutaj treść artykułu...")
    analyze_btn = st.button("🚀 Uruchom analizę SEO", type="primary")


def fetch_and_parse_xml(url):
    """Pobiera i parsuje pojedynczy plik XML"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        xml_data = response.read()
    return ET.fromstring(xml_data)


def get_urls_from_sitemap(url, visited=None):
    """Rekurencyjnie pobiera wszystkie końcowe adresy URL, w tym z indeksów sitemap"""
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
            # Sprawdzamy czy dany link prowadzi do kolejnej sitemapy (.xml)
            if loc.endswith('.xml') or 'sitemap' in loc.lower():
                sub_sitemaps.append(loc)
            else:
                page_urls.append(loc)

    # Jeśli znaleziono adresy podstron, dodaj je
    urls.extend(page_urls)

    # Jeśli znaleziono linki do pod-sitemap, pobierz z nich rekurencyjnie wszystkie adresy
    for sub_url in sub_sitemaps:
        if sub_url not in visited:
            urls.extend(get_urls_from_sitemap(sub_url, visited))

    # Usunięcie ewentualnych duplikatów z zachowaniem kolejności
    return list(dict.fromkeys(urls))


def suggest_internal_links(text, urls):
    suggestions = []
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        keyword = slug.replace("-", " ")

        if len(keyword) < 4:
            continue

        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        match = re.search(pattern, text)

        if match:
            suggestions.append({
                "Znaleziona fraza": match.group(0),
                "Sugerowany Anchor": keyword,
                "Docelowy URL": url
            })
    return suggestions


with col2:
    st.subheader("2. Wyniki analizy")
    if analyze_btn:
        if not sitemap_input or not text_input:
            st.error("⚠️ Proszę podać adres sitemapy oraz wkleić tekst.")
        else:
            with st.spinner("Przeszukiwanie sitemapy i analizowanie tekstu..."):
                try:
                    urls = get_urls_from_sitemap(sitemap_input)
                    results = suggest_internal_links(text_input, urls)

                    st.success(f"Pobrano łącznie {len(urls)} adresów z sitemapy (w tym z pod-sitemap).")

                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True)

                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Pobierz raport CSV",
                            data=csv_data,
                            file_name="linkowanie_wewnetrzne.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("Nie znaleziono pasujących fraz w podanym tekście.")
                except Exception as e:
                    st.error(f"❌ Błąd: {e}")
