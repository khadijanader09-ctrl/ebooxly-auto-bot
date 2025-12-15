import requests
from bs4 import BeautifulSoup
import feedparser
import os
import datetime
import sys

# --- CONFIGURATION ---
SOURCES = [
    {"url": "https://ebooxly.com/index.html", "limit": 4, "keyword": ""},
    {"url": "https://ebooxly.com/authors/index.html", "limit": 4, "keyword": "author"}
]
# Google News Arabe (Culture & Livres)
AUTHORITY_RSS = "https://news.google.com/rss/search?q=كتب+ثقافة+أدب&hl=ar&gl=EG&ceid=EG:ar"

OUTPUT_FILE = "public/index.html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
BLACKLIST_TEXT = ["من نحن", "اتصل بنا", "الشروط", "الخصوصية", "الرئيسية", "Contact", "Privacy", "Home", "DMCA"]

def ensure_public_folder():
    """ Crée le dossier public immédiatement """
    if not os.path.exists("public"):
        os.makedirs("public")

def get_external_news(rss_url, limit=3):
    print(f"   -> Récupération News Culturelles (Google News)...")
    try:
        feed = feedparser.parse(rss_url, agent=USER_AGENT)
        external_links = []
        if not feed.entries: return []
        for entry in feed.entries:
            external_links.append({'title': entry.title, 'link': entry.link, 'is_mine': False})
            if len(external_links) >= limit: break
        return external_links
    except Exception as e:
        print(f"      [!] Erreur camouflage : {e}")
        return []

def get_my_links(source):
    print(f"   -> Analyse Ebooxly ({source['url']})...")
    links_found = []
    try:
        response = requests.get(source['url'], headers={"User-Agent": USER_AGENT}, timeout=20)
        response.encoding = 'utf-8' # Force l'arabe
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Stratégie large : on prend tout ce qui ressemble à un titre
        potential_links = soup.select('h2 a') + soup.select('h3 a') + soup.find_all('a', href=True)
        
        for link in potential_links:
            href = link.get('href')
            text = link.get_text().strip()
            
            if not href or len(text) < 4: continue
            if any(bad in text for bad in BLACKLIST_TEXT): continue
            if source['keyword'] and source['keyword'] not in href: continue
            if "ebooxly.com" not in href and not href.startswith("/"): continue
            if any(item['title'] == text for item in links_found): continue
            
            full_url = href if href.startswith("http") else f"https://ebooxly.com{href}"
            links_found.append({'title': text, 'link': full_url, 'is_mine': True})
            if len(links_found) >= source['limit']: break
            
        return links_found
    except Exception as e: return []

def generate_html():
    # 1. SÉCURITÉ : On crée le dossier tout de suite
    ensure_public_folder()

    print("1. Génération Hybride (Livres)...")
    
    # Récupération Ebooxly
    my_books = []
    for source in SOURCES:
        my_books.extend(get_my_links(source))
    
    # Récupération Google News
    auth_news = get_external_news(AUTHORITY_RSS, limit=4)
    
    # Mode Secours : Si Ebooxly est inaccessible, on affiche au moins Google News
    if not my_books:
        print("ATTENTION : Aucun livre trouvé. Génération page de secours.")
        my_books = []

    # Sandwich
    if len(auth_news) >= 2:
        final_list = auth_news[:2] + my_books + auth_news[2:]
    else:
        final_list = my_books + auth_news

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مكتبة وأخبار الثقافة</title>
        <style>
            body {{ font-family: 'Tahoma', sans-serif; background: #fdfbf7; max-width: 800px; margin: 0 auto; padding: 20px; text-align: right; color:#333; }}
            h1 {{ color: #5d4037; text-align: center; border-bottom: 2px solid #d7ccc8; padding-bottom:15px; }}
            .article {{ margin-bottom: 10px; padding: 15px; border-radius: 4px; display:block; text-decoration:none; border: 1px solid #eee; }}
            
            .mine {{ background: #fff; border-right: 5px solid #5d4037; }}
            .mine:hover {{ background: #efebe9; }}
            .mine .title {{ color: #3e2723; font-weight: bold; font-size: 1.1em; }}
            
            .external {{ background: #fff; border-right: 5px solid #bdbdbd; }}
            .external .title {{ color: #616161; }}
            
            .tag {{ font-size: 0.8em; margin-bottom: 5px; display:block; }}
        </style>
    </head>
    <body>
        <h1>🏛️ Ebooxly - جديد الثقافة</h1>
        <p style="text-align:center; color:#888;">{datetime.datetime.now().strftime("%d/%m/%Y")}</p>
        <div id="content">
    """
    
    for item in final_list:
        css_class = "mine" if item['is_mine'] else "external"
        source_label = "📖 إصدار جديد" if item['is_mine'] else "📰 أخبار ثقافية (Google News)"
        
        html_content += f"""
        <a href="{item['link']}" class="article {css_class}" target="_blank">
            <span class="tag">{source_label}</span>
            <span class="title">{item['title']}</span>
        </a>
        """

    html_content += "</div></body></html>"
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("2. HTML Généré.")
    return True

if __name__ == "__main__":
    generate_html()