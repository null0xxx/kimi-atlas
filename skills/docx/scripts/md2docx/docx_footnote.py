#!/usr/bin/env python3
"""
Word document post-processing module: footnotes with NOTEREF cross-references

Strategy:
1. First occurrence: create footnote object (footnoteReference), content from citation_db
2. Subsequent occurrences: use NOTEREF field cross-reference (\\h \\f switches)
3. Original MD bibliography section is preserved as-is, no deletion
"""
import re
import logging
from zipfile import ZipFile
from lxml import etree
import tempfile
import shutil
from pathlib import Path
from collections import defaultdict

from docx.oxml.ns import qn
from docx_utils import update_document_rels, update_content_types, ensure_footnote_styles

logger = logging.getLogger(__name__)


def process_word_document_with_noteref(
    docx_path: str,
    output_path: str = None,
    citation_db: dict = None
) -> bool:
    """
    Process Word document using NOTEREF fields for footnote cross-references.
    Does not modify body paragraphs — only replaces superscript citation numbers.

    Args:
        docx_path: Input docx path
        output_path: Output path (None overwrites input)
        citation_db: {display_num: {url, page...}} mapping for footnote content
                     key is 1-based display number (sequential from citation_parser)
    """
    if output_path is None:
        output_path = docx_path

    try:
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        with ZipFile(docx_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)

        doc_xml_path = temp_path / 'word' / 'document.xml'
        tree = etree.parse(str(doc_xml_path))
        root = tree.getroot()

        nsmap = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

        # Scan body for superscript citation numbers, record all occurrences
        citation_all_occurrences = defaultdict(list)
        citation_first_occurrence = {}

        for para in root.findall('.//w:p', nsmap):
            for run in para.findall('.//w:r', nsmap):
                vert_align = run.find('.//w:vertAlign', nsmap)
                if vert_align is not None and vert_align.get(qn('w:val')) == 'superscript':
                    text_elem = run.find('.//w:t', nsmap)
                    if text_elem is not None and text_elem.text:
                        text = text_elem.text.strip()
                        if re.match(r'^\d+$', text):
                            num = int(text)
                            citation_all_occurrences[num].append((para, run))
                            if num not in citation_first_occurrence:
                                citation_first_occurrence[num] = (para, run)

        logger.info(f"Found {len(citation_first_occurrence)} unique citation numbers")
        logger.info(f"Total {sum(len(v) for v in citation_all_occurrences.values())} citation positions")

        # Create footnotes.xml (content from citation_db, fallback to number)
        footnotes_xml_path = temp_path / 'word' / 'footnotes.xml'
        footnotes_root = _create_footnotes(
            citation_first_occurrence.keys(),
            citation_db or {},
            nsmap
        )
        etree.ElementTree(footnotes_root).write(
            str(footnotes_xml_path),
            encoding='utf-8', xml_declaration=True, standalone=True
        )
        logger.info(f"Created footnotes.xml with {len(citation_first_occurrence)} footnotes")

        update_document_rels(temp_path, nsmap)
        ensure_footnote_styles(temp_path, nsmap)

        # Replace superscript numbers: first → footnoteReference, subsequent → NOTEREF
        footnote_count = noteref_count = 0
        for num, occurrences in citation_all_occurrences.items():
            for idx, (para, run) in enumerate(occurrences):
                parent = run.getparent()
                if idx == 0:
                    parent.replace(run, _footnote_ref_run(num, nsmap))
                    footnote_count += 1
                else:
                    parent.replace(run, _noteref_field(num, nsmap))
                    noteref_count += 1

        logger.info(f"Created {footnote_count} footnote references, {noteref_count} NOTEREF cross-references")

        tree.write(str(doc_xml_path), encoding='utf-8', xml_declaration=True, standalone=True)
        update_content_types(temp_path, nsmap)

        with ZipFile(output_path, 'w') as zout:
            for fp in temp_path.rglob('*'):
                if fp.is_file():
                    zout.write(fp, fp.relative_to(temp_path))

        shutil.rmtree(temp_dir)
        logger.info(f"Document saved: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error processing Word document: {e}")
        import traceback
        traceback.print_exc()
        return False


