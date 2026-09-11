"""Typography layer: font registry, measured text blocks, and vertical justification.

Everything a page draws goes through here so that hierarchy, leading and optical
spacing stay consistent across every design.
"""
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from app_paths import ROOT

FONT_DIR = ROOT / 'assets/fonts'

# Logical face name -> bundled file.
# 나눔글꼴(NAVER, SIL Open Font License 1.1)에서 한글·라틴만 남겨 가볍게 만든
# 판본이며, OFL의 예약 글꼴 이름 규정에 따라 이름을 바꾸어 수록했습니다.
# 다시 만들려면 build_fonts.py 를 참고하세요.
FACES = {
    'Serif':          'BulletinMyeongjo-Regular.ttf',
    'SerifBold':      'BulletinMyeongjo-Bold.ttf',
    'SerifBlack':     'BulletinMyeongjo-ExtraBold.ttf',
    'Sans':           'BulletinGothic-Regular.ttf',
    'SansLight':      'BulletinGothic-Light.ttf',
    'SansBold':       'BulletinGothic-Bold.ttf',
    'Square':         'BulletinSquare-Regular.ttf',
    'SquareBold':     'BulletinSquare-Bold.ttf',
    'SquareBlack':    'BulletinSquare-ExtraBold.ttf',
    'Gothic':         'BulletinClassic-Regular.ttf',
    'GothicBold':     'BulletinClassic-Bold.ttf',
}

# Body font families the user can pick in 디자인 · 용지.
BODY_FONTS = {
    'barun':    ('고딕 · 단정하고 읽기 편한 본문', 'SansLight', 'Sans', 'SansBold'),
    'gothic':   ('진한 고딕 · 어르신도 잘 보이는 본문', 'Gothic', 'Gothic', 'GothicBold'),
    'myeongjo': ('명조 · 책처럼 차분한 본문', 'Serif', 'Serif', 'SerifBold'),
    'square':   ('각진 고딕 · 또렷하고 현대적인 본문', 'Square', 'Square', 'SquareBold'),
}
HEAD_FONTS = {
    'myeongjo': ('명조 제목 · 기품 있는', 'Serif', 'SerifBold', 'SerifBlack'),
    'barun':    ('고딕 제목 · 담백한', 'Sans', 'SansBold', 'SansBold'),
    'square':   ('각진 제목 · 현대적인', 'Square', 'SquareBold', 'SquareBlack'),
}

# Legacy names used by earlier editions of the program.
ALIASES = {'Body': 'Sans', 'Title': 'Serif'}

_READY = False


def init_fonts():
    """Register every bundled face once. Raises only if the assets are missing."""
    global _READY
    if _READY:
        return
    missing = []
    for name, filename in FACES.items():
        if name in pdfmetrics.getRegisteredFontNames():
            continue
        path = Path(os.getenv('BULLETIN_FONT_DIR', str(FONT_DIR))) / filename
        if not path.exists():
            missing.append(filename)
            continue
        pdfmetrics.registerFont(TTFont(name, str(path)))
    if missing:
        raise ValueError('글꼴 파일이 없습니다: ' + ', '.join(missing) + ' · assets/fonts 폴더를 확인해 주세요.')
    for alias, target in ALIASES.items():
        if alias not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(alias, str(FONT_DIR / FACES[target])))
    for family, regular, bold in (('Serif', 'Serif', 'SerifBold'), ('Sans', 'Sans', 'SansBold'),
                                  ('Square', 'Square', 'SquareBold'), ('Gothic', 'Gothic', 'GothicBold')):
        pdfmetrics.registerFontFamily(family, normal=regular, bold=bold, italic=regular, boldItalic=bold)
    _READY = True


def width_of(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)


def fit_size(text, font, size, available, minimum=None):
    """Largest size at or below `size` that keeps one line inside `available`."""
    if not text:
        return size
    floor = minimum if minimum is not None else size * 0.62
    while size > floor and width_of(text, font, size) > available:
        size -= 0.25
    return size


def tracked(canvas, text, x, y, font, size, tracking=0.0, color=None, align='left', width=None):
    """Draw one line with optional letter spacing. Returns the drawn width."""
    if not text:
        return 0
    total = width_of(text, font, size) + tracking * max(0, len(text) - 1)
    if align == 'center' and width is not None:
        x = x + (width - total) / 2
    elif align == 'right' and width is not None:
        x = x + width - total
    if color is not None:
        canvas.setFillColor(color)
    canvas.setFont(font, size)
    if not tracking:
        canvas.drawString(x, y, text)
        return total
    canvas.saveState()
    text_object = canvas.beginText(x, y)
    text_object.setFont(font, size)
    text_object.setCharSpace(tracking)
    text_object.textOut(text)
    canvas.drawText(text_object)
    canvas.restoreState()
    return total


def style(font, size, leading=None, color=None, align=0, tracking=0.0, space_after=0):
    return ParagraphStyle(
        'block', fontName=font, fontSize=size,
        leading=leading if leading else round(size * 1.62, 2),
        textColor=color, alignment=align, wordWrap='CJK',
        splitLongWords=True, spaceAfter=space_after,
        allowWidows=0, allowOrphans=0,
    )


def markup(text):
    return escape(text).replace('\n', '<br/>')


def paragraph(text, width, font, size, leading=None, color=None, align=0):
    """Build a wrapped paragraph and report its height."""
    p = Paragraph(markup(text), style(font, size, leading, color, align))
    _, height = p.wrap(width, 100000)
    return p, height


