"""The page engine.

One composition system draws every design. Panels are laid out on a real
grid, hierarchy comes from a fixed type scale, and vertical slack is
distributed so a short bulletin still fills the page instead of leaving the
lower half blank. Nothing here raises on long content: text is fitted, and
anything that had to be trimmed is reported back as a note.
"""
import base64
import math
import re
from datetime import date
from io import BytesIO

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter, Transformation

import ornaments
from designs import THEMES, resolve
from typography import (BODY_FONTS, HEAD_FONTS, Stack, fit_size, init_fonts,
                        paragraph, tracked, width_of)

FORMATS = {'a4-half': (297, 210, 2), 'a4-third': (297, 210, 3), 'a3-third': (420, 297, 3)}
DESIGNS = {key: theme.name for key, theme in THEMES.items()}

WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']


def credit():
    """PDF 속성에 남길 제작 프로그램 표시. 인쇄되는 지면에는 나오지 않습니다."""
    import json
    from app_paths import ROOT
    name, version, author = '카리스 주보제작', '2.0', ''
    try:
        info = json.loads((ROOT / 'distribution.json').read_text(encoding='utf-8'))
        name = info.get('project') or name
        version = info.get('version') or version
        author = info.get('author') or ''
    except Exception:
        pass
    return f'{name} {version}' + (f' · © {author}' if author else '')


def geometry(d):
    sheet_w, sheet_h, n = FORMATS[d['format']]
    widths = [sheet_w / n] * n
    if n == 3 and d['fold'] == 'roll':
        widths = [sheet_w / 3 - 2, sheet_w / 3 + 1, sheet_w / 3 + 1]
    return sheet_w * mm, sheet_h * mm, [v * mm for v in widths]


def panel_widths(d):
    _, _, ws = geometry(d)
    if len(ws) == 2:
        return [ws[0]] * 4
    # Outer sheet: flap 5, back 6, cover 1. Inner sheet is horizontally reversed.
    return [ws[2], ws[2], ws[1], ws[0], ws[0], ws[1]]


def korean_date(iso):
    try:
        dt = date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso, ''
    return f'{dt.year}년 {dt.month}월 {dt.day}일', WEEKDAYS[dt.weekday()] + '요일'


def issue_label(value):
    value = (value or '').strip()
    if not value:
        return ''
    return value if value.endswith('호') else f'제{value}호'


def tint(hexcolor, ratio, toward='#FFFFFF'):
    a, b = HexColor(hexcolor), HexColor(toward)
    return Color(a.red + (b.red - a.red) * ratio,
                 a.green + (b.green - a.green) * ratio,
                 a.blue + (b.blue - a.blue) * ratio)


def split_row(row):
    parts = row.split('|', 1) if '|' in row else row.split(None, 1)
    label = parts[0].strip()
    value = parts[1].strip() if len(parts) > 1 else ''
    return label, value


# --- 홈페이지 공개본에서 성도 이름 가리기 -----------------------------
# 직분이 붙은 이름만 「홍길동 집사 → 홍○○ 집사」로 바꿉니다.
# 교회 안에서 쓰는 인쇄용·읽기용 주보는 건드리지 않습니다.
TITLE_WORDS = ('목사', '전도사', '강도사', '집사', '권사', '장로', '성도',
               '형제', '자매', '선교사', '사모', '교사', '간사', '선생')
# 직분 뒤에 흔히 붙는 「님」과 조사. 「권사님의」, 「형제가」도 이름으로 봅니다.
TITLE_TAIL = r'(?:님)?(?:[이가은는을를의에도만과와로써랑께](?:서|게|는|도|만|의)?)?(?![가-힣])'
# 이름이 아니라 직분을 꾸미는 말들. 「담임목사」가 「담○사」가 되면 안 됩니다.
NOT_A_NAME = {
    # 직분을 꾸미는 말
    '담임', '원로', '협동', '선임', '수석', '시무', '은퇴', '서리', '안수', '전임',
    '파송', '후원', '초청', '신임', '신규', '임시', '명예', '공동', '담당', '지도',
    # 부서·소속을 가리키는 말
    '교회', '학교', '주일', '유년', '장년', '청년', '교육', '중등', '고등', '초등',
    '유치', '영아', '유아', '아동', '중고', '대학', '청소', '여성', '남성', '남녀',
    '부장', '부서', '소속', '본당', '전체', '각부', '구역',
    # 그 밖에 이름이 아닌 말
    '우리', '모든', '여러', '새신', '새가', '차기', '해당', '오늘', '이번', '다음',
    '지난', '올해', '내년', '작년', '함께', '앞서',
}
NAME_PATTERN = re.compile(
    r'(?<![가-힣])([가-힣]{2,3})(?=\s*(?:' + '|'.join(TITLE_WORDS) + r')' + TITLE_TAIL + r')')


def mask_names(text):
    if not text:
        return text

    def replace(match):
        name = match.group(1)
        if name in NOT_A_NAME or name[:2] in NOT_A_NAME:
            return name
        return name[0] + '○' * (len(name) - 1)
    return NAME_PATTERN.sub(replace, text)


MASKED_FIELDS = ('order', 'announcements', 'prayers', 'article_body',
                 'article_title', 'article_quote', 'service_note')


