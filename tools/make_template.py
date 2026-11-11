"""入金伝票のテンプレートPDFを 素材/入金伝票.svg から作り直すスクリプト。

使い方（支払伝票PJ フォルダで）:
    python deposit-slip-app/tools/make_template.py
出力:
    deposit-slip-app/tools/out/nyukin_tpl.pdf … テンプレートPDF（A5横 595.32×419.52pt）
    deposit-slip-app/tools/out/nyukin_tpl.b64 … 入金伝票.html の TEMPLATE_B64 に貼る文字列
必要: Python + playwright（Chrome） + pymupdf

SVG（Inkscape製）は A4ページの上部に A5横の伝票が描かれているので、viewBox を A5 範囲に切り出し、
Chrome で印刷して PDF にする。SVGに無い「経理部」の縦書きラベルはここで追加している。
Chrome の PDF は 594.96×420pt になるため、MediaBox を上端基準で 595.32×419.52pt に合わせる。
HTML内の座標（フォーム座標）は、このページを 793.76×559.36 とした値（1単位=0.75pt）。
"""
import os, re, base64
from playwright.sync_api import sync_playwright
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PJ = os.path.abspath(os.path.join(HERE, "..", ".."))
SVG = os.path.join(PJ, "素材", "入金伝票.svg")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

W_PX, H_PX = 793.76, 559.36
W_MM, H_MM = 595.32 / 72 * 25.4, 419.52 / 72 * 25.4
MM = W_MM / W_PX

t = open(SVG, encoding="utf-8").read()
t, n = re.subn(r'<svg\s+width="210mm"\s+height="297mm"\s+viewBox="0 0 210 297"',
               f'<svg width="{W_PX}px" height="{H_PX}px" viewBox="0 0 {W_MM:.4f} {H_MM:.4f}"', t, count=1)
assert n == 1, "SVGの先頭(width/height/viewBox)が想定と違います"
cx = (515.64 + 534.36) / 2  # 経理部セル x:515.64-534.36, y:448.3-543
t = t.replace('</svg>', ''.join(
    f'<text x="{cx*MM:.3f}" y="{cy*MM:.3f}" text-anchor="middle" dominant-baseline="central" '
    f'style="font-family:\'MS Mincho\';font-size:{13.15*MM:.3f}px;fill:#f93644">{ch}</text>'
    for ch, cy in (("経", 471.7), ("理", 495.65), ("部", 519.6))) + '</svg>')

html_path = os.path.join(OUT, "tpl.html")
open(html_path, "w", encoding="utf-8").write(
    '<!doctype html><html><head><meta charset="utf-8"><style>@page{size:595.32pt 419.52pt;margin:0}'
    'html,body{margin:0;padding:0}svg{display:block}</style></head><body>' + t[t.index('<svg'):] + '</body></html>')
raw_pdf = os.path.join(OUT, "raw.pdf")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page()
    pg.goto("file:///" + html_path.replace("\\", "/"))
    pg.pdf(path=raw_pdf, prefer_css_page_size=True, print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()

d = pymupdf.open(raw_pdf)
page = d[0]
x0, y0, x1, y1 = page.mediabox  # Chromeは 0 0 594.96 420
d.xref_set_key(page.xref, "MediaBox", f"[0 {y1 - 419.52:.2f} 595.32 {y1:.2f}]")
out_pdf = os.path.join(OUT, "nyukin_tpl.pdf")
d.save(out_pdf, garbage=4, deflate=True)
open(os.path.join(OUT, "nyukin_tpl.b64"), "w").write(base64.b64encode(open(out_pdf, "rb").read()).decode())
print("ok", pymupdf.open(out_pdf)[0].rect)
