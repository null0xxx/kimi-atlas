#!/usr/bin/env python3
"""Warm Gradient — Smooth horizontal SVG gradient bands with subtle wave edges.
Warm earth tones transitioning to cool mist. Like sunset light falling across paper.
"""
import os, sys

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#faf8f5','warm':'#8b6f4e','cool':'#5a7a8a','cream':'#e8dfd3',
     'mist':'#c8d4d8','gold':'#a08050','rose':'#9e7e6b'}

DEFS = f'''<defs>
<linearGradient id="gw" x1="0" y1="0" x2="1" y2="0.3">
 <stop offset="0%" stop-color="{C['warm']}" stop-opacity="0.18"/>
 <stop offset="55%" stop-color="{C['rose']}" stop-opacity="0.12"/>
 <stop offset="100%" stop-color="{C['cool']}" stop-opacity="0.09"/>
</linearGradient>
<linearGradient id="gc" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0%" stop-color="{C['cream']}" stop-opacity="0.28"/>
 <stop offset="100%" stop-color="{C['mist']}" stop-opacity="0.16"/>
</linearGradient>
<linearGradient id="gv" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0%" stop-color="{C['warm']}" stop-opacity="0.06"/>
 <stop offset="45%" stop-color="{C['bg']}" stop-opacity="0"/>
 <stop offset="100%" stop-color="{C['cool']}" stop-opacity="0.05"/>
</linearGradient>
<filter id="gr"><feTurbulence type="fractalNoise" baseFrequency="0.55"
 numOctaves="3" stitchTiles="stitch" result="n"/>
 <feColorMatrix type="saturate" values="0" in="n" result="m"/>
 <feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>
</defs>'''

SVG = lambda body: (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
 f'<style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;'
 f'background:{C["bg"]}}}</style></head><body>'
 f'<svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">'
 f'{DEFS}<rect width="100%" height="100%" fill="{C["bg"]}"/>'
 f'{body}<rect width="100%" height="100%" filter="url(#gr)" opacity="0.04"/>'
 f'</svg></body></html>')

W = PAGE_W
COVER = SVG(f'''
<!-- Full-page vertical wash -->
<rect width="100%" height="100%" fill="url(#gv)"/>
<!-- Wide warm top band with gentle wave bottom -->
<path d="M0,0 L{W},0 L{W},220 Q{W*0.8},235 {W*0.6},225
 Q{W*0.35},210 {W*0.15},228 Q{W*0.05},232 0,230 Z" fill="url(#gw)"/>
<!-- Thin secondary ribbon -->
<path d="M0,226 Q{W*0.1},230 {W*0.2},224 Q{W*0.4},208 {W*0.65},222
 Q{W*0.85},233 {W},218 L{W},240 Q{W*0.8},252 {W*0.55},242
 Q{W*0.3},230 {W*0.1},248 Q{W*0.03},252 0,250 Z" fill="url(#gc)"/>
<!-- Bottom cool band -->
<path d="M0,940 Q{W*0.2},932 {W*0.45},938 Q{W*0.7},944 {W},935
 L{W},{PAGE_H} L0,{PAGE_H} Z" fill="url(#gw)"/>
<!-- Thin cool accent strip at very bottom -->
<path d="M0,1000 Q{W*0.3},992 {W*0.6},998 Q{W*0.85},1004 {W},996
 L{W},{PAGE_H} L0,{PAGE_H} Z" fill="url(#gc)" opacity="0.5"/>
<!-- Gold accent line left-aligned -->
<line x1="80" y1="900" x2="300" y2="900" stroke="{C['gold']}"
 stroke-width="1" opacity="0.40"/>
<circle cx="306" cy="900" r="2" fill="{C['gold']}" opacity="0.35"/>''')

BODY = SVG(f'''
<!-- Whisper of warm at top -->
<rect x="0" y="0" width="{W}" height="8" fill="url(#gw)" opacity="0.6"/>
<!-- Whisper of cool at bottom -->
<rect x="0" y="{PAGE_H-6}" width="{W}" height="6" fill="url(#gc)" opacity="0.5"/>
<!-- Full page vertical wash barely visible -->
<rect width="100%" height="100%" fill="url(#gv)" opacity="0.5"/>''')

BACK = SVG(f'''
<rect width="100%" height="100%" fill="url(#gv)"/>
<!-- Top warm band wider than cover bottom -->
<path d="M0,0 L{W},0 L{W},280 Q{W*0.75},296 {W*0.5},282
 Q{W*0.25},268 0,284 Z" fill="url(#gw)"/>
<!-- Bottom cool band -->
<path d="M0,820 Q{W*0.3},810 {W*0.55},818 Q{W*0.8},826 {W},815
 L{W},{PAGE_H} L0,{PAGE_H} Z" fill="url(#gc)"/>
<!-- Centered accent line -->
<line x1="{W//2-80}" y1="770" x2="{W//2+80}" y2="770"
 stroke="{C['gold']}" stroke-width="0.7" opacity="0.22"/>
<circle cx="{W//2}" cy="770" r="1.2" fill="{C['gold']}" opacity="0.20"/>''')

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
    print("Done - Warm Gradient")
