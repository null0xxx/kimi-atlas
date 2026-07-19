#!/usr/bin/env python3
"""
Word document post-processing module: hyperlink cross-references (WPS-compatible)
Simplified: direct run replacement, no delete-and-rebuild
"""
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re
import logging

logger = logging.getLogger(__name__)


def create_fld_simple_ref(bookmark_name, text):
    """Create REF field cross-reference."""
    fld_simple = OxmlElement('w:fldSimple')
    fld_simple.set(qn('w:instr'), f'REF {bookmark_name} \\h')

    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    vertAlign = OxmlElement('w:vertAlign')
    vertAlign.set(qn('w:val'), 'superscript')
    rPr.append(vertAlign)
    run.append(rPr)

    t = OxmlElement('w:t')
    t.text = text
    run.append(t)

    fld_simple.append(run)
    return fld_simple


def process_word_document_with_hyperlinks(docx_path: str, output_path: str = None, citation_db: dict = None) -> bool:
    """
    Process Word document using cross-references for citation navigation.

    Strategy:
    1. If document already has a References section (from original MD), add bookmarks to it
    2. If no References section, generate one from citation_db and append to document
    3. Replace body superscript numbers with fldSimple cross-references
    """
    if output_path is None:
        output_path = docx_path
    if citation_db is None:
        citation_db = {}

    try:
        doc = Document(docx_path)

        # Step 1: Check for existing References section
        in_references = False
        has_references = False
        reference_pattern = re.compile(r'^\[(\d+)\]\s+')
        bookmark_id = 1
        existing_ref_nums = set()

        for para in doc.paragraphs:
            if para.text.strip() in ('References', 'Bibliography', 'Works Cited'):
                in_references = True
                has_references = True
                logger.info("Found existing References section")
                continue

            if in_references:
                match = reference_pattern.match(para.text.strip())
                if match:
                    ref_num = match.group(1)
                    existing_ref_nums.add(int(ref_num))
                    bookmark_name = f'Note_{ref_num}'

                    p_element = para._element
                    bookmark_start = OxmlElement('w:bookmarkStart')
                    bookmark_start.set(qn('w:id'), str(bookmark_id))
                    bookmark_start.set(qn('w:name'), bookmark_name)

                    bookmark_end = OxmlElement('w:bookmarkEnd')
                    bookmark_end.set(qn('w:id'), str(bookmark_id))

                    p_element.insert(0, bookmark_start)
                    p_element.append(bookmark_end)
                    bookmark_id += 1

        # If no References section, generate from citation_db
        if not has_references and citation_db:
            logger.info(f"No References section found, generating from citation_db ({len(citation_db)} entries)")
            # Add "References" heading
            heading_para = doc.add_paragraph('References', style='Heading 2')
            # Add each citation sorted by display_num
            for num in sorted(citation_db.keys()):
                info = citation_db[num]
                site = info.get('page', {}).get('site_name', '')
                url = info.get('url', '')
                if site and url:
                    ref_text = f'[{num}] {site}. {url}'
                elif url:
                    ref_text = f'[{num}] {url}'
                else:
                    ref_text = f'[{num}]'

                ref_para = doc.add_paragraph(ref_text)
                # Add bookmark
                p_element = ref_para._element
                bookmark_name = f'Note_{num}'
                bookmark_start = OxmlElement('w:bookmarkStart')
                bookmark_start.set(qn('w:id'), str(bookmark_id))
                bookmark_start.set(qn('w:name'), bookmark_name)
                bookmark_end = OxmlElement('w:bookmarkEnd')
                bookmark_end.set(qn('w:id'), str(bookmark_id))
                p_element.insert(0, bookmark_start)
                p_element.append(bookmark_end)
                bookmark_id += 1
            logger.info(f"Generated {len(citation_db)} reference entries with bookmarks")

        # Step 2: Process body superscript citations
        crossref_count = 0

        for para in doc.paragraphs:
            if para.text.strip() in ('References', 'Bibliography', 'Works Cited'):
                break

            p_element = para._element

            # Collect consecutive superscript numbers
            citation_groups = []
            current_group = []

            for run in para.runs:
                if run.font.superscript and run.text.strip():
                    text = run.text.strip()
                    if re.match(r'^\d+$', text):
                        current_group.append((run, text))
                    else:
                        # Non-numeric superscript, end current group
                        if current_group:
                            citation_groups.append(current_group)
                            current_group = []
                else:
                    # Non-superscript, end current group
                    if current_group:
                        citation_groups.append(current_group)
                        current_group = []

            if current_group:
                citation_groups.append(current_group)

            # Process each citation group
            for group in citation_groups:
                if not group:
                    continue

                # Single citation: direct replacement
                if len(group) == 1:
                    run, text = group[0]
                    bookmark_name = f'Note_{text}'
                    fld_simple = create_fld_simple_ref(bookmark_name, text)
                    run_element = run._element
                    parent = run_element.getparent()
                    parent.replace(run_element, fld_simple)
                    crossref_count += 1
                else:
                    # Multiple citations: replace with fld,fld,fld format
                    first_run = group[0][0]
                    first_run_element = first_run._element
                    parent = first_run_element.getparent()

                    # Find position of first run
                    insert_pos = None
                    for idx, elem in enumerate(parent):
                        if elem is first_run_element:
                            insert_pos = idx
                            break

                    if insert_pos is None:
                        continue

                    # Remove all runs
                    for run, _ in group:
                        parent.remove(run._element)

                    # Insert new fldSimple elements and commas
                    offset = 0
                    for i, (_, text) in enumerate(group):
                        bookmark_name = f'Note_{text}'
                        fld_simple = create_fld_simple_ref(bookmark_name, text)
                        parent.insert(insert_pos + offset, fld_simple)
                        offset += 1
                        crossref_count += 1

                        # Add comma (except after last)
                        if i < len(group) - 1:
                            comma_run = OxmlElement('w:r')
                            rPr = OxmlElement('w:rPr')
                            vertAlign = OxmlElement('w:vertAlign')
                            vertAlign.set(qn('w:val'), 'superscript')
                            rPr.append(vertAlign)
                            comma_run.append(rPr)
                            t = OxmlElement('w:t')
                            t.text = ','
                            comma_run.append(t)
                            parent.insert(insert_pos + offset, comma_run)
                            offset += 1

        logger.info(f"Created {crossref_count} cross-references")

        # Save document
        doc.save(output_path)
        logger.info(f"Saved Word document with cross-references: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error processing Word document: {e}")
        import traceback
        traceback.print_exc()
        return False
