from pathlib import Path

src = Path(r"C:\Users\islom\OneDrive\Desktop\Game\cardverse (1).html")
dst = Path(r"C:\Users\islom\OneDrive\Desktop\Game\club\templates\club\index.html")
dst.parent.mkdir(parents=True, exist_ok=True)
text = src.read_text(encoding="utf-8")

if not text.startswith("{% load static %}"):
    text = "{% load static %}\n" + text

old_title = "<title>CardVerse — Настольные Игры</title>"
new_title = """<title>CardVerse — Премиум карточный клуб</title>
    <meta name="csrf-token" content="{{ csrf_token }}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{% static 'club/premium.css' %}">"""
if old_title not in text:
    raise SystemExit("title not found")
text = text.replace(old_title, new_title, 1)

old_body = '<body class="min-h-screen text-slate-100 font-sans flex flex-col justify-between antialiased selection:bg-indigo-500 selection:text-white">'
new_body = old_body + """
    <div class="cv-ambient" aria-hidden="true">
        <div class="cv-orb cv-orb-a"></div>
        <div class="cv-orb cv-orb-b"></div>
        <div class="cv-orb cv-orb-c"></div>
        <div class="cv-grid"></div>
        <div class="cv-noise"></div>
    </div>
"""
if old_body not in text:
    raise SystemExit("body not found")
text = text.replace(old_body, new_body, 1)

old_footer = "    <!-- Registration / Login Modal -->"
new_footer = """    <footer class="cv-footer">
        <div class="cv-footer-inner">
            <div>
                <p class="cv-footer-brand">CardVerse</p>
                <p class="cv-footer-copy">Премиум клуб настольных карт · Django-платформа</p>
            </div>
            <div class="cv-footer-pills">
                <span>UNO Classic</span>
                <span>No Mercy</span>
                <span>UNO Flip</span>
                <span>Дурак</span>
            </div>
        </div>
    </footer>

    <!-- Registration / Login Modal -->"""
if old_footer not in text:
    raise SystemExit("footer anchor not found")
text = text.replace(old_footer, new_footer, 1)

old_end = "    </script>\n</body>"
new_end = "    </script>\n    <script src=\"{% static 'club/django-bridge.js' %}\"></script>\n</body>"
if old_end not in text:
    raise SystemExit("script end not found")
text = text.replace(old_end, new_end, 1)

dst.write_text(text, encoding="utf-8")
print("template written", dst, "chars", len(text))
