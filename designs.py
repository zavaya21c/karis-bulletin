"""Design catalogue: one table of tokens per bulletin design.

A design never contains layout code. It only declares colour, cover
composition, headline family and ornament, so every design gets the same
carefully tuned page engine.
"""
from reportlab.lib.colors import HexColor


class Theme:
    __slots__ = ('key', 'name', 'blurb', 'group', 'paper', 'ink', 'accent', 'muted', 'soft',
                 'cover', 'cover_paper', 'cover_ink', 'cover_accent', 'motif', 'head', 'body_hint',
                 'frame', 'inner_band')

    def __init__(self, key, name, blurb, group, paper, ink, accent, muted, soft,
                 cover, cover_paper=None, cover_ink=None, cover_accent=None,
                 motif=None, head='myeongjo', body_hint=None, frame=False, inner_band=False):
        self.key, self.name, self.blurb, self.group = key, name, blurb, group
        self.paper, self.ink, self.accent, self.muted, self.soft = paper, ink, accent, muted, soft
        self.cover = cover
        self.cover_paper = cover_paper or paper
        self.cover_ink = cover_ink or ink
        self.cover_accent = cover_accent or accent
        self.motif, self.head, self.body_hint = motif, head, body_hint
        self.frame, self.inner_band = frame, inner_band

    def color(self, name):
        return HexColor(getattr(self, name))


def _t(*args, **kwargs):
    theme = Theme(*args, **kwargs)
    return theme.key, theme


