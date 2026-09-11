"""Build assets/design-samples.pdf — a printable catalogue of every design."""
import math
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from designs import catalogue
from layouts import FORMATS
from render import clean, render
from typography import init_fonts

init_fonts()

LABELS = {'a4-half': 'A4 반접지 · 4면', 'a4-third': 'A4 3단 · 6면', 'a3-third': 'A3 3단 · 6면'}
DESIGNS = [item for item in catalogue() if item['id'] != 'custom']
ITEMS = [(fmt, design) for fmt in FORMATS for design in DESIGNS]
PER_PAGE = 22

SAMPLE = {
    'church': '은혜교회',
    'denomination': '대한예수교장로회',
    'established': '1998년 4월 5일',
    'address': '우리 교회 주소를 입력하세요',
    'email': '',
    'website': '',
    'service_time': '주일 오전 11시 · 본당',
    'prayers': '새가족이 믿음 안에 잘 정착하도록 함께 기도합니다.\n이웃을 사랑하고 섬기는 교회가 되도록 기도합니다.',
    # 아래 이름은 모두 가상의 예시입니다.
    'order': '예배의 부름 | 인도자\n찬송 | 다 함께\n기도 | 홍길순 집사\n성경봉독 | 인도자\n말씀 | 홍길동 목사\n결단 찬양 | 시온 찬양대\n광고 | 인도자\n축도 | 홍길동 목사',
    'announcements': '주일예배에 오신 모든 분을 환영합니다.\n예배 후 새가족 환영 시간이 있습니다.\n이번 주 이웃을 위한 나눔에 함께해 주세요.',
}


def index_pages():
    pages = math.ceil(len(ITEMS) / PER_PAGE)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(210 * mm, 297 * mm))
    for section in range(pages):
        c.setFillColorRGB(.12, .17, .25)
        c.setFont('SerifBlack', 26)
        c.drawString(22 * mm, 264 * mm, '우리 교회에 맞는 주보')
        c.setFillColorRGB(.65, .50, .18)
        c.rect(22 * mm, 256 * mm, 26 * mm, 1.2 * mm, fill=1, stroke=0)
        c.setFillColorRGB(.35, .40, .48)
        c.setFont('Sans', 10.5)
        c.drawString(22 * mm, 245 * mm, f'디자인 {len(DESIGNS)}종 · 용지별 {len(ITEMS)}개 샘플')
        c.setFont('Sans', 9)
        c.drawString(22 * mm, 236 * mm, '각 샘플은 실제 인쇄 용지 크기의 앞면과 뒷면입니다.')
        c.drawString(22 * mm, 230 * mm, '인쇄: 선택한 용지 · 가로 · 양면 · 짧은 변 넘김 · 실제 크기 100%')
        for row, (fmt, design) in enumerate(ITEMS[section * PER_PAGE:(section + 1) * PER_PAGE]):
            i = section * PER_PAGE + row
            y = (215 - row * 7.6) * mm
            c.setFillColorRGB(.12, .17, .25)
            c.setFont('Sans', 9.6)
            c.drawString(22 * mm, y, f'{i + 1:02}')
            c.drawString(33 * mm, y, design['name'])
            c.setFillColorRGB(.45, .49, .56)
            c.drawString(95 * mm, y, LABELS[fmt])
            c.drawRightString(184 * mm, y, f'{pages + 1 + i * 2}–{pages + 2 + i * 2}쪽')
            c.setStrokeColorRGB(.87, .86, .82)
            c.setLineWidth(.4)
            c.line(22 * mm, y - 2.6 * mm, 184 * mm, y - 2.6 * mm)
        c.setFillColorRGB(.45, .49, .56)
        c.setFont('Sans', 8.6)
        c.drawString(22 * mm, 40 * mm, '샘플 문구는 예시입니다. 실제 내용은 편집실에서 입력하세요.')
        c.drawString(22 * mm, 33 * mm, f'샘플 목차 {section + 1} / {pages}')
        c.showPage()
    c.save()
    return buffer.getvalue()


def main():
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(index_pages())))
    for fmt, design in ITEMS:
        data = clean(dict(SAMPLE, format=fmt, design=design['id']))
        writer.append(PdfReader(BytesIO(render(data, 'print'))))
    writer.add_metadata({'/Title': f'카리스 주보제작 디자인 샘플 {len(ITEMS)}종'})
    try:
        # Every sample embeds the same fonts; folding the duplicates cuts the file by two thirds.
        writer.compress_identical_objects()
    except Exception:
        pass
    with open('assets/design-samples.pdf', 'wb') as stream:
        writer.write(stream)
    print(f'{len(writer.pages)}쪽 샘플집을 만들었습니다.')


if __name__ == '__main__':
    main()
