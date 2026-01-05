import cloudscraper
import feedparser
import os
import datetime
import json
import random
from html import escape
from urllib.parse import quote

# --- CONFIGURATION ---
MY_SITE_URL = "https://ebooxly.com"
# On ne met plus d'URL fixe ici, elle sera générée aléatoirement

# Google News (Culture, Littérature, Éducation en Arabe)
AUTHORITY_RSS = "https://news.google.com/rss/search?q=كتب+روايات+ثقافة+أدب&hl=ar&gl=EG&ceid=EG:ar"
OUTPUT_DIR = "public"
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# Images pour Google News
THEMATIC_IMAGES = [
    "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1507842217121-ad5596e65d31?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1519682337058-a5ca051231de?auto=format&fit=crop&w=600&q=80"
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

        # On mélange les news aussi pour ne pas toujours avoir les mêmes en tête
        entries = feed.entries
        random.shuffle(entries)

        for entry in entries:
            img_src = random.choice(THEMATIC_IMAGES)
            desc = clean_html(entry.description) if hasattr(entry, 'description') else ""
            
            links.append({
                'title': entry.title, 
                'link': entry.link, 
                'img': img_src, 
                'desc': desc,
                'author': 'أخبار ثقافية',
                'tag': 'ثقافة وأدب',
                'source': 'Google News',
                'is_mine': False,
                'date': datetime.datetime.now()
            })
            if len(links) >= limit: break
        return links
    except Exception as e:
        print(f"      [!] Erreur Google: {e}")
        return []

def get_my_books():
    # --- MODIFICATION MAJEURE ICI ---
    # On choisit une page au hasard entre 1 et 30 pour avoir des livres différents à chaque fois
    random_page = random.randint(1, 30)
    target_url = f"https://ebooxly.com/books_pages/page-{random_page}.json?v=1"
    
    print(f"   -> 📚 eBooxly API (Page {random_page} - Mode Aléatoire)...")
    
    try:
        response = scraper.get(target_url)
        if response.status_code != 200: 
            # Si la page au hasard n'existe pas (ex: page 30 trop loin), on se rabat sur la page 1
            print(f"      [!] Page {random_page} vide, retour page 1.")
            target_url = "https://ebooxly.com/books_pages/page-1.json?v=1"
            response = scraper.get(target_url)

        data = response.json()
        items = data if isinstance(data, list) else data.get('items', [])
        
        # On mélange les livres de la page récupérée
        random.shuffle(items)
        
        my_links = []
        
        for book in items:
            title = book.get('title', '')
            author = book.get('author', 'مؤلف غير معروف')
            img = book.get('image', FALLBACK_IMG)
            
            l_slug = book.get('letter', 'a')
            a_slug = book.get('author_slug', 'unknown')
            t_slug = book.get('title_slug', 'unknown')
            
            url = f"{MY_SITE_URL}/authors/{l_slug}/{a_slug}/{t_slug}.html"
            
            if img and not img.startswith('http'):
                img = f"{MY_SITE_URL}/{img.lstrip('/')}"

            cats = book.get('categories', '')
            first_cat = cats.split('-')[0].strip() if cats else 'كتب عامة'

            my_links.append({
                'title': title, 
                'link': url, 
                'img': img, 
                'desc': f"تحميل كتاب {title} للمؤلف {author}",
                'author': author,
                'tag': first_cat,
                'source': 'eBooxly',
                'is_mine': True,
                'date': datetime.datetime.now()
            })

            if len(my_links) >= 8: break
        
        print(f"      > {len(my_links)} livres récupérés.")
        return my_links

    except Exception as e:
        print(f"      [!] Erreur API : {e}")
        return []

def build_rss_feed(items_list):
    print("📡 Génération du Flux RSS (public/feed.xml)...")
    
    RSS_TITLE = "eBooxly - المكتبة العربية"
    RSS_LINK = MY_SITE_URL
    RSS_DESC = "آخر الكتب المضافة والأخبار الثقافية"
    
    rss_items = ""
    
    for item in items_list:
        title = escape(item['title'])
        link = escape(item['link'])
        desc = escape(item['desc'])
        pub_date = item['date'].strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        img_source = item['img']
        
        if img_source and not img_source.startswith('http'):
             img_source = MY_SITE_URL + "/" + img_source.lstrip('/')

        if img_source:
            safe_u = quote(img_source, safe="")
            img_final = f"https://wsrv.nl/?url={safe_u}&w=1200&output=jpg&q=100"
        else:
            img_final = FALLBACK_IMG

        img_final = img_final.replace("&", "&amp;")
        img_tag = f'<enclosure url="{img_final}" type="image/jpeg" />'
        
        rss_items += f"""
        <item>
            <title>{title}</title>
            <link>{link}</link>
            <guid>{link}</guid>
            <description>{desc}</description>
            <pubDate>{pub_date}</pubDate>
            {img_tag}
        </item>"""
        
    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>{RSS_TITLE}</title>
    <link>{RSS_LINK}</link>
    <description>{RSS_DESC}</description>
    <language>ar</language>
    {rss_items}
</channel>
</rss>"""

    with open(f"{OUTPUT_DIR}/feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_content)
    print("✅ Flux RSS généré.")

def generate_html():
    print("1. Récupération des données...")
    
    my_books = get_my_books()
    auth_news = get_external_news(AUTHORITY_RSS, limit=4)
    
    final_list = []
    if not my_books: my_books = []
    if not auth_news: auth_news = []
    
    # Mélange intelligent
    idx_news = 0
    for i, book in enumerate(my_books):
        final_list.append(book)
        if (i + 1) % 2 == 0 and idx_news < len(auth_news):
            final_list.append(auth_news[idx_news])
            idx_news += 1
            
    while idx_news < len(auth_news):
        final_list.append(auth_news[idx_news])
        idx_news += 1

    build_rss_feed(final_list)

    now_str = datetime.datetime.now().strftime("%Y/%m/%d")
    year = datetime.datetime.now().year

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
            
            .is-news {{ border-top: 4px solid var(--accent); }}
            .is-book {{ border-top: 4px solid var(--brand); }}

            .card-img {{
                height: 280px; width: 100%; overflow: hidden; background: #f3f4f6; position: relative;
            }}
            .card-img img {{
                width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;
            }}
            .is-book .card-img img {{ object-fit: contain; padding: 10px; }}
            .is-news .card-img img {{ object-fit: cover; }}
            
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
            <h2 style="margin:0; color:var(--brand);">كتب مختارة وأخبار ثقافية</h2>
            <span style="color:#888; font-size:0.9rem;">تحديث: {now_str}</span>
        </div>

        <div class="grid">
    """

    for item in final_list:
        fallback = random.choice(THEMATIC_IMAGES)
        css_type = "is-book" if item['is_mine'] else "is-news"
        tag_css = "tag-book" if item['is_mine'] else "tag-news"
        
        err_img = FALLBACK_IMG if item['is_mine'] else fallback
        
        img_html = item['img']
        if "http" in img_html:
             safe_u = quote(img_html, safe="")
             img_html = f"https://wsrv.nl/?url={safe_u}&w=400&output=webp&q=80"
        
        html_content += f"""
        <article class="book-card {css_type}">
            <a href="{item['link']}" class="card-img" target="_blank">
                <img src="{img_html}" alt="{item['title']}" loading="lazy" onerror="this.src='{err_img}'">
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

    with open(f"{OUTPUT_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("2. HTML Ebooxly (Arabe) généré.")
    return True

if __name__ == "__main__":
    if generate_html():
        os.system("firebase deploy --only hosting")
