"""Validation and output modes.

`clean` is the single gate every request passes through; `render` turns a
cleaned bulletin into a reading PDF, a duplex imposition, or a public copy.
"""
import json
from datetime import date

from app_paths import ROOT
from typography import BODY_FONTS, HEAD_FONTS, init_fonts

# Legacy colour themes from the first release. Kept so older saved files load;
# the visual identity now lives entirely in designs.py.
THEMES = {'forest': None, 'navy': None, 'mono': None}

DEFAULTS = {
    'format': 'a4-half',
    'fold': 'roll',
    'design': 'classic',
    'logo': '',
    'logo_size': '22',
    'logo_place': 'above',
    'logo_x': '50',
    'logo_y': '30',
    'public_contacts': True,
    'public_names': 'mask',
    'body_font': '',
    'head_font': '',
    'sermon_notes': 'on',
    'custom_background': '',
    'custom_top': '40',
    'custom_color': 'dark',
    'custom_panel': True,
    'custom_show_text': True,
    'custom_fit': 'contain',
}
BOOLEAN_KEYS = ('public_prayers', 'public_contacts', 'custom_panel', 'custom_show_text')
LIMITS = {'custom_background': 6000000, 'logo': 1500000}
SHORT_KEYS = ('church', 'issue', 'address', 'email', 'website', 'article_title',
              'article_heading', 'sermon', 'scripture', 'denomination', 'established',
              'service_time')


def blank():
    return json.loads((ROOT / 'sample.json').read_text(encoding='utf-8')) | DEFAULTS


def clean(data):
    from designs import THEMES as DESIGN_THEMES, resolve
    from layouts import FORMATS

    original = blank()
    if not isinstance(data, dict) or set(data) - set(original):
        unknown = ', '.join(sorted(set(data) - set(original))) if isinstance(data, dict) else ''
        raise ValueError('알 수 없는 입력 항목입니다' + (': ' + unknown if unknown else '.'))
    result = original | data
    for key, value in result.items():
        if key in BOOLEAN_KEYS:
            if not isinstance(value, bool):
                raise ValueError('켜기·끄기 설정을 확인해 주세요: ' + key)
        elif not isinstance(value, str) or len(value) > LIMITS.get(key, 8000):
            raise ValueError('입력값을 확인해 주세요: ' + key)

    result['design'] = resolve(result['design'])
    if result['design'] not in DESIGN_THEMES:
        raise ValueError('디자인 설정을 확인해 주세요.')
    if result['format'] not in FORMATS:
        raise ValueError('용지 설정을 확인해 주세요.')
    if result['fold'] not in ('roll', 'accordion'):
        raise ValueError('접지 설정을 확인해 주세요.')
    if result['body_font'] and result['body_font'] not in BODY_FONTS:
        raise ValueError('본문 글꼴을 확인해 주세요.')
    if result['head_font'] and result['head_font'] not in HEAD_FONTS:
        raise ValueError('제목 글꼴을 확인해 주세요.')
    if result['logo'] and not result['logo'].startswith('data:image/png;base64,'):
        raise ValueError('로고는 PNG 파일을 사용해 주세요.')
    if result['logo_place'] not in ('above', 'top', 'bottom', 'free'):
        raise ValueError('로고 위치를 확인해 주세요.')
    for key, low, high, label in (('logo_size', 6, 90, '로고 크기는 6~90mm'),
                                  ('logo_x', 0, 100, '로고 가로 위치는 0~100%'),
                                  ('logo_y', 0, 400, '로고 세로 위치는 0~400mm')):
        try:
            value = float(result[key])
        except (TypeError, ValueError):
            raise ValueError(label + ' 사이의 숫자로 입력해 주세요.')
        if not low <= value <= high:
            raise ValueError(label + ' 사이로 지정해 주세요.')
    if result['custom_color'] not in ('dark', 'light'):
        raise ValueError('글자 색상을 확인해 주세요.')
    if result['public_names'] not in ('mask', 'show'):
        raise ValueError('공개본 이름 표시 설정을 확인해 주세요.')
    if result['sermon_notes'] not in ('on', 'off'):
        raise ValueError('말씀 노트 설정을 확인해 주세요.')
    if result['custom_fit'] not in ('contain', 'cover'):
        raise ValueError('배경 이미지 맞춤 방식을 확인해 주세요.')
    try:
        top = float(result['custom_top'])
    except (ValueError, TypeError):
        raise ValueError('글자 시작 위치는 숫자로 입력해 주세요.')
    if not 10 <= top <= 170:
        raise ValueError('글자 시작 위치는 위에서 10~170mm로 지정해 주세요.')
    if result['custom_background']:
        from custom_designs import image_bytes
        image_bytes(result['custom_background'])
    date.fromisoformat(result['date'])
    for key in ('church', 'issue', 'sermon', 'scripture'):
        if not result[key].strip():
            raise ValueError('필수 항목을 입력해 주세요: ' + key)
    for key in SHORT_KEYS:
        if len(result[key]) > 120:
            raise ValueError('입력 내용이 너무 깁니다: ' + key)
    if result.get('theme') not in THEMES:
        result['theme'] = 'forest'
    return result


def inspect(data):
    """Render once and report anything that had to be fitted or trimmed."""
    from layouts import draw_pages
    notes = []
    draw_pages(clean(data), public=False, notes=notes)
    return notes


def design_previews(data):
    """One PDF holding every design's cover, in catalogue order."""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from designs import catalogue
    from layouts import cover_only

    init_fonts()
    base = clean(data)
    writer = PdfWriter()
    for item in catalogue():
        candidate = dict(base, design=item['id'])
        try:
            page = cover_only(candidate)
        except Exception:
            page = cover_only(dict(base, design='classic'))
        writer.add_page(PdfReader(BytesIO(page)).pages[0])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def render(data, mode='reading', notes=None):
    if mode not in ('reading', 'print', 'public'):
        raise ValueError('출력 형식을 확인해 주세요.')
    init_fonts()
    from layouts import draw_pages, impose
    data = clean(data)
    source = draw_pages(data, public=(mode == 'public'), notes=notes)
    return impose(source, data) if mode == 'print' else source


if __name__ == '__main__':
    source = json.loads((ROOT / 'sample.json').read_text(encoding='utf-8'))
    for mode, suffix in [('reading', '읽기용'), ('print', '인쇄용_양면'), ('public', '홈페이지용')]:
        path = ROOT / 'output/pdf' / f'{source["church"]}_{source["date"]}_{suffix}.pdf'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(render(source, mode))
        print(path)