THEMES = dict([
    # --- 밝은 정통 ------------------------------------------------------
    _t('classic', '클래식 명조', '아이보리 바탕에 금선 · 가장 무난하고 단정합니다', '정통',
       paper='#FFFFFF', ink='#1E2A38', accent='#A6802F', muted='#6C7684', soft='#F4F1E9',
       cover='light', cover_paper='#FCFAF4', motif='book', frame=True),
    _t('linen', '리넨 그레이스', '리넨빛 종이와 차분한 회갈색 · 조용한 품격', '정통',
       paper='#FFFFFF', ink='#33352F', accent='#8B8274', muted='#787468', soft='#F4F2EC',
       cover='light', cover_paper='#F5F3ED', motif='monogram', frame=True),
    _t('gold', '골든 라인', '가는 금선 장식과 여백 · 예식용 주보에 어울립니다', '정통',
       paper='#FFFFFF', ink='#26262B', accent='#B0873A', muted='#6F6F76', soft='#F7F2E6',
       cover='light', cover_paper='#FFFDF7', motif='deco', frame=True),
    _t('warm', '따뜻한 소식지', '연한 살구빛 바탕 · 가정 같은 분위기', '정통',
       paper='#FFFFFF', ink='#57402F', accent='#B0774C', muted='#836A55', soft='#F7EFE4',
       cover='light', cover_paper='#FBF4EA', motif='book', frame=False),
    _t('platinum', '플래티넘 모노그램', '은회색 모노그램과 넓은 여백 · 차분한 격식', '정통',
       paper='#FFFFFF', ink='#24262B', accent='#8B8F99', muted='#6E7078', soft='#F4F4F6',
       cover='light', cover_paper='#FBFBFC', motif='monogram', frame=True),
    _t('champagne', '샴페인 프레이즈', '샴페인 골드와 아르데코 문양 · 화려하지 않은 고급스러움', '정통',
       paper='#FFFFFF', ink='#2B2419', accent='#C9A66B', muted='#7A715F', soft='#F8F3E7',
       cover='light', cover_paper='#FCF9F1', motif='deco', frame=True),
    _t('silverleaf', '실버 리프', '차가운 은빛 잎사귀와 청회색', '정통',
       paper='#FFFFFF', ink='#25313D', accent='#7C93A6', muted='#68737D', soft='#EEF2F5',
       cover='light', cover_paper='#F7FAFC', motif='leaves', frame=True),
    _t('reverence', '리버런스 네이비', '아이보리 표지에 네이비 말씀 배너 · 예식 같은 격식', '정통',
       paper='#FFFFFF', ink='#1B2A4A', accent='#C5A059', muted='#4A4E54', soft='#F5F1EB',
       cover='motto', cover_paper='#FAF8F5', cover_ink='#1B2A4A', cover_accent='#C5A059',
       motif='book', head='myeongjo', frame=False),

    # --- 부드러운 색 ----------------------------------------------------
    _t('rose', '로즈 블로썸', '연분홍 바탕과 꽃 장식', '부드러운 색',
       paper='#FFFFFF', ink='#5E3244', accent='#B0708A', muted='#87646F', soft='#FBEFF1',
       cover='light', cover_paper='#FBF1F0', motif='flowers', frame=True),
    _t('ivory', '아이보리 블로썸', '아이보리 바탕과 들꽃', '부드러운 색',
       paper='#FFFFFF', ink='#31463B', accent='#9C824A', muted='#6C7A6F', soft='#F6F4E8',
       cover='light', cover_paper='#F8F5E9', motif='flowers', frame=True),
    _t('sanctuary', '세이지 채플', '세이지 그린과 아치 · 차분한 예배당', '부드러운 색',
       paper='#FFFFFF', ink='#26443C', accent='#7E9179', muted='#63776D', soft='#F1F4EE',
       cover='arch', cover_paper='#F4F6F1', motif='arch', frame=False),
    _t('laurel', '가든 로렐', '월계수 잎과 세이지 골드 · 은은한 품격', '부드러운 색',
       paper='#FFFFFF', ink='#243329', accent='#9C8B4E', muted='#6D7566', soft='#F3F4EC',
       cover='light', cover_paper='#F5F6EE', motif='leaves', frame=True),
    _t('dawn', '로즈골드 스테인드', '로즈골드빛 유리창 무늬 · 부드럽고 화사한 표지', '부드러운 색',
       paper='#FFFFFF', ink='#3B2A34', accent='#C08A72', muted='#7C6B72', soft='#F8F0EE',
       cover='light', cover_paper='#FBF3F1', motif='glass', frame=True),
    _t('chapel', '샹들리에 아치', '아이보리 아치와 따뜻한 금빛 · 예식 같은 분위기', '부드러운 색',
       paper='#FFFFFF', ink='#3A2E22', accent='#B7935A', muted='#7C7062', soft='#F6F1E6',
       cover='arch', cover_paper='#FAF6EC', motif='arch', frame=False),

    # --- 현대적 --------------------------------------------------------
    _t('editorial', '에디토리얼 크림', '큰 날짜 숫자와 테라코타 · 잡지 같은 표지', '현대적',
       paper='#FFFFFF', ink='#2C2F2B', accent='#B35B3E', muted='#6E7169', soft='#FAF6EE',
       cover='bigdate', cover_paper='#FBF8F1', motif=None, head='myeongjo', frame=False),
    _t('modern', '모던 블록', '청록 색면과 각진 글씨 · 젊은 공동체에', '현대적',
       paper='#FFFFFF', ink='#14313F', accent='#1F7A76', muted='#5D707A', soft='#EDF4F4',
       cover='band', cover_paper='#FFFFFF', motif=None, head='square', body_hint='square',
       frame=False, inner_band=True),
    _t('slate', '슬레이트 모던', '차분한 청회색과 넓은 색면', '현대적',
       paper='#FFFFFF', ink='#23303B', accent='#4E6B7C', muted='#63737F', soft='#EEF2F5',
       cover='band', cover_paper='#FFFFFF', motif=None, head='square', body_hint='barun',
       frame=False, inner_band=True),
    _t('minimal', '미니멀 흑백', '선과 여백만으로 · 흑백 인쇄에 최적', '현대적',
       paper='#FFFFFF', ink='#1A1A1A', accent='#767676', muted='#6B6B6B', soft='#F2F2F2',
       cover='rule', cover_paper='#FFFFFF', motif=None, head='barun', body_hint='barun',
       frame=False),
    _t('graphite', '그래파이트 라인', '그래파이트 색면과 코퍼 포인트 · 세련된 인상', '현대적',
       paper='#FFFFFF', ink='#24262B', accent='#B0714A', muted='#63666D', soft='#F1F1F1',
       cover='band', cover_paper='#FFFFFF', motif=None, head='square', body_hint='square',
       frame=False, inner_band=True),
    _t('inkline', '잉크라인', '먹빛 세리프와 가는 금선 · 절제된 품격', '현대적',
       paper='#FFFFFF', ink='#1F2421', accent='#9C7B3E', muted='#6B6E68', soft='#F2F1EC',
       cover='rule', cover_paper='#FFFFFF', motif=None, head='myeongjo', body_hint='barun',
       frame=False),

    # --- 내 디자인 -----------------------------------------------------
    _t('custom', '내 디자인', '직접 만든 표지 이미지를 올려 사용합니다', '내 디자인',
       paper='#FFFFFF', ink='#233143', accent='#B0873A', muted='#6C7684', soft='#F3F4F6',
       cover='image', motif=None, frame=False),
])

GROUP_ORDER = ['정통', '부드러운 색', '현대적', '내 디자인']

# Designs retired in earlier versions map onto their closest replacement so that
# bulletins saved with an older release keep opening.
LEGACY = {
    'original': 'classic',
    'royal': 'platinum',
    'emerald': 'laurel',
    'burgundy': 'dawn',
    'amethyst': 'dawn',
    'ocean': 'silverleaf',
    'midnight': 'silverleaf',
    'sunrise': 'champagne',
}


def resolve(key):
    return LEGACY.get(key, key)


def catalogue():
    """Ordered list for the design picker."""
    items = []
    for group in GROUP_ORDER:
        for theme in THEMES.values():
            if theme.group == group:
                items.append({'id': theme.key, 'name': theme.name, 'blurb': theme.blurb,
                              'group': group, 'paper': theme.cover_paper,
                              'ink': theme.cover_ink, 'accent': theme.cover_accent})
    return items
