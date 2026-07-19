"""
OOXML shared utility functions

Provides shared ZIP-internal XML update logic used by docx_footnote / docx_endnote.
"""
from lxml import etree
from pathlib import Path


def update_document_rels(temp_path, nsmap):
    """Update document.xml.rels to ensure footnotes/endnotes relationships exist."""
    rels_path = temp_path / 'word' / '_rels' / 'document.xml.rels'

    if not rels_path.exists():
        rels_dir = temp_path / 'word' / '_rels'
        rels_dir.mkdir(parents=True, exist_ok=True)
        rels = etree.Element(
            '{http://schemas.openxmlformats.org/package/2006/relationships}Relationships'
        )
        etree.ElementTree(rels).write(str(rels_path), encoding='utf-8', xml_declaration=True)

    tree = etree.parse(str(rels_path))
    root = tree.getroot()
    ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}

    existing = {rel.get('Target') for rel in root.findall('.//r:Relationship', ns)}

    max_id = 0
    for rel in root.findall('.//r:Relationship', ns):
        rid = rel.get('Id', '')
        if rid.startswith('rId'):
            try:
                max_id = max(max_id, int(rid[3:]))
            except ValueError:
                pass

    for target, rel_type in [
        ('footnotes.xml', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes'),
        ('endnotes.xml', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes'),
    ]:
        if target not in existing:
            max_id += 1
            el = etree.SubElement(root, f'{{{ns["r"]}}}Relationship')
            el.set('Id', f'rId{max_id}')
            el.set('Type', rel_type)
            el.set('Target', target)

    tree.write(str(rels_path), encoding='utf-8', xml_declaration=True)


def update_content_types(temp_path, nsmap):
    """Update [Content_Types].xml to ensure footnotes/endnotes type declarations exist."""
    ct_path = temp_path / '[Content_Types].xml'
    tree = etree.parse(str(ct_path))
    root = tree.getroot()
    ns = {'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'}

    existing = {o.get('PartName') for o in root.findall('.//ct:Override', ns)}

    for part, content_type in [
        ('/word/footnotes.xml', 'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml'),
        ('/word/endnotes.xml', 'application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml'),
    ]:
        if part not in existing:
            el = etree.SubElement(root, f'{{{ns["ct"]}}}Override')
            el.set('PartName', part)
            el.set('ContentType', content_type)

    tree.write(str(ct_path), encoding='utf-8', xml_declaration=True)


def ensure_footnote_styles(temp_path, nsmap):
    """Ensure FootnoteText / FootnoteReference styles in styles.xml have correct font size.

    If the style already exists (e.g. from Pandoc), forcefully overwrite its rPr
    to guarantee small font size. If missing, inject from scratch.
    """
    styles_path = temp_path / 'word' / 'styles.xml'
    if not styles_path.exists():
        return

    tree = etree.parse(str(styles_path))
    root = tree.getroot()
    w = nsmap['w']

    def _qn(tag):
        return f'{{{w}}}{tag}'

    existing = {
        s.get(_qn('styleId')): s
        for s in root.findall(f'.//{_qn("style")}')
    }

    # ── FootnoteText ──
    ft = existing.get('FootnoteText')
    if ft is None:
        ft = etree.SubElement(root, _qn('style'), {
            _qn('type'): 'paragraph',
            _qn('styleId'): 'FootnoteText',
        })
        etree.SubElement(ft, _qn('name'), {_qn('val'): 'Footnote Text'})
        etree.SubElement(ft, _qn('basedOn'), {_qn('val'): 'Normal'})

    # Force spacing on pPr
    pPr = ft.find(_qn('pPr'))
    if pPr is None:
        pPr = etree.SubElement(ft, _qn('pPr'))
    sp = pPr.find(_qn('spacing'))
    if sp is None:
        sp = etree.SubElement(pPr, _qn('spacing'))
    sp.set(_qn('before'), '0')
    sp.set(_qn('after'), '0')
    sp.set(_qn('line'), '200')
    sp.set(_qn('lineRule'), 'exact')

    # Force font size on rPr
    rPr = ft.find(_qn('rPr'))
    if rPr is None:
        rPr = etree.SubElement(ft, _qn('rPr'))
    for tag in ('sz', 'szCs'):
        el = rPr.find(_qn(tag))
        if el is None:
            el = etree.SubElement(rPr, _qn(tag))
        el.set(_qn('val'), '18')

    # ── FootnoteReference ──
    fr = existing.get('FootnoteReference')
    if fr is None:
        fr = etree.SubElement(root, _qn('style'), {
            _qn('type'): 'character',
            _qn('styleId'): 'FootnoteReference',
        })
        etree.SubElement(fr, _qn('name'), {_qn('val'): 'Footnote Reference'})
        rPr = etree.SubElement(fr, _qn('rPr'))
        etree.SubElement(rPr, _qn('vertAlign'), {_qn('val'): 'superscript'})

    tree.write(str(styles_path), encoding='utf-8', xml_declaration=True)
