"""번들 글꼴을 다시 만드는 도구 (배포판 제작자용, 평소에는 실행할 필요 없습니다).

나눔글꼴(NAVER, SIL Open Font License 1.1)에서 한글·라틴·문장부호만 남겨
가볍게 만든 뒤, OFL 제3조의 예약 글꼴 이름(Reserved Font Name) 규정에 따라
글꼴 이름을 바꾸어 저장합니다. 저작권 표시와 라이선스 문구는 원본 그대로
유지되므로 assets/fonts 안의 라이선스 파일을 반드시 함께 보관하세요.

사용법:  python build_fonts.py [나눔글꼴_TTF_폴더]
기본 경로는 리눅스의 /usr/share/fonts/truetype/nanum 입니다.
fonttools 가 필요합니다:  pip install fonttools brotli
"""
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent / 'assets/fonts'

# 남길 문자 범위: 라틴 기본·확장, 한글 자모와 음절, 문장부호, 통화·화살표·도형 기호.
UNICODES = ','.join([
    'U+0020-007E', 'U+00A0-00FF', 'U+00B7',
    'U+2010-2015', 'U+2018-201F', 'U+2022', 'U+2026', 'U+2030', 'U+2032-2033',
    'U+203B', 'U+20A9', 'U+20AC', 'U+2190-2193', 'U+2500-2503', 'U+25A0-25CF',
    'U+2605-2606', 'U+261E', 'U+271D',
    'U+3000-303F', 'U+3130-318F', 'U+1100-11FF', 'U+AC00-D7A3',
    'U+FF01-FF60',
])

# 원본 파일 -> (내보낼 파일, 글꼴 가족 이름, 스타일 이름)
FACES = [
    ('NanumMyeongjo.ttf',          'BulletinMyeongjo-Regular.ttf',   'Bulletin Myeongjo', 'Regular'),
    ('NanumMyeongjoBold.ttf',      'BulletinMyeongjo-Bold.ttf',      'Bulletin Myeongjo', 'Bold'),
    ('NanumMyeongjoExtraBold.ttf', 'BulletinMyeongjo-ExtraBold.ttf', 'Bulletin Myeongjo', 'ExtraBold'),
    ('NanumBarunGothicLight.ttf',  'BulletinGothic-Light.ttf',       'Bulletin Gothic',   'Light'),
    ('NanumBarunGothic.ttf',       'BulletinGothic-Regular.ttf',     'Bulletin Gothic',   'Regular'),
    ('NanumBarunGothicBold.ttf',   'BulletinGothic-Bold.ttf',        'Bulletin Gothic',   'Bold'),
    ('NanumSquareR.ttf',           'BulletinSquare-Regular.ttf',     'Bulletin Square',   'Regular'),
    ('NanumSquareB.ttf',           'BulletinSquare-Bold.ttf',        'Bulletin Square',   'Bold'),
    ('NanumSquareEB.ttf',          'BulletinSquare-ExtraBold.ttf',   'Bulletin Square',   'ExtraBold'),
    ('NanumGothic.ttf',            'BulletinClassic-Regular.ttf',    'Bulletin Classic',  'Regular'),
    ('NanumGothicBold.ttf',        'BulletinClassic-Bold.ttf',       'Bulletin Classic',  'Bold'),
]

CREDIT = ('Subset of the Nanum fonts by NAVER Corporation, licensed under the SIL Open Font '
          'License 1.1. Renamed as required by OFL clause 3 (Reserved Font Names).')


def rename(path, family, style):
    font = TTFont(path)
    full = family if style == 'Regular' else f'{family} {style}'
    postscript = full.replace(' ', '')
    values = {1: family, 2: style if style in ('Regular', 'Bold', 'Italic', 'Bold Italic') else 'Regular',
              3: f'{postscript}; subset for Karis Bulletin', 4: full, 6: postscript,
              16: family, 17: style, 10: CREDIT,
              13: ('This Font Software is licensed under the SIL Open Font License, Version 1.1. '
                   'This font is a renamed, subset Modified Version of the Nanum fonts '
                   '(Copyright NAVER Corporation), as permitted by that license.'),
              14: 'https://scripts.sil.org/OFL'}
    for record in list(font['name'].names):
        if record.nameID in values:
            font['name'].setName(values[record.nameID], record.nameID,
                                 record.platformID, record.platEncID, record.langID)
    for name_id, value in values.items():
        if not font['name'].getDebugName(name_id):
            font['name'].setName(value, name_id, 3, 1, 0x409)
    font.save(path)
    font.close()


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else '/usr/share/fonts/truetype/nanum')
    if not source.is_dir():
        raise SystemExit(f'나눔글꼴 TTF 폴더를 찾을 수 없습니다: {source}')
    OUT.mkdir(parents=True, exist_ok=True)
    for original, target, family, style in FACES:
        src = source / original
        if not src.exists():
            print(f'건너뜀 (원본 없음): {original}')
            continue
        dst = OUT / target
        subprocess.check_call([
            sys.executable, '-m', 'fontTools.subset', str(src),
            f'--output-file={dst}', f'--unicodes={UNICODES}',
            '--layout-features=*', '--name-IDs=*', '--no-hinting', '--recalc-bounds',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rename(dst, family, style)
        print(f'{target}  {dst.stat().st_size // 1024}KB  ({family} {style})')


if __name__ == '__main__':
    main()
