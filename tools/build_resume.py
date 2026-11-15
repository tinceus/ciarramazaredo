#!/usr/bin/env python3
"""Build the editable ATS résumé from the same HTML used for both PDFs.

Requires python-docx. Run tools/build_resume.js separately for PDFs (Playwright).
"""
from html.parser import HTMLParser
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]

class Blocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = None
        self.text = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag in ('h1', 'h2', 'h3', 'p', 'li'):
            self.active = tag
            self.text = []
        elif tag == 'br' and self.active:
            self.text.append('\n')

    def handle_data(self, data):
        if self.active:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == self.active:
            self.blocks.append((tag, ''.join(self.text).strip()))
            self.active = None

parser = Blocks()
parser.feed((ROOT / 'tools/resume/resume-ats.html').read_text())
doc = Document()
section = doc.sections[0]
section.top_margin = section.bottom_margin = Inches(.6)
section.left_margin = section.right_margin = Inches(.7)
style = doc.styles['Normal']
style.font.name = 'Arial'
style.font.size = Pt(10.5)
style.paragraph_format.space_after = Pt(4)
for tag, text in parser.blocks:
    if tag == 'h1':
        p = doc.add_paragraph(text)
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(18)
    elif tag in ('h2', 'h3'):
        doc.add_heading(text.upper() if tag == 'h2' else text, level=1 if tag == 'h2' else 2)
    else:
        doc.add_paragraph(text, style='List Bullet' if tag == 'li' else None)
doc.save(ROOT / 'assets/Ciarra_Mazaredo_Resume_ATS.docx')
print('Built editable résumé from shared source')
