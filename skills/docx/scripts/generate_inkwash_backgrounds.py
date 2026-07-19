#!/usr/bin/env python3
"""Ink Wash 水墨 — SVG turbulence-based ink diffusion with calligraphic strokes.
Gray-scale, asymmetric composition, wabi-sabi aesthetic.
DO NOT COPY — create your own. Learn the feTurbulence + feDisplacementMap technique.
"""
import os, sys

PAGE_W, PAGE_H = 794, 1123
C = {'bg':'#f7f5f0','ink':'#3a3a3a','wash':'#8a8a7a','mist':'#c8c4b8'}

# SVG filters: ink blots with different turbulence characters
INK_FILTER = '''<filter id="ink" x="-20%" y="-20%" width="140%" height="140%">
<feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="4" seed="3" result="turb"/>
<feDisplacementMap in="SourceGraphic" in2="turb" scale="35" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="ink2" x="-20%" y="-20%" width="140%" height="140%">
<feTurbulence type="fractalNoise" baseFrequency="0.025" numOctaves="3" seed="7" result="turb"/>
<feDisplacementMap in="SourceGraphic" in2="turb" scale="22" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="ink3" x="-30%" y="-30%" width="160%" height="160%">
<feTurbulence type="fractalNoise" baseFrequency="0.01" numOctaves="5" seed="11" result="turb"/>
<feDisplacementMap in="SourceGraphic" in2="turb" scale="45" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="2" stitchTiles="stitch" result="n"/>
<feColorMatrix type="saturate" values="0" in="n" result="m"/><feBlend in="SourceGraphic" in2="m" mode="multiply"/></filter>'''

SVG = lambda body: f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0}}body{{width:{PAGE_W}px;height:{PAGE_H}px;background:{C["bg"]}}}</style></head><body><svg width="{PAGE_W}" height="{PAGE_H}" xmlns="http://www.w3.org/2000/svg">{INK_FILTER}<rect width="100%" height="100%" fill="{C["bg"]}"/>{body}<rect width="100%" height="100%" filter="url(#grain)" opacity="0.05"/></svg></body></html>'

COVER = SVG(f'''
<ellipse cx="650" cy="130" rx="300" ry="80" fill="{C["ink"]}" opacity="0.035" filter="url(#ink3)"/>
<ellipse cx="580" cy="155" rx="220" ry="55" fill="{C["wash"]}" opacity="0.04" filter="url(#ink)"/>
<ellipse cx="700" cy="170" rx="160" ry="40" fill="{C["ink"]}" opacity="0.05" filter="url(#ink2)"/>
<ellipse cx="100" cy="920" rx="140" ry="100" fill="{C["ink"]}" opacity="0.04" filter="url(#ink3)"/>
<ellipse cx="55" cy="960" rx="90" ry="65" fill="{C["wash"]}" opacity="0.035" filter="url(#ink)"/>
<ellipse cx="155" cy="985" rx="55" ry="40" fill="{C["ink"]}" opacity="0.03" filter="url(#ink2)"/>
<path d="M50,720 Q200,708 450,724 T734,715" stroke="{C["ink"]}" stroke-width="2" fill="none" opacity="0.1" stroke-linecap="round" filter="url(#ink2)"/>
<path d="M120,748 Q350,740 600,750" stroke="{C["wash"]}" stroke-width="0.5" fill="none" opacity="0.08" stroke-linecap="round"/>
<rect x="668" y="1015" width="32" height="32" fill="#B83A2A" opacity="0.35" rx="2"/>
<line x1="675" y1="1025" x2="693" y2="1025" stroke="#f7f5f0" stroke-width="1" opacity="0.5"/>
<line x1="684" y1="1020" x2="684" y2="1042" stroke="#f7f5f0" stroke-width="1" opacity="0.5"/>''')

BODY = SVG(f'''
<path d="M80,52 Q400,45 714,56" stroke="{C["ink"]}" stroke-width="1" fill="none" opacity="0.08" stroke-linecap="round" filter="url(#ink2)"/>
<ellipse cx="740" cy="1080" rx="80" ry="50" fill="{C["wash"]}" opacity="0.025" filter="url(#ink)"/>''')

BACK = SVG(f'''
<ellipse cx="220" cy="210" rx="280" ry="95" fill="{C["ink"]}" opacity="0.04" filter="url(#ink3)"/>
<ellipse cx="170" cy="240" rx="180" ry="60" fill="{C["wash"]}" opacity="0.035" filter="url(#ink)"/>
<ellipse cx="300" cy="255" rx="110" ry="40" fill="{C["ink"]}" opacity="0.03" filter="url(#ink2)"/>
<path d="M60,880 Q300,868 550,883 T734,875" stroke="{C["ink"]}" stroke-width="1.2" fill="none" opacity="0.08" stroke-linecap="round" filter="url(#ink2)"/>
<rect x="405" y="960" width="28" height="28" fill="#B83A2A" opacity="0.28" rx="2"/>''')

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
    _render({'cover_bg.png':COVER,'backcover_bg.png':BACK,'body_bg.png':BODY},out);print("Done - Ink Wash 水墨")
