#!/usr/bin/env python3
"""Copy gate for the shipped pages. Exit 1 on any hard failure.

Hard checks: em/en dashes, sentence-ending ? or ! outside quotes, banned words and
phrases, sentences over 18 words, H1/H2 outside 4 to 7 words.
Grade: Flesch-Kincaid for the whole site and for each page. A page with ten or more
full sentences fails above grade 9. Shorter pages are reported, not failed.
Pages come from tools/build_site.py, so a new page is checked without editing this file.
Usage: python3 tools/copy_gate.py
"""
import html, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site  # noqa: E402

PAGES = [p['file'] for p in build_site.all_pages(build_site.stories())]
MAX_GRADE, MIN_SENTENCES = 9, 10
# Story titles kept at three words by choice (plan task 3.5). Exempt by exact text only.
SHORT_TITLES = {'The Onboarding Manual', 'The $86B Validation'}
DATA = 'assets/case-studies.js'
BANNED = [
    'leverage', 'delve', 'unlock', 'elevate', r'optimi[sz]e', 'transformative', 'innovative',
    'groundbreaking', 'holistic', 'disruptive', 'revolutionary', 'game-changing', 'seamless',
    'cutting-edge', 'empower', 'synergy', 'trusted partner', 'navigate the complexities',
    'more than just', 'at the intersection of', "here's the thing", 'the truth is',
    'let that sink in', "in today's", 'in an era of', 'it is important to note', 'worth mentioning',
    'very', 'really', 'basically', 'literally', 'landscape', 'realm', 'tapestry', 'beacon', 'vibrant',
    'usually', 'typically', 'often', 'significantly', 'effectively', 'highly',
]
MAX_WORDS = 18


class Visible(HTMLParser):
    """Collect visible text; quoted text (blockquote) is collected separately."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.quote = 0
        self.stack = []
        self.text, self.quotes, self.heads = [], [], []
        self._head = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'svg', 'title'):
            self.skip += 1
        if tag == 'blockquote':
            self.quote += 1
        if tag in ('h1', 'h2'):
            self._head = [tag, '']
        if tag in ('p', 'li', 'div', 'h1', 'h2', 'h3', 'h4', 'br', 'section', 'span', 'a', 'figcaption'):
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'svg', 'title'):
            self.skip -= 1
        if tag == 'blockquote':
            self.quote -= 1
        if tag in ('h1', 'h2') and self._head:
            self.heads.append((self._head[0], self._head[1].strip()))
            self._head = None
        if tag in ('p', 'li', 'div', 'h1', 'h2', 'h3', 'h4', 'figcaption'):
            self.text.append('\n')

    def handle_data(self, data):
        if self.skip:
            return
        if self._head is not None:
            self._head[1] += data
        (self.quotes if self.quote else self.text).append(data)


def sentences(block):
    for line in block.split('\n'):
        line = ' '.join(line.split())
        if not line:
            continue
        for s in re.split(r'(?<=[.?!])\s+(?=[A-Z0-9<"$#₱])', line):
            if s.strip():
                yield s.strip()


def syllables(word):
    word = word.lower()
    groups = re.findall(r'[aeiouy]+', word)
    n = len(groups)
    if word.endswith('e') and n > 1 and not word.endswith('le'):
        n -= 1
    return max(1, n)


def data_strings(js):
    """Prose fields from the case-studies data, minus quotes, ids and authors."""
    out = []
    for key, val in re.findall(r'\b(\w+):\s*"((?:[^"\\]|\\.)*)"', js):
        if key in ('about', 'problem', 'move', 'result', 'title', 'headlineLabel', 'clientType', 'coverTagline', 'label'):
            out.append(re.sub(r'<[^>]+>', '', html.unescape(val)))
    return out


def fk_grade(sents):
    words = [w for s in sents for w in re.findall(r"[A-Za-z][A-Za-z'-]*", s)]
    if not words:
        return None
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / len(sents) + 11.8 * syl / len(words) - 15.59


def main():
    fails = []
    body_text = []
    per_page = {}
    for name in PAGES + [DATA]:
        raw = open(os.path.join(ROOT, name), encoding='utf-8').read()
        for i, line in enumerate(raw.split('\n'), 1):
            if '—' in line or '–' in line:
                fails.append(f'{name}:{i}: dash used: {line.strip()[:90]}')
        if name == DATA:
            prose = data_strings(raw)
        else:
            v = Visible()
            v.feed(raw)
            prose = [''.join(v.text)]
            for tag, h in v.heads:
                n = len(h.split())
                if n and not 4 <= n <= 7 and h not in SHORT_TITLES:   # empty = filled by script at runtime
                    fails.append(f'{name}: {tag} has {n} words (4 to 7): "{h}"')
        for block in prose:
            for s in sentences(block):
                words = s.split()
                if re.search(r'[?!]$', s):
                    fails.append(f'{name}: sentence ends with ?/!: "{s[:90]}"')
                if len(words) > MAX_WORDS and re.search(r'[a-z]', s) and s.endswith('.'):
                    fails.append(f'{name}: {len(words)} words: "{s[:110]}"')
                low = s.lower()
                for b in BANNED:
                    if re.search(r'\b' + b + r'\b', low):
                        fails.append(f'{name}: banned "{b}": "{s[:90]}"')
                if s.endswith('.') and len(words) >= 6:
                    body_text.append(s)
                    per_page.setdefault(name, []).append(s)
    # Flesch-Kincaid grade over full sentences of prose (report only)
    words = [w for s in body_text for w in re.findall(r"[A-Za-z][A-Za-z'-]*", s)]
    if words and body_text:
        syl = sum(syllables(w) for w in words)
        grade = 0.39 * len(words) / len(body_text) + 11.8 * syl / len(words) - 15.59
        print(f'Flesch-Kincaid grade (prose sentences): {grade:.1f}  [{len(body_text)} sentences, {len(words)} words]')
    for name in PAGES:
        sents = per_page.get(name, [])
        g = fk_grade(sents) if sents else None
        if g is None:
            print(f'  {name}: no full sentences')
            continue
        flag = ''
        if g > MAX_GRADE and len(sents) >= MIN_SENTENCES:
            fails.append(f'{name}: grade {g:.1f} is above {MAX_GRADE} ({len(sents)} sentences)')
            flag = '  FAIL'
        elif g > MAX_GRADE:
            flag = '  (above 9, under ten sentences: reported only)'
        print(f'  {name}: grade {g:.1f} [{len(sents)} sentences]{flag}')
    if fails:
        print(f'\n{len(fails)} problem(s):')
        for f in fails:
            print('  ' + f)
        sys.exit(1)
    print('copy gate: PASS')


if __name__ == '__main__':
    main()
