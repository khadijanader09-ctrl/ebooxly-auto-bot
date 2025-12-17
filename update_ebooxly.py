import cloudscraper
import feedparser
import os
import datetime
import json
import random

# --- CONFIGURATION ---
MY_SITE_URL = "https://ebooxly.com"
# On tape directement dans la source de données du site (plus fiable que le HTML)
MY_API_URL = "https://ebooxly.com/books_pages/page-1.json?v=1"

# Google News (Culture, Littérature, Éducation en Arabe)
AUTHORITY_RSS = "https://news.google.com/rss/search?q=كتب+روايات+ثقافة+أدب&hl=ar&gl=EG&ceid=EG:ar"
OUTPUT_FILE = "public/index.html"

# Images pour Google News (Thème : Livres, Bibliothèques, Écriture)
THEMATIC_IMAGES = [
    "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?auto=format&fit=crop&w=600&q=80", # Library
    "https://images.unsplash.com/photo-1507842217121-ad5596e65d31?auto=format&fit=crop&w=600&q=80", # Open book
    "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=600&q=80", # Reading
    "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80", # Book pile
    "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&q=80", # Pen and paper
    "https://images.unsplash.com/photo-1519682337058-a5ca051231de?auto=format&fit=crop&w=600&q=80"  # Cover close up
]
FALLBACK_IMG = "https://ebooxly.com/imgs/book.png"

# SEO ARABE
SEO_DESC = "اكتشف أحدث الكتب العربية والأخبار الثقافية. مكتبة eBooxly تجمع لك جديد الأدب والمعرفة."
SEO_KEYWORDS = "كتب, تحميل كتب, روايات, ثقافة, أخبار الأدب, ebooxly, pdf"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def clean_html(raw_html):
    if not raw_html: return ""
    import re
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text[:100] + "..."

def get_external_news(rss_url, limit=4):
    print(f"   -> 🌍 Google News (Culture Arabe)...")
    try:
        response = scraper.get(rss_url)
        feed = feedparser.parse(response.content)
        links = []
        if not feed.entries: return []

        for entry in feed.entries:
            img_src = random.choice(THEMATIC_IMAGES)
            desc = clean_html(entry.description) if hasattr(entry, 'description') else ""
            
            links.append({
                'title': entry.title, 
                'link': entry.link, 
                'img': img_src, 
                'desc': desc,
                'author': 'أخبار ثقافية', # "Cultural News"
                'tag': 'ثقافة وأدب',      # "Culture & Lit"
                'source': 'Google News',
                'is_mine': False
            })
            if len(links) >= limit: break
        return links
    except Exception as e:
        print(f"      [!] Erreur Google: {e}")
        return []

def get_my_books():
    print(f"   -> 📚 Ebooxly API (JSON)...")
    try:
        # On appelle le fichier JSON directement
        response = scraper.get(MY_API_URL)
        
        if response.status_code != 200: 
            print(f"      [!] Erreur API: {response.status_code}")
            return []

        # Le JSON contient une liste de livres dans 'items' ou directement en liste
        data = response.json()
        items = data if isinstance(data, list) else data.get('items', [])
        
        my_links = []
        
        for book in items:
            # Extraction des données du JSON eBooxly
            title = book.get('title', '')
            author = book.get('author', 'مؤلف غير معروف')
            img = book.get('image', FALLBACK_IMG)
            
            # Reconstruction des liens (basé sur la logique JS du site)
            # Les liens dépendent souvent de la lettre/auteur/titre
            # Si le JSON donne un lien direct, on le prend, sinon on fabrique
            # Ici on va essayer de fabriquer ou prendre ce qui existe
            
            # Note: Si le JSON ne contient pas d'URL complète, on pointe vers la recherche
            # ou on essaie de construire l'URL si on a les slugs
            l_slug = book.get('letter', 'a')
            a_slug = book.get('author_slug', 'unknown')
            t_slug = book.get('title_slug', 'unknown')
            
            url = f"{MY_SITE_URL}/authors/{l_slug}/{a_slug}/{t_slug}.html"
            
            # Correction image relative
            if img and not img.startswith('http'):
                img = f"{MY_SITE_URL}/{img.lstrip('/')}"

            # Catégories
            cats = book.get('categories', '')
            first_cat = cats.split('-')[0].strip() if cats else 'كتب عامة'

            my_links.append({
                'title': title, 
                'link': url, 
                'img': img, 
                'desc': '', # Pas de description longue dans le JSON liste
                'author': author,
                'tag': first_cat,
                'source': 'eBooxly',
                'is_mine': True
            })

            if len(my_links) >= 8: break # On prend 8 livres
        
        print(f"      > {len(my_links)} livres récupérés via API.")
        return my_links

    except Exception as e:
        print(f"      [!] Erreur API : {e}")
        return []

