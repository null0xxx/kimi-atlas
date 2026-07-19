#!/usr/bin/env python3
"""Swiss Grid — Precise thin lines, mathematical rhythm, one red accent.
Inspired by International Typographic Style. Clean, rational, authoritative.
DO NOT COPY — create your own. Learn the SVG line + circle precision technique.
"""
import os, sys

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#fafaf8','line':'#c0c0bc','fine':'#d8d8d4','dark':'#1a1a1a','red':'#c8372d'}

GRAIN = '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" result="n"/><feColorMatrix type="saturate" values="0" in="n" result="m"/><feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>'
SVG = lambda body: f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;background:{C["bg"]}}}</style></head><body><svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">{GRAIN}<rect width="100%" height="100%" fill="{C["bg"]}"/>{body}<rect width="100%" height="100%" filter="url(#g)" opacity="0.025"/></svg></body></html>'

COVER = SVG(f'''
<!-- Upper-right quadrant: partial grid with varying weights -->
<line x1="490" y1="68" x2="490" y2="310" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="570" y1="68" x2="570" y2="310" stroke="{C['line']}" stroke-width="0.6"/>
<line x1="650" y1="68" x2="650" y2="310" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="730" y1="68" x2="730" y2="250" stroke="{C['dark']}" stroke-width="1.0" opacity="0.25"/>
<!-- Horizontal cross-lines, staggered -->
<line x1="490" y1="120" x2="754" y2="120" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="530" y1="190" x2="754" y2="190" stroke="{C['line']}" stroke-width="0.6"/>
<line x1="490" y1="260" x2="730" y2="260" stroke="{C['dark']}" stroke-width="1.0" opacity="0.25"/>
<!-- Red accent: short, precise, left-aligned -->
<line x1="72" y1="360" x2="190" y2="360" stroke="{C['red']}" stroke-width="1.8"/>
<!-- Registration mark at one grid intersection -->
<circle cx="570" cy="190" r="2.5" fill="none" stroke="{C['dark']}" stroke-width="0.5"/>
<line x1="563" y1="190" x2="577" y2="190" stroke="{C['dark']}" stroke-width="0.35"/>
<line x1="570" y1="183" x2="570" y2="197" stroke="{C['dark']}" stroke-width="0.35"/>
<!-- Bottom rule -->
<line x1="72" y1="1058" x2="722" y2="1058" stroke="{C['dark']}" stroke-width="0.5"/>
<!-- Tiny red dot as anchor -->
<circle cx="72" cy="1010" r="2.5" fill="{C['red']}" opacity="0.55"/>''')

BODY = SVG(f'''
<!-- Top hairline -->
<line x1="72" y1="50" x2="722" y2="50" stroke="{C['fine']}" stroke-width="0.3"/>
<!-- Bottom hairline -->
<line x1="72" y1="1073" x2="722" y2="1073" stroke="{C['fine']}" stroke-width="0.3"/>
<!-- Red dot echoes cover -->
<circle cx="722" cy="50" r="1.5" fill="{C['red']}" opacity="0.35"/>''')

BACK = SVG(f'''
<!-- Lower-right grid echo: mirrors cover's upper-right quadrant -->
<line x1="510" y1="830" x2="510" y2="1050" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="590" y1="830" x2="590" y2="1050" stroke="{C['line']}" stroke-width="0.6"/>
<line x1="670" y1="860" x2="670" y2="1050" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="510" y1="900" x2="720" y2="900" stroke="{C['fine']}" stroke-width="0.3"/>
<line x1="510" y1="970" x2="720" y2="970" stroke="{C['line']}" stroke-width="0.6"/>
<!-- Red rule: echoing cover accent -->
<line x1="72" y1="850" x2="310" y2="850" stroke="{C['red']}" stroke-width="1.4"/>
<!-- Registration mark echoing cover -->
<circle cx="590" cy="970" r="2" fill="none" stroke="{C['dark']}" stroke-width="0.4"/>
<!-- Anchor dot -->
<circle cx="72" cy="790" r="2" fill="{C['red']}" opacity="0.4"/>''')

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
    _render({'cover_bg.png':COVER,'backcover_bg.png':BACK,'body_bg.png':BODY},out);print("Done - Swiss Grid")