class Book:
    """Draws all panels of one bulletin onto a single reportlab canvas."""

    def __init__(self, d, public=False, notes=None):
        init_fonts()
        if public and (d.get('public_names') or 'mask') == 'mask':
            d = dict(d)
            for key in MASKED_FIELDS:
                d[key] = mask_names(d.get(key, ''))
        self.d = d
        self.public = public
        self.notes = notes if notes is not None else []
        self.theme = THEMES[resolve(d['design'])]
        self.widths = panel_widths(d)
        self.n = len(self.widths)
        _, self.h, _ = geometry(d)
        self.page_h = self.h
        self.shift = 0
        self.buffer = BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=(self.widths[0], self.h), pageCompression=1)
        self.c.setTitle(f'{d["church"]} {d["date"]} 주보')
        self.c.setAuthor(d['church'])
        self.c.setSubject(d['sermon'])
        self.c.setCreator(credit())

        body_key = d.get('body_font') or self.theme.body_hint or 'barun'
        if body_key not in BODY_FONTS:
            body_key = 'barun'
        head_key = d.get('head_font') or self.theme.head
        if head_key not in HEAD_FONTS:
            head_key = 'myeongjo'
        _, self.body_light, self.body, self.body_bold = BODY_FONTS[body_key]
        _, self.head, self.head_bold, self.head_black = HEAD_FONTS[head_key]

        self.ink = self.theme.color('ink')
        self.accent = self.theme.color('accent')
        self.muted = self.theme.color('muted')
        self.paper = self.theme.color('paper')
        self.soft = self.theme.color('soft')
        self.hairline = tint(self.theme.ink, 0.86)

        self.prayer = d['prayers'] if not public or d['public_prayers'] else ''
        self.email = d['email'] if not public or d['public_contacts'] else ''
        self.address = d['address'] if not public or d['public_contacts'] else ''

    # -- metrics -----------------------------------------------------
    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def open_panel(self, index):
        """Start a panel and return (width, margin_x, top_y, bottom_y)."""
        w = self.widths[index - 1]
        self.c.setPageSize((w, self.h))
        self.w = w
        self.ratio = math.sqrt(w / (148.5 * mm))
        self.mx = (10.5 if self.n == 6 else 15) * mm
        self.inner = w - 2 * self.mx
        return w

    def ds(self, size):
        """Display scale — headline sizes track the panel width."""
        return round(size * self.ratio, 2)

    def ts(self, size):
        """Text scale — body sizes shrink far more gently."""
        return round(size * (0.80 + 0.20 * self.ratio), 2)

    # -- shared chrome -----------------------------------------------
    # 표지에서 로고 자리를 비울 때 self.h 를 잠시 줄이고 화면을 위로 옮깁니다.
    # 바탕색과 테두리는 그래도 종이 전체를 덮어야 하므로 page_h · shift 로 보정합니다.
    page_h = None
    shift = 0

    def paint(self, color):
        self.c.setFillColor(color)
        self.c.rect(0, -self.shift, self.w, self.page_h or self.h, fill=1, stroke=0)

    def frame(self, color, inset=6.5, double=True):
        c = self.c
        page = self.page_h or self.h
        c.setStrokeColor(color)
        c.setLineWidth(0.9)
        c.rect(inset * mm, inset * mm - self.shift, self.w - 2 * inset * mm, page - 2 * inset * mm,
               fill=0, stroke=1)
        if double:
            c.setLineWidth(0.3)
            pad = (inset + 1.8) * mm
            c.rect(pad, pad - self.shift, self.w - 2 * pad, page - 2 * pad, fill=0, stroke=1)

    def eyebrow(self, text, y, color, align='center', size=None, tracking=None):
        if not text:
            return
        size = size or self.ds(7.2)
        tracking = tracking if tracking is not None else size * 0.34
        text = ' '.join(text.split())
        while (width_of(text, self.body, size) + tracking * len(text)) > self.inner and size > 5.4:
            size -= 0.2
            tracking = size * 0.28
        tracked(self.c, text, self.mx, y, self.body, size, tracking, color, align, self.inner)

    def logo_image(self):
        """(ImageReader, 원본 가로, 원본 세로) 또는 None."""
        raw = self.d.get('logo')
        if not raw or not raw.startswith('data:image/png;base64,'):
            return None
        try:
            image = ImageReader(BytesIO(base64.b64decode(raw.split(',', 1)[1])))
            iw, ih = image.getSize()
            return image, iw, ih
        except Exception:
            self.note('로고 이미지를 읽지 못했습니다. PNG 파일을 다시 등록해 주세요.')
            return None

    def logo_metrics(self, limit_width):
        """사용자가 지정한 높이(mm)를 지면 폭에 맞춰 실제 크기로 바꿉니다."""
        got = self.logo_image()
        if not got:
            return None
        image, iw, ih = got
        try:
            height_mm = float(self.d.get('logo_size') or 22)
        except (TypeError, ValueError):
            height_mm = 22
        height_mm = max(6, min(90, height_mm))
        h = height_mm * mm * self.ratio
        w = h * iw / ih
        if w > limit_width:
            w = limit_width
            h = w * ih / iw
        return image, w, h

    def logo_block(self):
        """세로 흐름 안에 넣는 로고. 위치가 '교회 이름 위'일 때만 씁니다."""
        if (self.d.get('logo_place') or 'above') != 'above':
            return None
        metrics = self.logo_metrics(self.inner)
        if not metrics:
            return None
        image, w, h = metrics

        def draw(c, x, top, box, _i=image, _w=w, _h=h):
            c.drawImage(_i, x + (box - _w) / 2, top - _h, width=_w, height=_h, mask='auto')
        return draw, h

    def logo_reserve(self):
        """맨 위·맨 아래에 놓을 때 표지 내용이 비켜 줄 높이."""
        if (self.d.get('logo_place') or 'above') not in ('top', 'bottom'):
            return 0
        metrics = self.logo_metrics(self.w - 8 * mm)
        return metrics[2] + 14 * mm if metrics else 0

    def place_logo(self):
        """표지 맨 위·맨 아래·직접 지정 위치에 로고를 얹습니다."""
        place = self.d.get('logo_place') or 'above'
        if place == 'above':
            return
        metrics = self.logo_metrics(self.w - 8 * mm)
        if not metrics:
            return
        image, w, h = metrics
        if place == 'top':
            x, y = (self.w - w) / 2, self.h - 11 * mm - h
        elif place == 'bottom':
            x, y = (self.w - w) / 2, 11 * mm
        else:
            try:
                across = float(self.d.get('logo_x') or 50)
            except (TypeError, ValueError):
                across = 50
            try:
                down = float(self.d.get('logo_y') or 30)
            except (TypeError, ValueError):
                down = 30
            x = (self.w - w) * max(0, min(100, across)) / 100
            y = self.h - max(0, down) * mm - h
            y = max(2 * mm, min(y, self.h - h - 2 * mm))
        self.c.drawImage(image, x, y, width=w, height=h, mask='auto')

    def content_box(self):
        """Top and bottom of the text column for an inner page, without drawing."""
        top = self.h - (35 * mm if not self.theme.inner_band else 26 * mm + 9 * mm)
        return top, 17 * mm

    def header(self, index, title, eyebrow_text):
        """Inner-page chrome. Returns (top_y, bottom_y) of the content column."""
        c = self.c
        theme = self.theme
        self.paint(self.paper)
        if theme.inner_band:
            band = 26 * mm
            c.setFillColor(self.ink)
            c.rect(0, self.h - band, self.w, band, fill=1, stroke=0)
            self.eyebrow(eyebrow_text, self.h - 10 * mm, tint(theme.accent, 0.25), align='left')
            size = fit_size(title, self.head_bold, self.ds(17), self.inner)
            tracked(c, title, self.mx, self.h - 20.5 * mm, self.head_bold, size, 0, HexColor('#FFFFFF'))
            top = self.h - band - 9 * mm
        else:
            c.setFillColor(self.accent)
            c.rect(self.mx, self.h - 10.6 * mm, self.inner * 0.13, 1.1 * mm, fill=1, stroke=0)
            self.eyebrow(eyebrow_text, self.h - 15.6 * mm, self.accent, align='left')
            size = fit_size(title, self.head_bold, self.ds(19), self.inner)
            tracked(c, title, self.mx, self.h - 24.5 * mm, self.head_bold, size, 0, self.ink)
            c.setStrokeColor(self.hairline)
            c.setLineWidth(0.5)
            c.line(self.mx, self.h - 28.5 * mm, self.w - self.mx, self.h - 28.5 * mm)
        self.footer(index)
        return self.content_box()

    def footer(self, index):
        c = self.c
        y = 10 * mm
        c.setStrokeColor(self.hairline)
        c.setLineWidth(0.4)
        c.line(self.mx, y + 4 * mm, self.w - self.mx, y + 4 * mm)
        size = self.ts(6.8)
        c.setFillColor(self.muted)
        c.setFont(self.body, size)
        c.drawString(self.mx, y, self.d['church'])
        stamp, _ = korean_date(self.d['date'])
        c.drawRightString(self.w - self.mx, y, f'{stamp}  ·  {index}')

    def stack(self, top, bottom):
        return Stack(self.c, self.mx, top, bottom, self.inner)

    # -- cover -------------------------------------------------------
    def cover(self):
        theme = self.theme
        self.open_panel(1)
        self.page_h = self.h
        self.shift = 0
        reserve = self.logo_reserve()
        place = self.d.get('logo_place') or 'above'
        if reserve and place == 'top':
            self.h -= reserve
        elif reserve and place == 'bottom':
            self.shift = reserve
            self.h -= reserve

        composition = getattr(self, 'cover_' + theme.cover, self.cover_light)
        self.c.saveState()
        if self.shift:
            self.c.translate(0, self.shift)
        composition()
        self.c.restoreState()

        self.h = self.page_h
        self.shift = 0
        self.place_logo()
        self.c.showPage()

    def cover_palette(self):
        return (self.theme.color('cover_paper'), self.theme.color('cover_ink'),
                self.theme.color('cover_accent'))

    def cover_common(self, paper, ink, accent, ornament_flex=1.0, show_frame=None):
        """Shared cover: eyebrow, ornament, identity block and a footer plate."""
        d = self.d
        self.paint(paper)
        if show_frame if show_frame is not None else self.theme.frame:
            self.frame(tint(self.theme.cover_accent, 0.35, self.theme.cover_paper))
        muted = tint(self.theme.cover_ink, 0.38, self.theme.cover_paper)
        top = self.h - 20 * mm
        bottom = 20 * mm

        self.eyebrow(d['denomination'] or '주일예배', self.h - 15.5 * mm, accent)
        stamp, weekday = korean_date(d['date'])

        s = self.stack(top, bottom)
        s.gap(2 * mm)
        s.rule(width=self.inner * 0.10, thickness=0.9, color=accent, align='center', pad=0)
        s.gap(4 * mm, flex=0.55)

        art = self.logo_block()
        if art:
            s.block(art[0], art[1])
            if self.theme.motif:
                s.gap(3 * mm)
        elif self.theme.motif:
            radius = min(self.inner * 0.30, self.h * 0.105)

            def draw(c, x, y, box, _r=radius):
                ornaments.draw(c, self.theme.motif, x + box / 2, y - _r, _r,
                               self.theme.cover_ink, self.theme.cover_accent, self.theme.cover_paper)
            s.block(draw, radius * 2)
        s.gap(7 * mm, flex=ornament_flex)

        s.line(d['church'], self.head_black, self.ds(27), ink, 'center')
        s.gap(3.4 * mm)
        s.rule(width=self.inner * 0.22, thickness=0.5, color=accent, align='center')
        s.gap(3.4 * mm)
        s.para(d['tagline'], self.head, self.ts(11), self.ts(11) * 1.72, muted, 1, shrink_to=self.ts(8.6))
        s.gap(6 * mm, flex=1.0)

        s.rule(thickness=0.5, color=tint(self.theme.cover_accent, 0.45, self.theme.cover_paper))
        s.gap(4.6 * mm)
        s.para(d['sermon'], self.head_bold, self.ds(14.5), self.ds(14.5) * 1.40, ink, 1, shrink_to=self.ds(10.5))
        s.gap(2.4 * mm)
        s.line(d['scripture'], self.body, self.ts(9), accent, 'center')
        s.gap(4.6 * mm)
        s.rule(thickness=0.5, color=tint(self.theme.cover_accent, 0.45, self.theme.cover_paper))
        s.gap(4.2 * mm, flex=0.35)

        meta = '  ·  '.join(x for x in (stamp, weekday, issue_label(d['issue'])) if x)
        s.line(meta, self.body, self.ts(8.6), muted, 'center')
        if d['service_time']:
            s.gap(2.2 * mm)
            s.line(d['service_time'], self.body, self.ts(8), muted, 'center')
        contact = '  ·  '.join(x for x in (self.address, self.email) if x)
        if contact:
            s.gap(2.6 * mm)
            s.para(contact, self.body, self.ts(7.4), self.ts(7.4) * 1.5, muted, 1, shrink_to=self.ts(6.4))
        s.draw()

    def cover_light(self):
        paper, ink, accent = self.cover_palette()
        self.cover_common(paper, ink, accent)

    def cover_frame(self):
        paper, ink, accent = self.cover_palette()
        self.cover_common(paper, ink, accent, ornament_flex=0.9)

    def cover_arch(self):
        d = self.d
        theme = self.theme
        paper, ink, accent = self.cover_palette()
        self.paint(paper)
        c = self.c
        c.setFillColor(tint(theme.cover_accent, 0.80, theme.cover_paper))
        c.rect(0, 0, self.w, 34 * mm, fill=1, stroke=0)
        muted = tint(theme.cover_ink, 0.38, theme.cover_paper)
        self.eyebrow(d['denomination'] or 'SUNDAY WORSHIP', self.h - 15 * mm, accent)
        c.setStrokeColor(tint(theme.cover_accent, 0.45, theme.cover_paper))
        c.setLineWidth(0.5)
        c.line(self.mx, self.h - 20 * mm, self.w - self.mx, self.h - 20 * mm)

        s = self.stack(self.h - 27 * mm, 42 * mm)
        s.gap(3 * mm, flex=0.4)
        art = self.logo_block()
        if art:
            s.block(*[art[0], art[1]])
        else:
            radius = min(self.inner * 0.28, self.h * 0.10)

            def draw(cv, x, y, box, _r=radius):
                ornaments.draw(cv, 'arch', x + box / 2, y - _r, _r,
                               theme.cover_ink, theme.cover_accent, theme.cover_paper)
            s.block(draw, radius * 2.1)
        s.gap(8 * mm, flex=0.9)
        s.line(d['church'], self.head_black, self.ds(26), ink, 'center')
        s.gap(3.2 * mm)
        s.para(d['tagline'], self.head, self.ts(10.6), self.ts(10.6) * 1.7, muted, 1, shrink_to=self.ts(8.4))
        s.gap(6 * mm, flex=1.0)
        s.rule(width=self.inner * 0.16, thickness=0.8, color=accent, align='center')
        s.gap(5 * mm)
        s.para(d['sermon'], self.head_bold, self.ds(14), self.ds(14) * 1.4, ink, 1, shrink_to=self.ds(10.5))
        s.gap(2.4 * mm)
        s.line(d['scripture'], self.body, self.ts(9), accent, 'center')
        s.draw()

        stamp, weekday = korean_date(d['date'])
        meta = '  ·  '.join(x for x in (stamp, weekday, issue_label(d['issue'])) if x)
        base = self.stack(30 * mm, 9 * mm)
        base.line(meta, self.body_bold, self.ts(8.8), ink, 'center')
        if d['service_time']:
            base.gap(2.4 * mm)
            base.line(d['service_time'], self.body, self.ts(8), muted, 'center')
        contact = '  ·  '.join(x for x in (self.address, self.email) if x)
        if contact:
            base.gap(2.4 * mm)
            base.para(contact, self.body, self.ts(7.4), self.ts(7.4) * 1.5, muted, 1, shrink_to=self.ts(6.4))
        base.draw(justify=False)

    def cover_bigdate(self):
        d = self.d
        theme = self.theme
        paper, ink, accent = self.cover_palette()
        self.paint(paper)
        c = self.c
        muted = tint(theme.cover_ink, 0.42, theme.cover_paper)
        self.eyebrow(d['denomination'] or 'SUNDAY BULLETIN', self.h - 14 * mm, accent, align='left')
        stamp, weekday = korean_date(d['date'])
        c.setStrokeColor(accent)
        c.setLineWidth(0.9)
        c.line(self.mx, self.h - 19 * mm, self.w - self.mx, self.h - 19 * mm)

        big = self.ds(62)
        month, day = d['date'][5:7], d['date'][8:10]
        c.setFillColor(ink)
        c.setFont(self.head_black, big)
        c.drawString(self.mx, self.h - 19 * mm - big * 0.92, month)
        month_w = width_of(month, self.head_black, big)
        c.setFillColor(accent)
        c.drawString(self.mx + month_w + big * 0.10, self.h - 19 * mm - big * 0.92 - big * 0.62, day)
        c.setFillColor(muted)
        c.setFont(self.body, self.ts(8.4))
        c.drawRightString(self.w - self.mx, self.h - 19 * mm - big * 0.55, weekday)
        c.drawRightString(self.w - self.mx, self.h - 19 * mm - big * 0.55 - self.ts(12),
                          issue_label(d['issue']))
        top = self.h - 19 * mm - big * 1.72

        s = self.stack(top, 20 * mm)
        art = self.logo_block()
        if art:
            s.gap(2 * mm)
            s.block(art[0], art[1])
            s.gap(4 * mm)
        s.gap(2 * mm, flex=0.55)
        s.line(d['church'], self.head_black, self.ds(26), ink, 'left')
        s.gap(3.4 * mm)
        s.para(d['tagline'], self.head, self.ts(10.6), self.ts(10.6) * 1.72, muted, 0, shrink_to=self.ts(8.4))
        s.gap(6 * mm, flex=1.0)
        s.rule(width=self.inner * 0.20, thickness=1.4, color=accent)
        s.gap(5 * mm)
        s.para(d['sermon'], self.head_bold, self.ds(15), self.ds(15) * 1.38, ink, 0, shrink_to=self.ds(11))
        s.gap(2.6 * mm)
        s.line(d['scripture'], self.body, self.ts(9), accent, 'left')
        s.gap(5 * mm, flex=0.5)
        if d['service_time']:
            s.line(d['service_time'], self.body, self.ts(8.2), muted, 'left')
            s.gap(2.2 * mm)
        contact = '  ·  '.join(x for x in (self.address, self.email) if x)
        if contact:
            s.para(contact, self.body, self.ts(7.4), self.ts(7.4) * 1.5, muted, 0, shrink_to=self.ts(6.4))
        s.draw()

    def cover_band(self):
        d = self.d
        theme = self.theme
        paper, ink, accent = self.cover_palette()
        self.paint(paper)
        c = self.c
        band = self.h * 0.31
        c.setFillColor(self.ink)
        c.rect(0, self.h - band, self.w, band, fill=1, stroke=0)
        c.setFillColor(self.accent)
        c.rect(0, self.h - band - 2.2 * mm, self.w, 2.2 * mm, fill=1, stroke=0)
        white = HexColor('#FFFFFF')
        self.eyebrow(d['denomination'] or 'SUNDAY WORSHIP', self.h - 14 * mm,
                     tint(theme.accent, 0.35), align='left')

        head = self.stack(self.h - 22 * mm, self.h - band + 8 * mm)
        art = self.logo_block()
        if art:
            head.block(art[0], art[1])
            head.gap(3 * mm)
        head.line(d['church'], self.head_black, self.ds(26), white, 'left')
        head.gap(3 * mm, flex=1)
        stamp, weekday = korean_date(d['date'])
        head.line('  ·  '.join(x for x in (stamp, weekday, issue_label(d['issue'])) if x),
                  self.body, self.ts(8.6), tint(theme.accent, 0.45), 'left')
        head.draw()

        s = self.stack(self.h - band - 14 * mm, 20 * mm)
        s.gap(4 * mm, flex=0.9)
        s.para(d['tagline'], self.body_light, self.ts(11.5), self.ts(11.5) * 1.7,
               self.muted, 0, shrink_to=self.ts(9))
        s.gap(8 * mm, flex=0.8)
        s.rule(width=self.inner * 0.24, thickness=2.4, color=self.accent)
        s.gap(6 * mm)
        s.para(d['sermon'], self.head_bold, self.ds(18), self.ds(18) * 1.34, self.ink, 0,
               shrink_to=self.ds(12))
        s.gap(3 * mm)
        s.line(d['scripture'], self.body_bold, self.ts(9.4), self.accent, 'left')
        s.gap(6 * mm, flex=0.8)
        if d['service_time']:
            s.line(d['service_time'], self.body, self.ts(8.4), self.muted, 'left')
            s.gap(2.2 * mm)
        contact = '  ·  '.join(x for x in (self.address, self.email) if x)
        if contact:
            s.para(contact, self.body, self.ts(7.6), self.ts(7.6) * 1.5, self.muted, 0,
                   shrink_to=self.ts(6.4))
        s.draw()

    def cover_rule(self):
        d = self.d
        paper, ink, accent = self.cover_palette()
        self.paint(paper)
        c = self.c
        muted = tint(self.theme.cover_ink, 0.45, self.theme.cover_paper)
        c.setStrokeColor(ink)
        c.setLineWidth(1.6)
        c.line(self.mx, self.h - 14 * mm, self.w - self.mx, self.h - 14 * mm)
        self.eyebrow(d['denomination'] or 'SUNDAY WORSHIP', self.h - 20 * mm, muted, align='left')
        stamp, weekday = korean_date(d['date'])

        s = self.stack(self.h - 30 * mm, 20 * mm)
        art = self.logo_block()
        if art:
            s.block(art[0], art[1])
            s.gap(5 * mm)
        s.gap(2 * mm, flex=1.05)
        s.line(d['church'], self.head_black, self.ds(29), ink, 'left')
        s.gap(4 * mm)
        s.para(d['tagline'], self.body_light, self.ts(11), self.ts(11) * 1.75, muted, 0,
               shrink_to=self.ts(8.6))
        s.gap(8 * mm, flex=0.95)
        s.rule(thickness=0.6, color=ink)
        s.gap(5 * mm)
        s.para(d['sermon'], self.head_bold, self.ds(16), self.ds(16) * 1.36, ink, 0, shrink_to=self.ds(11))
        s.gap(2.8 * mm)
        s.line(d['scripture'], self.body, self.ts(9), muted, 'left')
        s.gap(5 * mm)
        s.rule(thickness=0.6, color=ink)
        s.gap(4 * mm, flex=0.4)
        s.line('  ·  '.join(x for x in (stamp, weekday, issue_label(d['issue'])) if x),
               self.body, self.ts(8.4), muted, 'left')
        if d['service_time']:
            s.gap(2.2 * mm)
            s.line(d['service_time'], self.body, self.ts(8.2), muted, 'left')
        contact = '  ·  '.join(x for x in (self.address, self.email) if x)
        if contact:
            s.gap(2.4 * mm)
            s.para(contact, self.body, self.ts(7.4), self.ts(7.4) * 1.5, muted, 0, shrink_to=self.ts(6.4))
        s.draw()

    def cover_image(self):
        d = self.d
        c = self.c
        self.paint(HexColor('#FFFFFF'))
        if not d.get('custom_background'):
            self.note('디자인 · 용지에서 표지로 쓸 PNG·JPG 이미지를 등록해 주세요.')
            self.cover_light()
            return
        from custom_designs import image_bytes
        image = ImageReader(BytesIO(image_bytes(d['custom_background'])))
        iw, ih = image.getSize()
        mode = d.get('custom_fit', 'contain')
        if mode == 'cover':
            scale = max(self.w / iw, self.h / ih)
        else:
            scale = min(self.w / iw, self.h / ih)
        c.drawImage(image, (self.w - iw * scale) / 2, (self.h - ih * scale) / 2,
                    width=iw * scale, height=ih * scale, mask='auto')
        if not d['custom_show_text']:
            return
        light = d['custom_color'] != 'dark'
        ink = HexColor('#FFFFFF') if light else HexColor('#1E293B')
        muted = tint('#FFFFFF' if light else '#1E293B', 0.25, '#94A3B8')
        top = self.h - float(d['custom_top']) * mm
        if d['custom_panel']:
            c.setFillColor(HexColor('#0F172A') if light else HexColor('#FFFFFF'))
            c.setFillAlpha(0.62 if light else 0.80)
            c.rect(self.mx - 4 * mm, 14 * mm, self.inner + 8 * mm, top - 12 * mm, fill=1, stroke=0)
            c.setFillAlpha(1)
        stamp, weekday = korean_date(d['date'])
        s = self.stack(top - 4 * mm, 18 * mm)
        s.line(d['denomination'], self.body, self.ts(8.4), muted, 'center')
        s.gap(2.6 * mm)
        s.line(d['church'], self.head_black, self.ds(24), ink, 'center')
        s.gap(3 * mm)
        s.rule(width=self.inner * 0.18, thickness=0.6, color=muted, align='center')
        s.gap(3 * mm)
        s.para(d['tagline'], self.head, self.ts(10.4), self.ts(10.4) * 1.7, muted, 1, shrink_to=self.ts(8.2))
        s.gap(5 * mm, flex=1)
        s.para(d['sermon'], self.head_bold, self.ds(14), self.ds(14) * 1.4, ink, 1, shrink_to=self.ds(10))
        s.gap(2.4 * mm)
        s.line(d['scripture'], self.body, self.ts(8.8), muted, 'center')
        s.gap(4 * mm, flex=0.5)
        s.line('  ·  '.join(x for x in (stamp, weekday, issue_label(d['issue'])) if x),
               self.body, self.ts(8.2), muted, 'center')
        if d['service_time']:
            s.gap(2.2 * mm)
            s.line(d['service_time'], self.body, self.ts(8), muted, 'center')
        s.draw()

    # -- worship order -----------------------------------------------
    def page_worship(self, index):
        d = self.d
        self.open_panel(index)
        top, bottom = self.header(index, '예배 순서', 'ORDER OF WORSHIP')
        c = self.c
        rows = [split_row(r.strip()) for r in d['order'].splitlines() if r.strip()]
        if len(rows) > 24:
            self.note('예배 순서가 24개를 넘어 뒷부분을 줄였습니다.')
            rows = rows[:24]

        s = self.stack(top, bottom)
        if d['service_note'].strip():
            note_size = self.ts(9)
            p, height = paragraph(d['service_note'], self.inner - 9 * mm, self.body,
                                  note_size, note_size * 1.62, self.ink, 0)
            pad = 4.2 * mm

            def draw(cv, x, y, box, _p=p, _h=height, _pad=pad):
                cv.setFillColor(self.soft)
                cv.rect(x, y - _h - 2 * _pad, box, _h + 2 * _pad, fill=1, stroke=0)
                cv.setFillColor(self.accent)
                cv.rect(x, y - _h - 2 * _pad, 1.1 * mm, _h + 2 * _pad, fill=1, stroke=0)
                _p.drawOn(cv, x + 4.5 * mm, y - _pad - _h)
            s.block(draw, height + 2 * pad)
            s.gap(6 * mm, flex=0.3)

        label_size = self.ts(10.2)
        value_size = self.ts(9.4)
        num_size = self.ts(7.6)
        num_col = self.inner * (0.085 if self.n == 4 else 0.11)
        label_col = self.inner * 0.40
        value_col = self.inner - num_col - label_col - 2 * mm
        highlight = None
        for i, (label, value) in enumerate(rows):
            if highlight is None and any(k in label for k in ('말씀', '설교')):
                highlight = i
            lp, lh = paragraph(label, label_col, self.head_bold, label_size,
                               label_size * 1.42, self.ink, 0)
            vp, vh = paragraph(value, value_col, self.body, value_size,
                               value_size * 1.46, self.muted, 2)
            extra = 0
            sub = None
            if highlight == i and (d['sermon'] or d['scripture']):
                text = ' · '.join(x for x in (d['sermon'], d['scripture']) if x)
                sub, extra = paragraph(text, label_col + value_col, self.head, self.ts(8.8),
                                       self.ts(8.8) * 1.45, self.accent, 0)
                extra += 1.6 * mm
            height = max(lh, vh) + extra

            def draw(cv, x, y, box, _l=lp, _lh=lh, _v=vp, _vh=vh, _i=i, _sub=sub,
                     _extra=extra, _height=height):
                cv.setFillColor(self.accent)
                cv.setFont(self.body, num_size)
                cv.drawString(x, y - _lh + (label_size * 0.30), f'{_i + 1:02}')
                _l.drawOn(cv, x + num_col, y - _lh)
                _v.drawOn(cv, x + num_col + label_col + 2 * mm, y - _vh)
                if _sub is not None:
                    _sub.drawOn(cv, x + num_col, y - max(_lh, _vh) - _extra + 1.6 * mm)
                cv.setStrokeColor(self.hairline)
                cv.setLineWidth(0.4)
                cv.line(x, y - _height - 2.4 * mm, x + box, y - _height - 2.4 * mm)
            s.block(draw, height + 2.4 * mm)
            s.gap(3.4 * mm, flex=1.0, cap=9 * mm)
        s.draw(balance=0.42)
        self.c.showPage()

    # -- reflection --------------------------------------------------
    def intro_stack(self, top, bottom):
        """Title, subtitle and pull quote for the first meditation panel."""
        d = self.d
        s = self.stack(top, bottom)
        empty = True
        if d['article_title'].strip():
            s.para(d['article_title'], self.head_bold, self.ds(14.5), self.ds(14.5) * 1.42,
                   self.ink, 0, shrink_to=self.ds(11))
            s.gap(2.6 * mm)
            empty = False
        if d['article_subtitle'].strip():
            s.para(d['article_subtitle'], self.body, self.ts(8.8), self.ts(8.8) * 1.55,
                   self.muted, 0)
            s.gap(3 * mm)
            empty = False
        if d['article_quote'].strip():
            qsize = self.ts(10.6)
            qp, qh = paragraph(d['article_quote'], self.inner - 7 * mm, self.head,
                               qsize, qsize * 1.66, self.accent, 0)

            def draw(cv, x, y, box, _p=qp, _h=qh):
                cv.setStrokeColor(self.accent)
                cv.setLineWidth(1.6)
                cv.line(x + 0.7 * mm, y, x + 0.7 * mm, y - _h)
                _p.drawOn(cv, x + 7 * mm, y - _h)
            s.block(draw, qh)
            s.gap(5.5 * mm)
            empty = False
        if not empty:
            s.gap(1 * mm)
        return s

    def body_metrics(self, texts, width, capacity, gap):
        """Pick one type size and leading so the meditation fills its columns."""
        minimum = self.ts(8.0)
        largest = self.ts(11.6)
        lead = 1.68

        def measure(size, ratio):
            total = 0
            for text in texts:
                _, h = paragraph(text, width, self.body, size, size * ratio, self.ink, 4)
                total += h + gap
            return total - gap

        chosen = minimum
        size = largest
        while size >= minimum:
            if measure(size, lead) <= capacity:
                chosen = size
                break
            size = round(size - 0.2, 2)
        filled = measure(chosen, lead)
        # A short reflection opens up its leading instead of floating at the top.
        while filled < capacity * 0.88 and lead < 1.88:
            nxt = round(lead + 0.03, 3)
            if measure(chosen, nxt) > capacity:
                break
            lead = nxt
            filled = measure(chosen, lead)
        return chosen, lead

    def page_reflection(self, indexes):
        d = self.d
        texts = [t.strip() for t in d['article_body'].split('\n\n') if t.strip()]
        gap = 2.6 * mm

        self.open_panel(indexes[0])
        top, bottom = self.content_box()
        intro_height = self.intro_stack(top, bottom).natural_height()
        capacity = 0
        narrowest = None
        for order, index in enumerate(indexes):
            self.open_panel(index)
            panel_top, panel_bottom = self.content_box()
            capacity += panel_top - panel_bottom - (intro_height if order == 0 else 0)
            narrowest = self.inner if narrowest is None else min(narrowest, self.inner)
        size, lead = self.body_metrics(texts, narrowest or 100, max(capacity, 1), gap) if texts else (10, 1.68)

        queue = None
        for order, index in enumerate(indexes):
            self.open_panel(index)
            heading = d['article_heading'] or '말씀 묵상'
            if order:
                heading += ' · 이어서'
            panel_top, panel_bottom = self.header(index, heading, 'WORD & REFLECTION')
            if order == 0:
                intro = self.intro_stack(panel_top, panel_bottom)
                intro.draw(justify=False)
                panel_top -= intro.natural_height()
            if queue is None:
                queue = [paragraph(t, self.inner, self.body, size, size * lead, self.ink, 4)[0]
                         for t in texts]
            end = self.pour(queue, panel_top, panel_bottom, gap)
            if index == indexes[-1] and not queue and d.get('sermon_notes', 'on') != 'off':
                self.note_lines(end - 6 * mm, panel_bottom)
            self.c.showPage()
        if queue:
            self.note('묵상 글이 조금 길어 마지막 부분이 실리지 못했습니다. 본문을 줄이거나 A3 3단 용지를 선택해 보세요.')

    def pour(self, queue, top, bottom, gap):
        """Draw paragraphs from `queue` until the column runs out. Mutates queue."""
        y = top
        while queue:
            block = queue[0]
            _, height = block.wrap(self.inner, 100000)
            if height <= y - bottom:
                block.drawOn(self.c, self.mx, y - height)
                y -= height + gap
                queue.pop(0)
                continue
            pieces = block.split(self.inner, y - bottom)
            if len(pieces) >= 2:
                head = pieces[0]
                _, head_h = head.wrap(self.inner, 100000)
                head.drawOn(self.c, self.mx, y - head_h)
                queue[0:1] = list(pieces[1:])
                y = bottom
            break
        return y

    def note_lines(self, top, bottom):
        """Fill an unused tail of the meditation page with a writing area."""
        if top - bottom < 34 * mm:
            return
        c = self.c
        tracked(c, '말씀 노트', self.mx, top - self.ts(9) * 0.9, self.body_bold,
                self.ts(8.6), self.ts(8.6) * 0.18, self.accent)
        c.setStrokeColor(self.hairline)
        c.setLineWidth(0.4)
        y = top - self.ts(9) - 6.5 * mm
        step = 8.6 * mm
        while y > bottom + 2 * mm:
            c.line(self.mx, y, self.w - self.mx, y)
            y -= step

    # -- news --------------------------------------------------------
    def page_news(self, index, with_prayer):
        d = self.d
        self.open_panel(index)
        top, bottom = self.header(index, '교회 소식', 'LIFE TOGETHER')
        items = [t.strip() for t in d['announcements'].splitlines() if t.strip()]
        s = self.stack(top, bottom)
        size = self.ts(9.8)
        num_col = self.inner * (0.075 if self.n == 4 else 0.10)
        for i, text in enumerate(items):
            p, h = paragraph(text, self.inner - num_col, self.body, size, size * 1.62, self.ink, 0)

            def draw(cv, x, y, box, _p=p, _h=h, _i=i):
                cv.setFillColor(self.accent)
                cv.circle(x + 1.0 * mm, y - size * 0.62, 0.85 * mm, fill=1, stroke=0)
                cv.setFillColor(self.muted)
                cv.setFont(self.body, self.ts(7.4))
                _p.drawOn(cv, x + num_col, y - _h)
            s.block(draw, h)
            s.gap(3.2 * mm, flex=0.9, cap=8 * mm)
        if with_prayer and self.prayer.strip():
            s.gap(4 * mm, flex=3.0)
            psize = self.ts(9.4)
            pp, ph = paragraph(self.prayer, self.inner - 9 * mm, self.body, psize, psize * 1.66,
                               self.ink, 0)
            title_h = self.ts(11) * 1.5
            pad = 5 * mm

            def draw(cv, x, y, box, _p=pp, _h=ph, _t=title_h, _pad=pad):
                total = _h + _t + 2 * _pad
                cv.setFillColor(self.soft)
                cv.rect(x, y - total, box, total, fill=1, stroke=0)
                cv.setStrokeColor(self.accent)
                cv.setLineWidth(0.6)
                cv.line(x, y, x + box, y)
                tracked(cv, '함께 기도해요', x + 4.5 * mm, y - _pad - self.ts(11) * 0.92,
                        self.head_bold, self.ts(11.5), 0, self.accent)
                _p.drawOn(cv, x + 4.5 * mm, y - _pad - _t - _h)
            s.block(draw, ph + title_h + 2 * pad)
        s.draw(balance=0.30)
        self.c.showPage()

    def page_info(self, index):
        d = self.d
        self.open_panel(index)
        top, bottom = self.header(index, '교회 안내', 'VISIT US')
        s = self.stack(top, bottom)
        rows = [('예배 시간', d['service_time']), ('찾아오시는 길', self.address),
                ('이메일', self.email), ('홈페이지', d['website']),
                ('교회 설립', d['established'])]
        for label, value in rows:
            if not value or not value.strip():
                continue
            lp, lh = paragraph(label, self.inner, self.body_bold, self.ts(8),
                               self.ts(8) * 1.4, self.accent, 0)
            vp, vh = paragraph(value, self.inner, self.body, self.ts(9.6),
                               self.ts(9.6) * 1.6, self.ink, 0)

            def draw(cv, x, y, box, _l=lp, _lh=lh, _v=vp, _vh=vh):
                _l.drawOn(cv, x, y - _lh)
                _v.drawOn(cv, x, y - _lh - 1.4 * mm - _vh)
                cv.setStrokeColor(self.hairline)
                cv.setLineWidth(0.4)
                cv.line(x, y - _lh - _vh - 5 * mm, x + box, y - _lh - _vh - 5 * mm)
            s.block(draw, lh + vh + 5 * mm)
            s.gap(3.5 * mm, flex=0.8, cap=9 * mm)
        if self.prayer.strip():
            s.gap(4 * mm, flex=3.0)
            psize = self.ts(9.4)
            pp, ph = paragraph(self.prayer, self.inner - 9 * mm, self.body, psize, psize * 1.66,
                               self.ink, 0)
            title_h = self.ts(11) * 1.5
            pad = 5 * mm

            def draw(cv, x, y, box, _p=pp, _h=ph, _t=title_h, _pad=pad):
                total = _h + _t + 2 * _pad
                cv.setFillColor(self.soft)
                cv.rect(x, y - total, box, total, fill=1, stroke=0)
                tracked(cv, '함께 기도해요', x + 4.5 * mm, y - _pad - self.ts(11) * 0.92,
                        self.head_bold, self.ts(11.5), 0, self.accent)
                _p.drawOn(cv, x + 4.5 * mm, y - _pad - _t - _h)
            s.block(draw, ph + title_h + 2 * pad)
        s.draw(balance=0.30)
        self.c.showPage()

    # -- assembly ----------------------------------------------------
    def build(self):
        self.cover()
        self.page_worship(2)
        if self.n == 6:
            self.page_reflection([3, 4])
            self.page_news(5, with_prayer=False)
            self.page_info(6)
        else:
            self.page_reflection([3])
            self.page_news(4, with_prayer=True)
        self.c.save()
        return self.buffer.getvalue()


