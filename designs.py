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
       cover='light', cover_paper='#FCFAF4', motif='cross', frame=True),
    _t('linen', '리넨 그레이스', '리넨빛 종이와 차분한 회갈색 · 조용한 품격', '정통',
       paper='#FFFFFF', ink='#33352F', accent='#8B8274', muted='#787468', soft='#F4F2EC',
       cover='light', cover_paper='#F5F3ED', motif='monogram', frame=True),
    _t('gold', '골든 라인', '가는 금선 장식과 여백 · 예식용 주보에 어울립니다', '정통',
       paper='#FFFFFF', ink='#26262B', accent='#B0873A', muted='#6F6F76', soft='#F7F2E6',
       cover='light', cover_paper='#FFFDF7', motif='deco', frame=True),
    _t('warm', '따뜻한 소식지', '연한 살구빛 바탕 · 가정 같은 분위기', '정통',
       paper='#FFFFFF', ink='#57402F', accent='#B0774C', muted='#836A55', soft='#F7EFE4',
       cover='light', cover_paper='#FBF4EA', motif='cross', frame=False),

    # --- 깊은 색 표지 ---------------------------------------------------
    _t('royal', '로열 사파이어', '짙은 남색과 금빛 잎 · 가장 격식 있는 표지', '깊은 색',
       paper='#FFFFFF', ink='#1B2C48', accent='#B08B45', muted='#6A7385', soft='#F1F3F7',
       cover='frame', cover_paper='#14284A', cover_ink='#F4E7C8', cover_accent='#D6B676',
       motif='leaves', frame=True),
    _t('emerald', '에메랄드 가든', '깊은 초록과 금빛 잎사귀', '깊은 색',
       paper='#FFFFFF', ink='#14382F', accent='#A2803C', muted='#5F7168', soft='#EFF4F0',
       cover='frame', cover_paper='#0F3B31', cover_ink='#FCF1D8', cover_accent='#D3B071',
       motif='leaves', frame=True),
    _t('burgundy', '버건디 크라운', '진한 자주빛과 금빛 잎사귀', '깊은 색',
       paper='#FFFFFF', ink='#4A2033', accent='#A97C46', muted='#7A6069', soft='#F7F0F1',
       cover='frame', cover_paper='#55203A', cover_ink='#FCEFD8', cover_accent='#DFB87C',
       motif='leaves', frame=True),
    _t('amethyst', '자수정 스테인드글라스', '보랏빛 유리창 무늬', '깊은 색',
       paper='#FFFFFF', ink='#2F2545', accent='#9A7BB0', muted='#6E6880', soft='#F4F1F8',
       cover='frame', cover_paper='#2E1F45', cover_ink='#F6EBD4', cover_accent='#CBAE84',
       motif='glass', frame=True),
    _t('ocean', '오션 스테인드글라스', '푸른 유리창과 물빛', '깊은 색',
       paper='#FFFFFF', ink='#123A54', accent='#3F8C94', muted='#5C7484', soft='#EDF5F6',
       cover='frame', cover_paper='#103752', cover_ink='#E9F8F5', cover_accent='#9FD3CE',
       motif='glass', frame=True),
    _t('midnight', '미드나이트 글로리', '밤하늘빛 바탕에 퍼지는 빛살', '깊은 색',
       paper='#FFFFFF', ink='#1B2745', accent='#5C6DA8', muted='#65708C', soft='#F0F2F8',
       cover='frame', cover_paper='#142140', cover_ink='#EFF1FF', cover_accent='#C3CBEA',
       motif='rays', frame=True),
    _t('sunrise', '선라이즈 글로리', '해 뜨는 빛살과 따뜻한 주홍', '깊은 색',
       paper='#FFFFFF', ink='#7A3529', accent='#C4783C', muted='#8A6152', soft='#FBF0E4',
       cover='frame', cover_paper='#8A3C30', cover_ink='#FFF1DA', cover_accent='#F0BE7C',
       motif='rays', frame=True),

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

    # --- 내 디자인 -----------------------------------------------------
    _t('custom', '내 디자인', '직접 만든 표지 이미지를 올려 사용합니다', '내 디자인',
       paper='#FFFFFF', ink='#233143', accent='#B0873A', muted='#6C7684', soft='#F3F4F6',
       cover='image', motif=None, frame=False),
])

GROUP_ORDER = ['정통', '깊은 색', '부드러운 색', '현대적', '내 디자인']

# Designs retired in earlier versions map onto their closest replacement so that
# bulletins saved with an older release keep opening.
LEGACY = {'original': 'classic'}


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