def _create_footnotes(citation_numbers, citation_db: dict, nsmap):
    """Create footnotes.xml with bookmarks; footnote content from citation_db."""
    footnotes = etree.Element(
        qn('w:footnotes'),
        nsmap={'w': nsmap['w'], 'r': nsmap['r']}
    )

    # Separator footnotes (required by Word)
    for fn_type, fn_id, fn_tag in [
        ('separator', '-1', qn('w:separator')),
        ('continuationSeparator', '0', qn('w:continuationSeparator')),
    ]:
        fn = etree.SubElement(footnotes, qn('w:footnote'))
        fn.set(qn('w:type'), fn_type)
        fn.set(qn('w:id'), fn_id)
        p = etree.SubElement(fn, qn('w:p'))
        r = etree.SubElement(p, qn('w:r'))
        etree.SubElement(r, fn_tag)

    for num in sorted(citation_numbers):
        footnote = etree.SubElement(footnotes, qn('w:footnote'))
        footnote.set(qn('w:id'), str(num))

        p = etree.SubElement(footnote, qn('w:p'))

        # Paragraph style → FootnoteText (smaller font, compact spacing)
        pPr = etree.SubElement(p, qn('w:pPr'))
        etree.SubElement(pPr, qn('w:pStyle'), {qn('w:val'): 'FootnoteText'})
        sp = etree.SubElement(pPr, qn('w:spacing'))
        sp.set(qn('w:before'), '0')
        sp.set(qn('w:after'), '0')
        sp.set(qn('w:line'), '200')
        sp.set(qn('w:lineRule'), 'exact')

        # Bookmark (needed for NOTEREF references)
        bk_start = etree.SubElement(p, qn('w:bookmarkStart'))
        bk_start.set(qn('w:id'), str(num + 10000))
        bk_start.set(qn('w:name'), f'_Ref_Footnote_{num}')

        # Superscript footnote number marker
        r1 = etree.SubElement(p, qn('w:r'))
        rPr1 = etree.SubElement(r1, qn('w:rPr'))
        etree.SubElement(rPr1, qn('w:rStyle'), {qn('w:val'): 'FootnoteReference'})
        va1 = etree.SubElement(rPr1, qn('w:vertAlign'))
        va1.set(qn('w:val'), 'superscript')
        etree.SubElement(r1, qn('w:footnoteRef'))

        # Footnote body text (explicit sz as fallback if style missing)
        r2 = etree.SubElement(p, qn('w:r'))
        rPr2 = etree.SubElement(r2, qn('w:rPr'))
        etree.SubElement(rPr2, qn('w:sz'), {qn('w:val'): '18'})
        etree.SubElement(rPr2, qn('w:szCs'), {qn('w:val'): '18'})
        t2 = etree.SubElement(r2, qn('w:t'))
        t2.set(qn('xml:space'), 'preserve')
        info = citation_db.get(num, {})
        site = info.get('page', {}).get('site_name', '')
        url = info.get('url', '')
        if site and url:
            t2.text = f' {site}. {url}'
        elif url:
            t2.text = f' {url}'
        else:
            t2.text = ''

        bk_end = etree.SubElement(p, qn('w:bookmarkEnd'))
        bk_end.set(qn('w:id'), str(num + 10000))

    return footnotes


def _footnote_ref_run(num, nsmap):
    """First occurrence: create footnoteReference run."""
    run = etree.Element(qn('w:r'))
    rPr = etree.SubElement(run, qn('w:rPr'))
    va = etree.SubElement(rPr, qn('w:vertAlign'))
    va.set(qn('w:val'), 'superscript')
    ref = etree.SubElement(run, qn('w:footnoteReference'))
    ref.set(qn('w:id'), str(num))
    return run


def _noteref_field(num, nsmap):
    """Subsequent occurrences: create NOTEREF field (\\h \\f switches)."""
    fld = etree.Element(qn('w:fldSimple'))
    fld.set(qn('w:instr'), f'NOTEREF _Ref_Footnote_{num} \\h \\f')
    run = etree.SubElement(fld, qn('w:r'))
    rPr = etree.SubElement(run, qn('w:rPr'))
    va = etree.SubElement(rPr, qn('w:vertAlign'))
    va.set(qn('w:val'), 'superscript')
    t = etree.SubElement(run, qn('w:t'))
    t.text = str(num)
    return fld
