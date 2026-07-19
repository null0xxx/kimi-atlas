#!/usr/bin/env python3
"""Morandi Curves — Soft organic SVG curves with paper grain texture.
Warm neutral palette, flowing lines. Professional and calm.
DO NOT COPY this design — create your own. Learn the SVG + filter technique.
Technical: 794x1123px, device_scale_factor=2, center clear for text.
"""
import os, sys

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#f5f2ed','c1':'#7C9885','c2':'#8B9DC3','c3':'#B4A992','acc':'#C9A9A6'}

GRAIN = '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="3" stitchTiles="stitch" result="n"/><feColorMatrix type="saturate" values="0" in="n" result="m"/><feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>'
SVG = lambda body: f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;background:{C["bg"]}}}</style></head><body><svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">{GRAIN}<rect width="100%" height="100%" fill="{C["bg"]}"/>{body}<rect width="100%" height="100%" filter="url(#g)" opacity="0.04"/></svg></body></html>'

COVER = SVG(f'''
<path d="M450,-80 C580,30 720,110 844,80 L844,-80Z" fill="{C["c1"]}" opacity="0.055"/>
<path d="M530,-60 C640,40 760,130 844,100 L844,-60Z" fill="{C["c2"]}" opacity="0.04"/>
<path d="M-60,135 C120,85 340,185 520,145 S760,95 860,165" stroke="{C["c1"]}" stroke-width="2.5" fill="none" opacity="0.18"/>
<path d="M-60,162 C160,125 370,210 540,170 S730,125 860,183" stroke="{C["c2"]}" stroke-width="1.2" fill="none" opacity="0.12"/>
<path d="M-60,186 C190,158 410,222 560,192 S710,152 860,198" stroke="{C["c3"]}" stroke-width="0.6" fill="none" opacity="0.08"/>
<ellipse cx="690" cy="930" rx="210" ry="130" fill="{C["c1"]}" opacity="0.05" transform="rotate(-8 690 930)"/>
<ellipse cx="720" cy="955" rx="145" ry="88" fill="{C["c2"]}" opacity="0.04" transform="rotate(5 720 955)"/>
<ellipse cx="740" cy="975" rx="80" ry="50" fill="{C["c3"]}" opacity="0.035"/>
<circle cx="95" cy="975" r="32" fill="{C["acc"]}" opacity="0.1"/>
<circle cx="135" cy="1000" r="16" fill="{C["c1"]}" opacity="0.07"/>
<path d="M65,1060 C155,1052 260,1068 355,1055" stroke="{C["c1"]}" stroke-width="1" fill="none" opacity="0.2" stroke-linecap="round"/>
<path d="M70,1070 C145,1064 230,1076 300,1065" stroke="{C["c2"]}" stroke-width="0.5" fill="none" opacity="0.12" stroke-linecap="round"/>''')

BODY = SVG(f'''
<path d="M60,48 C250,42 500,55 734,46" stroke="{C["c1"]}" stroke-width="0.5" fill="none" opacity="0.15" stroke-linecap="round"/>
<path d="M60,1075 C250,1070 500,1080 734,1072" stroke="{C["c1"]}" stroke-width="0.5" fill="none" opacity="0.15" stroke-linecap="round"/>
<ellipse cx="-20" cy="-10" rx="130" ry="85" fill="{C["c3"]}" opacity="0.035" transform="rotate(15 -20 -10)"/>''')

BACK = SVG(f'''
<ellipse cx="140" cy="180" rx="180" ry="110" fill="{C["c2"]}" opacity="0.04" transform="rotate(12 140 180)"/>
<ellipse cx="110" cy="200" rx="120" ry="70" fill="{C["c1"]}" opacity="0.03" transform="rotate(-5 110 200)"/>
<path d="M-60,860 C180,820 400,890 600,850 S800,810 860,855" stroke="{C["c1"]}" stroke-width="1.8" fill="none" opacity="0.14"/>
<path d="M-60,880 C200,850 420,910 620,875 S780,840 860,870" stroke="{C["c2"]}" stroke-width="0.8" fill="none" opacity="0.09"/>
<circle cx="680" cy="1000" r="18" fill="{C["acc"]}" opacity="0.07"/>''')

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
    _render({'cover_bg.png':COVER,'backcover_bg.png':BACK,'body_bg.png':BODY},out);print("Done - Morandi Curves")
