#!/usr/bin/env python3
"""Formal Frame — Double-line SVG border with corner ornaments and gold accents.
Navy + gold on warm ivory. Institutional, legal, academic gravitas.
"""
import os, sys

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#faf9f5','navy':'#1e2a4a','gold':'#b8975a','rule':'#d4cfc2'}
M = 56  # outer margin

GRAIN = ('<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.5"'
 ' numOctaves="3" stitchTiles="stitch" result="n"/>'
 '<feColorMatrix type="saturate" values="0" in="n" result="m"/>'
 '<feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>')

def _frame(x, y, w, h, outer_sw=2, inner_sw=0.5, gap=7, op=1.0):
    """Double border: outer thick + inner thin with gap."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
     f'fill="none" stroke="{C["navy"]}" stroke-width="{outer_sw}" opacity="{op}"/>'
     f'<rect x="{x+gap}" y="{y+gap}" width="{w-2*gap}" height="{h-2*gap}" '
     f'fill="none" stroke="{C["navy"]}" stroke-width="{inner_sw}" opacity="{op}"/>')

def _corners(x, y, w, h, arm=30, dia=4, sw=1.5, op=0.7):
    """L-bracket corners with diamond at each corner of the given rect."""
    corners = [(x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)]
    out = ''
    for cx,cy,dx,dy in corners:
        out += (f'<path d="M{cx},{cy+dy*arm} L{cx},{cy} L{cx+dx*arm},{cy}" '
         f'fill="none" stroke="{C["gold"]}" stroke-width="{sw}" opacity="{op}"/>')
        if dia > 0:
            out += (f'<polygon points="{cx+dx*6},{cy} {cx},{cy+dy*6} '
             f'{cx-dx*6},{cy} {cx},{cy-dy*6}" '
             f'fill="{C["gold"]}" opacity="{op*0.55}"/>')
    return out

SVG = lambda body: (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
 f'<style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;'
 f'background:{C["bg"]}}}</style></head><body>'
 f'<svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">'
 f'<defs>{GRAIN}</defs><rect width="100%" height="100%" fill="{C["bg"]}"/>'
 f'{body}<rect width="100%" height="100%" filter="url(#g)" opacity="0.04"/>'
 f'</svg></body></html>')

W, H = PAGE_W, PAGE_H
cx = W // 2
# Cover frame coords
fx, fy, fw, fh = M, M, W-2*M, H-2*M

COVER = SVG(f'''
{_frame(fx, fy, fw, fh)}
{_corners(fx, fy, fw, fh, arm=35, dia=5, sw=1.6, op=0.65)}
<!-- Gold rule under title zone -->
<line x1="{fx+45}" y1="225" x2="{fx+fw-45}" y2="225"
 stroke="{C['gold']}" stroke-width="0.6" opacity="0.35"/>
<!-- Bottom author separator -->
<line x1="{cx-100}" y1="1012" x2="{cx+100}" y2="1012"
 stroke="{C['gold']}" stroke-width="0.7" opacity="0.45"/>
<!-- Diamond below separator -->
<polygon points="{cx},{1026} {cx+5},{1033} {cx},{1040} {cx-5},{1033}"
 fill="{C['gold']}" opacity="0.40"/>
<!-- Flanking dots -->
<circle cx="{cx-15}" cy="1033" r="1.3" fill="{C['gold']}" opacity="0.30"/>
<circle cx="{cx+15}" cy="1033" r="1.3" fill="{C['gold']}" opacity="0.30"/>''')

# Body frame coords
bx, by = M+14, M-4
bw, bh = W-2*M-28, H-2*M+8
BODY = SVG(f'''
<rect x="{bx}" y="{by}" width="{bw}" height="{bh}"
 fill="none" stroke="{C['rule']}" stroke-width="0.5"/>
{_corners(bx, by, bw, bh, arm=15, dia=0, sw=1.0, op=0.40)}
<!-- Footer rule -->
<line x1="{cx-50}" y1="{by+bh-18}" x2="{cx+50}" y2="{by+bh-18}"
 stroke="{C['gold']}" stroke-width="0.5" opacity="0.30"/>''')

# Backcover frame coords
BACK = SVG(f'''
{_frame(fx, fy, fw, fh, outer_sw=1.5, inner_sw=0.4, gap=6)}
{_corners(fx, fy, fw, fh, arm=26, dia=4, sw=1.3, op=0.55)}
<!-- Center ornament -->
<line x1="{cx-70}" y1="{H//2}" x2="{cx+70}" y2="{H//2}"
 stroke="{C['gold']}" stroke-width="0.6" opacity="0.35"/>
<polygon points="{cx},{H//2-5} {cx+4},{H//2} {cx},{H//2+5} {cx-4},{H//2}"
 fill="{C['gold']}" opacity="0.30"/>''')

def _render(tpl, out):
    from playwright.sync_api import sync_playwright
    os.makedirs(out, exist_ok=True)
    pairs = list(tpl.items())
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': PAGE_W, 'height': PAGE_H}, device_scale_factor=2)
        for n, h in pairs:
            pg.set_content(h)
            pg.screenshot(path=os.path.join(out, n), type='png')
            print(n)
        b.close()

if __name__=='__main__':
    out=sys.argv[1] if len(sys.argv)>1 else os.path.dirname(os.path.abspath(__file__))
    _render({'cover_bg.png':COVER,'backcover_bg.png':BACK,'body_bg.png':BODY},out)
    print("Done - Formal Frame")
