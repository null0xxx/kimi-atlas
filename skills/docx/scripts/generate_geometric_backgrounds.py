#!/usr/bin/env python3
"""Geometric Arcs — Overlapping SVG arcs and circles, modern corporate feel.
Muted jewel tones, asymmetric composition, depth through transparency.
DO NOT COPY — create your own. Learn the SVG arc + opacity layering technique.
"""
import os, sys, math

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#f7f8fa','navy':'#1a3550','teal':'#0a6b6e','copper':'#a0714a','slate':'#556677'}

GRAIN = '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="3" stitchTiles="stitch" result="n"/><feColorMatrix type="saturate" values="0" in="n" result="m"/><feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>'
SVG = lambda body: f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;background:{C["bg"]}}}</style></head><body><svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">{GRAIN}<rect width="100%" height="100%" fill="{C["bg"]}"/>{body}<rect width="100%" height="100%" filter="url(#g)" opacity="0.03"/></svg></body></html>'

def _arc(cx, cy, r, s_deg, e_deg):
    s, e = math.radians(s_deg), math.radians(e_deg)
    x1, y1 = cx + r*math.cos(s), cy + r*math.sin(s)
    x2, y2 = cx + r*math.cos(e), cy + r*math.sin(e)
    big = 1 if abs(e_deg - s_deg) > 180 else 0
    return f"M {x1:.1f} {y1:.1f} A {r} {r} 0 {big} 1 {x2:.1f} {y2:.1f}"

# Cover: upper-right cluster + bottom-left corner peek
_cv1 = _arc(770, 60, 310, 150, 255)
_cv2 = _arc(770, 60, 225, 158, 238)
_cv3 = _arc(-60, 1060, 210, -45, 45)
_cv4 = _arc(-60, 1060, 145, -30, 25)

COVER = SVG(f'''
<path d="{_cv1}" fill="none" stroke="{C['navy']}" stroke-width="38" opacity="0.07" stroke-linecap="round"/>
<path d="{_cv2}" fill="none" stroke="{C['teal']}" stroke-width="1.5" opacity="0.16" stroke-linecap="round"/>
<path d="{_cv3}" fill="none" stroke="{C['copper']}" stroke-width="24" opacity="0.08" stroke-linecap="round"/>
<path d="{_cv4}" fill="none" stroke="{C['navy']}" stroke-width="1.2" opacity="0.13" stroke-linecap="round"/>
<circle cx="630" cy="820" r="5.5" fill="{C['teal']}" opacity="0.14"/>
<circle cx="648" cy="808" r="2" fill="{C['copper']}" opacity="0.24"/>
<line x1="260" y1="440" x2="540" y2="440" stroke="{C['slate']}" stroke-width="0.4" opacity="0.12"/>''')

# Body: whisper arcs at opposite corners
_bd1 = _arc(785, 20, 65, 135, 220)
_bd2 = _arc(15, 1103, 50, -50, 35)

BODY = SVG(f'''
<path d="{_bd1}" fill="none" stroke="{C['navy']}" stroke-width="12" opacity="0.035" stroke-linecap="round"/>
<path d="{_bd2}" fill="none" stroke="{C['teal']}" stroke-width="8" opacity="0.035" stroke-linecap="round"/>
<line x1="72" y1="50" x2="722" y2="50" stroke="{C['slate']}" stroke-width="0.3" opacity="0.12"/>''')

# Back: arcs anchored to right edge, not centered
_bk1 = _arc(820, 560, 340, 110, 230)
_bk2 = _arc(820, 560, 250, 120, 215)
_bk3 = _arc(820, 560, 165, 130, 200)

BACK = SVG(f'''
<path d="{_bk1}" fill="none" stroke="{C['navy']}" stroke-width="42" opacity="0.04" stroke-linecap="round"/>
<path d="{_bk2}" fill="none" stroke="{C['teal']}" stroke-width="1.5" opacity="0.1" stroke-linecap="round"/>
<path d="{_bk3}" fill="none" stroke="{C['copper']}" stroke-width="0.8" opacity="0.09" stroke-linecap="round"/>
<circle cx="460" cy="880" r="4" fill="{C['navy']}" opacity="0.16"/>''')

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
    _render({'cover_bg.png':COVER,'backcover_bg.png':BACK,'body_bg.png':BODY},out);print("Done - Geometric Arcs")