class Stack:
    """Vertical block layout with justification.

    Blocks are measured first, then leftover space is distributed to the gaps
    that declare flex. Sparse bulletins fill the page instead of leaving the
    lower half empty, and dense ones simply tighten to their natural spacing.
    """

    def __init__(self, canvas, x, top, bottom, width):
        self.c = canvas
        self.x = x
        self.top = top          # y of the first baseline area (higher value)
        self.bottom = bottom    # lowest y content may reach
        self.width = width
        self.items = []         # (kind, payload)

    # -- composition -------------------------------------------------
    def gap(self, size, flex=0.0, cap=None):
        self.items.append(('gap', {'size': size, 'flex': flex, 'cap': cap}))
        return self

    def block(self, draw, height):
        """draw(canvas, x, top_y, width) renders inside `height` measured downward."""
        self.items.append(('block', {'draw': draw, 'height': height}))
        return self

    def para(self, text, font, size, leading=None, color=None, align=0, shrink_to=None):
        if not text or not text.strip():
            return self
        lead = leading if leading else round(size * 1.62, 2)
        p, height = paragraph(text, self.width, font, size, lead, color, align)
        self.items.append(('para', {'p': p, 'height': height, 'text': text, 'font': font,
                                    'size': size, 'lead_ratio': lead / size, 'color': color,
                                    'align': align, 'shrink_to': shrink_to}))
        return self

    def line(self, text, font, size, color=None, align='left', tracking=0.0, fit=True):
        if not text or not text.strip():
            return self
        text = ' '.join(text.split())
        drawn = fit_size(text, font, size, self.width) if fit else size
        height = drawn * 1.35

        def draw(c, x, top, width, _t=text, _f=font, _s=drawn, _col=color, _a=align, _tr=tracking):
            tracked(c, _t, x, top - _s * 1.0, _f, _s, _tr, _col, _a, width)
        self.items.append(('block', {'draw': draw, 'height': height}))
        return self

    def rule(self, width=None, thickness=0.6, color=None, align='left', pad=0):
        length = width if width is not None else self.width

        def draw(c, x, top, box, _l=length, _t=thickness, _c=color, _a=align):
            if _c is not None:
                c.setStrokeColor(_c)
            c.setLineWidth(_t)
            start = x if _a == 'left' else x + (box - _l) / 2 if _a == 'center' else x + box - _l
            c.line(start, top - _t, start + _l, top - _t)
        self.items.append(('block', {'draw': draw, 'height': thickness + pad}))
        return self

    # -- measurement and drawing -------------------------------------
    def natural_height(self):
        return sum(item[1]['height'] if item[0] != 'gap' else item[1]['size'] for item in self.items)

    def _shrink_paragraphs(self, overflow):
        """Reduce paragraph sizes (in declared priority order) to recover space."""
        for item in self.items:
            if overflow <= 0:
                break
            if item[0] != 'para':
                continue
            data = item[1]
            floor = data.get('shrink_to')
            if not floor:
                continue
            size = data['size']
            while size > floor and overflow > 0:
                size = round(size - 0.25, 2)
                p, height = paragraph(data['text'], self.width, data['font'], size,
                                      round(size * data['lead_ratio'], 2), data['color'], data['align'])
                overflow -= data['height'] - height
                data.update(p=p, height=height, size=size)
        return overflow

    def draw(self, justify=True, balance=None):
        """Render the stack.

        `balance` decides what happens to space that the capped flexible gaps
        could not absorb: 0 keeps it at the bottom, 0.5 centres the block, and
        0.38 sits it slightly above centre, which reads best on a printed page.
        """
        available = self.top - self.bottom
        natural = self.natural_height()
        overflow = natural - available
        if overflow > 0:
            overflow = self._shrink_paragraphs(overflow)
            natural = self.natural_height()
        slack = available - natural
        flex_total = sum(item[1]['flex'] for item in self.items if item[0] == 'gap')
        shares = {}
        if justify and slack > 0 and flex_total:
            pool = slack
            weights = {id(item[1]): item[1]['flex'] for item in self.items
                       if item[0] == 'gap' and item[1]['flex']}
            # Two passes so capped gaps hand their surplus to the uncapped ones.
            for _ in range(2):
                total = sum(weights.values())
                if not total or pool <= 0:
                    break
                spent = 0
                for item in self.items:
                    if item[0] != 'gap' or not item[1]['flex']:
                        continue
                    key = id(item[1])
                    if key not in weights:
                        continue
                    extra = pool * weights[key] / total
                    if item[1]['cap'] is not None and extra > item[1]['cap'] - shares.get(key, 0):
                        extra = max(0, item[1]['cap'] - shares.get(key, 0))
                        weights.pop(key, None)
                    shares[key] = shares.get(key, 0) + extra
                    spent += extra
                pool -= spent
            slack = max(0, pool)
        else:
            slack = max(0, slack)
        y = self.top
        if balance and slack > 0:
            y -= slack * balance
        for kind, data in self.items:
            if kind == 'gap':
                y -= data['size'] + shares.get(id(data), 0)
            elif kind == 'para':
                data['p'].drawOn(self.c, self.x, y - data['height'])
                y -= data['height']
            else:
                data['draw'](self.c, self.x, y, self.width)
                y -= data['height']
        return y