def draw_pages(d, public=False, notes=None):
    return Book(d, public=public, notes=notes).build()


def cover_only(d):
    """One page: the cover panel alone. Used for the design gallery."""
    book = Book(d, public=False, notes=[])
    book.cover()
    book.c.save()
    return book.buffer.getvalue()


def impose(source, d):
    reader = PdfReader(BytesIO(source))
    writer = PdfWriter()
    sheet_w, sheet_h, ws = geometry(d)
    groups = ((3, 0), (1, 2)) if len(ws) == 2 else ((4, 5, 0), (1, 2, 3))
    for group in groups:
        sheet = writer.add_blank_page(width=sheet_w, height=sheet_h)
        x = 0
        for index in group:
            page = reader.pages[index]
            sheet.merge_transformed_page(page, Transformation().translate(tx=x))
            x += float(page.mediabox.width)
    from pypdf.generic import DictionaryObject, NameObject
    writer._root_object[NameObject('/ViewerPreferences')] = DictionaryObject({
        NameObject('/Duplex'): NameObject('/DuplexFlipShortEdge'),
        NameObject('/PrintScaling'): NameObject('/None')})
    writer.add_metadata({'/Title': d['church'] + ' 주보 양면 인쇄용', '/Author': d['church'],
                         '/Creator': credit()})
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
