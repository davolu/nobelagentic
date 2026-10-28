"""Render content/*.md → docs/*.html. Run: python build.py"""
import re, pathlib, markdown

ROOT = pathlib.Path(__file__).parent
SHELL = (ROOT / "shell.html").read_text()
pages = []
for md in (ROOT / "content").glob("*.md"):
    text = md.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = dict(l.split(":", 1) for l in m.group(1).splitlines())
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    pages.append((int(meta["order"]), md.stem, meta, m.group(2)))
pages.sort()
for i, (_, stem, meta, body) in enumerate(pages):
    html = markdown.markdown(
        body,
        extensions=["fenced_code", "tables", "codehilite"],
        extension_configs={"codehilite": {"css_class": "hl", "guess_lang": False}},
    )
    nav = "".join(f'<a href="{s}.html"{" aria-current=page" if s == stem else ""}>{mt["nav"]}</a>' for _, s, mt, _ in pages)
    prev = f'<a href="{pages[i-1][1]}.html">← {pages[i-1][2]["nav"]}</a>' if i else "<span></span>"
    nxt = f'<a href="{pages[i+1][1]}.html">{pages[i+1][2]["nav"]} →</a>' if i + 1 < len(pages) else "<span></span>"
    out = SHELL.replace("{{title}}", meta["title"]).replace("{{nav}}", nav).replace("{{body}}", html).replace("{{prev}}", prev).replace("{{next}}", nxt)
    out = re.sub(r'href="index\.html"', 'href="/docs/"', out); out = re.sub(r'href="([a-z]+)\.html(#[A-Za-z0-9_-]+)?"', r'href="/docs/\1\2"', out)
    (ROOT / "docs" / f"{stem}.html").write_text(out)
    print("built", stem)