def generate_html():
    print("1. Génération Design Arabe (RTL)...")
    
    my_books = get_my_books()
    auth_news = get_external_news(AUTHORITY_RSS, limit=4)
    
    final_list = []
    if not my_books: my_books = []
    if not auth_news: auth_news = []
    
    # Mélange : 2 livres, 1 news, 2 livres, 1 news...
    idx_news = 0
    for i, book in enumerate(my_books):
        final_list.append(book)
        # Toutes les 2 livres, on insère une news si dispo
        if (i + 1) % 2 == 0 and idx_news < len(auth_news):
            final_list.append(auth_news[idx_news])
            idx_news += 1
            
    # Ajouter le reste des news si il en reste
    while idx_news < len(auth_news):
        final_list.append(auth_news[idx_news])
        idx_news += 1

    now_str = datetime.datetime.now().strftime("%Y/%m/%d")
    year = datetime.datetime.now().year

    # JSON-LD pour les livres
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Library",
        "name": "eBooxly",
        "url": "https://ebooxly.com",
        "logo": "https://ebooxly.com/imgs/logo.png"
    }

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>eBooxly - جديد المكتبة والأخبار</title>
        <meta name="description" content="{SEO_DESC}">
        <meta name="keywords" content="{SEO_KEYWORDS}">
        <link rel="icon" href="https://ebooxly.com/imgs/favicon.ico">
        
        <script type="application/ld+json">
        {json.dumps(json_ld)}
        </script>

        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;800&display=swap" rel="stylesheet">
        
        <style>
            :root{{
                --bg: #f5fcfb; --card: #ffffff; --text: #1f2937; 
                --brand: #2fae6b; --accent: #ffbf00; --line: #e5e7eb;
                --shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            }}
            body{{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:'Tajawal', sans-serif;}}
            a{{color:inherit;text-decoration:none;transition:.2s}}
            .container{{max-width:1100px;margin:0 auto;padding:0 15px}}
            
            /* HEADER */
            nav {{
                background:#ffffffcc; backdrop-filter:blur(6px);
                border-bottom:2px solid var(--accent);
                padding:.75rem 1rem; position:sticky; top:0; z-index:50;
                display:flex; justify-content:space-between; align-items:center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            }}
            .logo {{ display:flex; align-items:center; gap:.5rem; font-weight:800; font-size:1.3rem; color:#1f2937; }}
            .logo span {{ background:var(--brand); color:#fff; padding:.2rem .5rem; border-radius:.5rem; }}
            
            .nav-links a {{ font-weight:700; color:#1f2937; margin-left:15px; font-size:0.95rem; }}
            .nav-links a:hover {{ color:var(--brand); }}

            /* GRID & CARDS */
            .main-title {{ text-align:center; margin:30px 0; font-weight:800; color:var(--text); }}
            .grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); 
                gap: 20px; margin-bottom: 40px; 
            }}
            
            .book-card {{
                background: var(--card); border: 1px solid var(--line);
                border-radius: 8px; overflow: hidden; box-shadow: var(--shadow);
                display: flex; flex-direction: column; transition: transform 0.2s;
                position: relative;
            }}
            .book-card:hover {{ transform: translateY(-5px); border-color:var(--brand); }}
            
            /* Design spécial pour News vs Livre */
            .is-news {{ border-top: 4px solid var(--accent); }}
            .is-book {{ border-top: 4px solid var(--brand); }}

            .card-img {{
                height: 280px; width: 100%; overflow: hidden; background: #f3f4f6; position: relative;
            }}
            .card-img img {{
                width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;
            }}
            .is-book .card-img img {{ object-fit: contain; padding: 10px; }} /* Livres en entier */
            .is-news .card-img img {{ object-fit: cover; }} /* News en plein cadre */
            
            .book-card:hover img {{ transform: scale(1.05); }}
            
            .card-body {{ padding: 15px; flex-grow: 1; display: flex; flex-direction: column; }}
            
            .card-tag {{ 
                font-size: 0.7rem; color: #fff; padding: 3px 8px; 
                border-radius: 10px; width: fit-content; margin-bottom: 8px; font-weight: bold;
            }}
            .tag-news {{ background: var(--accent); color: #000; }}
            .tag-book {{ background: var(--brand); }}

            .card-title {{ font-size: 1rem; font-weight: 700; margin: 0 0 5px 0; line-height: 1.4; }}
            .card-sub {{ font-size: 0.85rem; color: #64748b; margin-bottom: 10px; }}
            
            /* FOOTER */
            footer {{ background: #fff; border-top: 1px solid var(--line); padding: 30px; text-align: center; margin-top: auto; }}
            .f-links a {{ margin: 0 10px; color: var(--brand); font-weight: 700; font-size: 0.9rem; }}
            
            @media (max-width: 600px) {{
                .grid {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
                .card-img {{ height: 200px; }}
            }}
        </style>
    </head>
    <body>

    <nav>
        <a href="https://ebooxly.com" class="logo">
            <span>📚</span> مكتبة الكتب
        </a>
        <div class="nav-links">
            <a href="https://ebooxly.com/categories/index.html">التصنيفات</a>
            <a href="https://ebooxly.com/authors/index.html">المؤلفون</a>
        </div>
    </nav>

    <div class="container">
        <div style="text-align:center; padding: 20px 0; border-bottom:1px solid var(--line); margin-bottom:20px;">
            <h2 style="margin:0; color:var(--brand);">أحدث الإضافات والأخبار</h2>
            <span style="color:#888; font-size:0.9rem;">تحديث: {now_str}</span>
        </div>

        <div class="grid">
    """

    for item in final_list:
        fallback = random.choice(THEMATIC_IMAGES)
        css_type = "is-book" if item['is_mine'] else "is-news"
        tag_css = "tag-book" if item['is_mine'] else "tag-news"
        
        # Gestion des erreurs d'image (onError)
        # Si c'est un livre et que l'image plante -> Fallback Livre
        # Si c'est une news et que l'image plante -> Fallback Thématique
        err_img = FALLBACK_IMG if item['is_mine'] else fallback
        
        html_content += f"""
        <article class="book-card {css_type}">
            <a href="{item['link']}" class="card-img" target="_blank">
                <img src="{item['img']}" alt="{item['title']}" loading="lazy" onerror="this.src='{err_img}'">
            </a>
            <div class="card-body">
                <span class="card-tag {tag_css}">{item['tag']}</span>
                <h3 class="card-title"><a href="{item['link']}" target="_blank">{item['title']}</a></h3>
                <div class="card-sub">{item['author']}</div>
            </div>
        </article>
        """

    html_content += f"""
        </div>
    </div>

    <footer>
        <div class="f-links">
            <a href="https://ebooxly.com/pages/about.html">من نحن</a>
            <a href="https://ebooxly.com/pages/privacy.html">الخصوصية</a>
            <a href="https://ebooxly.com/pages/contact.html">اتصل بنا</a>
        </div>
        <p style="margin-top:15px; color:#888; font-size:0.8rem;">© {year} eBooxly - جميع الحقوق محفوظة</p>
    </footer>

    </body>
    </html>
    """

    if not os.path.exists("public"):
        os.makedirs("public")
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("2. HTML Ebooxly (Arabe) généré.")
    return True

if __name__ == "__main__":
    if generate_html():
        os.system("firebase deploy --only hosting")
