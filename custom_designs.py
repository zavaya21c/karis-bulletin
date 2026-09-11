"""Local image library. Images are embedded in saved bulletins for portability."""
import base64,hashlib,re,secrets
from io import BytesIO
from pathlib import Path
from PIL import Image,ImageOps
from app_paths import storage_root
FOLDER=storage_root()/'내 디자인'
MAX_BYTES=4_000_000

def image_bytes(value):
    if not isinstance(value,str) or len(value)>6_000_000:raise ValueError('디자인 이미지는 4MB 이하로 등록해 주세요.')
    if ',' not in value or value.split(',',1)[0] not in ('data:image/png;base64','data:image/jpeg;base64'):raise ValueError('PNG 또는 JPG 이미지만 사용할 수 있습니다.')
    try:raw=base64.b64decode(value.split(',',1)[1],validate=True)
    except Exception as e:raise ValueError('이미지 파일이 올바르지 않습니다.') from e
    if len(raw)>MAX_BYTES:raise ValueError('디자인 이미지는 4MB 이하로 등록해 주세요.')
    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in ('PNG','JPEG') or im.width*im.height>12_000_000:raise ValueError('PNG·JPG 및 1200만 화소 이하 이미지를 사용해 주세요.')
            im.verify()
    except (OSError,Image.DecompressionBombError) as e:raise ValueError('이미지 파일을 읽을 수 없습니다.') from e
    return raw

def library():
    FOLDER.mkdir(parents=True,exist_ok=True)
    return [{'id':hashlib.sha256(p.name.encode()).hexdigest()[:24],'name':p.name} for p in sorted(FOLDER.iterdir()) if p.is_file() and not p.is_symlink() and p.suffix.lower() in ('.png','.jpg','.jpeg')]

def load_image(identifier):
    match=next((x for x in library() if x['id']==identifier),None)
    if not match:raise ValueError('디자인 파일이 없습니다. 목록을 다시 불러와 주세요.')
    p=FOLDER/match['name']
    if p.stat().st_size>MAX_BYTES:raise ValueError('디자인 이미지는 4MB 이하로 등록해 주세요.')
    raw=p.read_bytes();mime='image/png' if p.suffix.lower()=='.png' else 'image/jpeg';value='data:'+mime+';base64,'+base64.b64encode(raw).decode();image_bytes(value)
    return {'name':p.name,'image':value}

def register(name,value):
    raw=image_bytes(value)
    with Image.open(BytesIO(raw)) as im:
        im=ImageOps.exif_transpose(im);out=BytesIO()
        if value.startswith('data:image/jpeg'):im.convert('RGB').save(out,format='JPEG',quality=95);ext='.jpg'
        else:im.save(out,format='PNG');ext='.png'
    if len(out.getvalue())>MAX_BYTES:raise ValueError('변환한 이미지가 4MB를 넘습니다. 이미지를 줄여 주세요.')
    safe=re.sub(r'[^가-힣a-zA-Z0-9_-]','_',Path(name).stem)[:60] or '디자인'
    FOLDER.mkdir(parents=True,exist_ok=True);target=FOLDER/(safe+'-'+secrets.token_hex(4)+ext)
    with target.open('xb') as f:f.write(out.getvalue())
    return load_image(hashlib.sha256(target.name.encode()).hexdigest()[:24])
