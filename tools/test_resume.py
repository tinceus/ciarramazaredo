#!/usr/bin/env python3
"""Parse test for the plain (ATS) résumé. Exit 1 on any failure.
Usage: python3 tools/test_resume.py"""
import os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'assets/Ciarra_Mazaredo_Resume_ATS.pdf')
DOCX = os.path.join(ROOT, 'assets/Ciarra_Mazaredo_Resume_ATS.docx')
HEADINGS = ['SUMMARY', 'CORE SKILLS', 'PROFESSIONAL EXPERIENCE', 'EDUCATION', 'LEADERSHIP AND AWARDS']
fails = []

def check_text(label, text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or lines[0] != 'Ciarra Amor G. Mazaredo':
        fails.append(f'{label}: first line is {lines[:1]}, expected the full name')
    for needle in ['ciarramazaredo@gmail.com', '+63 956 623 8024', 'Chief of Staff', 'Executive Assistant to CEO', 'Operations Manager', 'Marketing Operations Specialist', 'AI Automation Specialist']:
        if needle not in text:
            fails.append(f'{label}: missing "{needle}"')
    pos = [text.upper().find(h) for h in HEADINGS]
    if -1 in pos or pos != sorted(pos):
        fails.append(f'{label}: headings missing or out of order {dict(zip(HEADINGS, pos))}')
    for bad in ['—', '–', '[CONFIRM', '83.57%', '#1 category', 'Available immediately']:
        if bad in text:
            fails.append(f'{label}: contains {bad!r}')

pdf_text = subprocess.run(['pdftotext', PDF, '-'], capture_output=True, text=True, check=True).stdout
check_text('pdf', pdf_text)
fonts = subprocess.run(['pdffonts', PDF], capture_output=True, text=True, check=True).stdout
if 'Type 3' in fonts:
    fails.append('pdf: uses Type 3 fonts')
pages = re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', PDF], capture_output=True, text=True).stdout)
if not pages or int(pages.group(1)) > 3:
    fails.append(f'pdf: page count {pages and pages.group(1)}')

with zipfile.ZipFile(DOCX) as archive:
    root = ET.fromstring(archive.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    docx_text = '\n'.join(''.join(p.itertext()) for p in root.findall('.//w:p', ns))
check_text('docx', docx_text)

if fails:
    print('\n'.join(fails)); sys.exit(1)
print(f'resume parse test: PASS (pdf {pages.group(1)} pages)')
