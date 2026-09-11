"""Local-only bulletin editor. No external publishing or message sending."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from io import BytesIO
import json, os, re, threading, zipfile, secrets, subprocess
from datetime import datetime
import custom_designs
from render import ROOT, render, clean, init_fonts, inspect, design_previews

PORT=int(os.getenv('BULLETIN_PORT','8012'))
from app_paths import storage_root, documents_folder, open_folder
DATA=storage_root()/'data';DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
LOCK=threading.Lock()
PRINTS={}

PROFILE_KEYS={'church','denomination','established','address','email','website','service_time','logo','logo_size','logo_place','logo_x','logo_y','format','fold','design','theme','public_prayers','public_contacts','body_font','head_font','sermon_notes','custom_background','custom_top','custom_color','custom_panel','custom_show_text','custom_fit'}
def output_folder(data):
    church=re.sub(r'[^가-힣a-zA-Z0-9_.-]','_',data['church'])
    return documents_folder()/'카리스 주보제작'/(church.strip('.') or '교회')/data['date'][:4]

def save_bytes(data,suffix,content):
    folder=output_folder(data);folder.mkdir(parents=True,exist_ok=True)
    label=re.sub(r'[^가-힣a-zA-Z0-9_.-]','_',data['church']+'_'+data['date']+'_'+data['issue'])
    for number in range(10000):
        target=folder/(label+('' if number==0 else f'_{number+1}')+suffix)
        try:fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:continue
        with os.fdopen(fd,'wb') as stream:stream.write(content)
        return str(target)
    raise ValueError('같은 이름의 저장 파일이 너무 많습니다.')

def save_document(data,kind):
    suffix={'content':'_편집내용.json','reading':'_읽기용.pdf','print':'_인쇄용.pdf','public':'_홈페이지용.pdf','bundle':'_주보묶음.zip'}
    if kind not in suffix:raise ValueError('저장 형식을 확인해 주세요.')
    if kind=='content':content=json.dumps(data,ensure_ascii=False,indent=2).encode()
    elif kind=='bundle':
        buf=BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
            for mode in ('reading','print','public'):archive.writestr(mode+'.pdf',render(data,mode))
            archive.writestr('content.json',json.dumps(data,ensure_ascii=False,indent=2))
        content=buf.getvalue()
    else:content=render(data,kind)
    return save_bytes(data,suffix[kind],content)

def atomic_json(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");temp.chmod(0o600);temp.replace(path)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,body,status=200,mime='application/json; charset=utf-8',filename=None):
        if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
        if isinstance(body,str):body=body.encode()
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; frame-src 'self' blob:; object-src 'self' blob:; connect-src 'self'; frame-ancestors 'self'")
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers();self.wfile.write(body)
    def safe(self):
        return self.headers.get('Host') in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
    def do_GET(self):
        if not self.safe():return self.respond({'error':'허용하지 않는 접속 주소입니다.'},403)
        path=urlparse(self.path).path
        if path.startswith('/static/pdfjs/'):
            relative=path.removeprefix('/static/pdfjs/')
            file=(ROOT/'static/pdfjs'/relative).resolve()
            if (ROOT/'static/pdfjs').resolve() not in file.parents or not file.is_file():return self.respond({'error':'자료가 없습니다.'},404)
            return self.respond(file.read_bytes(),mime='text/javascript' if file.suffix=='.mjs' else 'application/octet-stream')
        if path.startswith('/api/print/'):
            token=path.rsplit('/',1)[-1]
            with LOCK: output=PRINTS.get(token)
            if output:return self.respond(output,mime='application/pdf')
            return self.respond({'error':'인쇄 자료가 만료되었습니다. 편집실에서 다시 열어 주세요.'},404)
        if path=='/api/designs':
            from designs import catalogue, GROUP_ORDER
            from typography import BODY_FONTS, HEAD_FONTS
            return self.respond({'items':catalogue(),'groups':GROUP_ORDER,
                'body_fonts':[{'id':k,'name':v[0]} for k,v in BODY_FONTS.items()],
                'head_fonts':[{'id':k,'name':v[0]} for k,v in HEAD_FONTS.items()]})
        if path=='/assets/brand-logo.png':
            file=ROOT/'assets/brand-logo.png'
            if not file.is_file():return self.respond({'error':'브랜드 로고가 없습니다.'},404)
            return self.respond(file.read_bytes(),mime='image/png')
        if path=='/api/about':
            info={'version':'2.0.0','project':'카리스 주보제작','author':'','year':'','notice':'',
                  'support_notice':'','support_account':'','support_link':'','suite':''}
            file=ROOT/'distribution.json'
            if file.exists():
                try:info.update({k:v for k,v in json.loads(file.read_text(encoding='utf-8')).items() if k in info or k=='contact'})
                except ValueError:pass
            info['brand_logo']=(ROOT/'assets/brand-logo.png').is_file()
            return self.respond(info)
        if path=='/api/presets':
            return self.respond({'items':json.loads((ROOT/'presets.json').read_text(encoding='utf-8'))})
        if path=='/api/design-library':return self.respond({'items':custom_designs.library()})
        if path.startswith('/api/design-image/'):
            try:return self.respond(custom_designs.load_image(path.rsplit('/',1)[-1]))
            except ValueError as e:return self.respond({'error':str(e)},422)
        if path=='/api/profile':
            p=DATA/'profile.json';return self.respond(json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})
        if path=='/api/draft':
            p=DATA/'draft.json';return self.respond({'data':json.loads(p.read_text(encoding="utf-8")) if p.exists() else {},'updated':int(p.stat().st_mtime*1000) if p.exists() else 0})
        if path=='/api/current':
            source=DATA/'current.json'
            return self.respond(clean(json.loads((source if source.exists() else ROOT/'sample.json').read_text(encoding="utf-8"))))
        if path=='/api/history':
            return self.respond({'items':[p.stem for p in sorted(DATA.glob('bulletin-*.json'),reverse=True)]})
        if path.startswith('/api/history/'):
            name=path.rsplit('/',1)[-1]
            if not re.fullmatch(r'bulletin-[a-zA-Z0-9_-]+',name):return self.respond({'error':'파일명을 확인해 주세요.'},400)
            file=DATA/(name+'.json')
            if file.exists():return self.respond(json.loads(file.read_text(encoding="utf-8")))
            return self.respond({'error':'저장된 주보가 없습니다.'},404)
        mapping={'/':'index.html','/print':'print.html','/static/print.js':'print.js','/static/print.css':'print.css','/static/app.js':'app.js','/static/app.css':'app.css'}
        if path in mapping:
            file=ROOT/'static'/mapping[path]
            mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[file.suffix]
            return self.respond(file.read_bytes(),mime=mime)
        self.respond({'error':'페이지가 없습니다.'},404)
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.safe() or origin not in {f'http://localhost:{PORT}',f'http://127.0.0.1:{PORT}'}:
            return self.respond({'error':'이 편집 화면에서만 실행할 수 있습니다.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<9000000 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('입력 자료의 형식이나 크기를 확인해 주세요.')
            payload=json.loads(self.rfile.read(length))
            path=urlparse(self.path).path
            if path=='/api/register-design':
                with LOCK:result=custom_designs.register(payload.get('name',''),payload.get('image',''))
                return self.respond(result)
            if path=='/api/open-design-folder':
                custom_designs.FOLDER.mkdir(parents=True,exist_ok=True);open_folder(custom_designs.FOLDER)
                return self.respond({'ok':True})
            if path=='/api/draft':
                draft=payload['data']
                if not isinstance(draft,dict) or set(draft)-set(clean({})):raise ValueError('편집 자료 형식을 확인해 주세요.')
                for key,value in draft.items():
                    if not isinstance(value,(str,bool)):raise ValueError('편집 자료 형식을 확인해 주세요.')
                with LOCK:atomic_json(DATA/'draft.json',draft)
                return self.respond({'ok':True})
            data=clean(payload['data'])
            if path=='/api/save-samples':
                return self.respond({'ok':True,'path':save_bytes(data,'_디자인샘플모음.pdf',(ROOT/'assets/design-samples.pdf').read_bytes())})
            if path=='/api/profile':
                with LOCK:atomic_json(DATA/'profile.json',{k:v for k,v in data.items() if k in PROFILE_KEYS})
                return self.respond({'ok':True})
            if path=='/api/open-folder':
                folder=output_folder(data);folder.mkdir(parents=True,exist_ok=True)
                open_folder(folder)
                return self.respond({'ok':True,'path':str(folder)})
            if path=='/api/backup':
                buf=BytesIO()
                with LOCK,zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
                    for file in DATA.glob('*.json'):archive.writestr(file.name,file.read_bytes())
                    for item in custom_designs.library():
                        file=custom_designs.FOLDER/item['name']
                        if file.stat().st_size<=custom_designs.MAX_BYTES:archive.writestr('내 디자인/'+file.name,file.read_bytes())
                    archive.writestr('editor-current.json',json.dumps(data,ensure_ascii=False))
                return self.respond({'ok':True,'path':save_bytes(data,'_전체백업.zip',buf.getvalue())})

            if path=='/api/save-document':
                with LOCK:saved=save_document(data,payload.get('kind'))
                return self.respond({'ok':True,'path':saved})
            if path=='/api/print':
                with LOCK:
                    token=secrets.token_urlsafe(24);PRINTS[token]=render(data,'print')
                    while len(PRINTS)>20:PRINTS.pop(next(iter(PRINTS)))
                return self.respond({'url':'/print?id='+token})
            if path=='/api/render':
                with LOCK:output=render(data,payload.get('mode','reading'))
                return self.respond(output,mime='application/pdf')
            if path=='/api/inspect':
                with LOCK:notes=inspect(data)
                return self.respond({'notes':notes})
            if path=='/api/design-previews':
                with LOCK:output=design_previews(data)
                return self.respond(output,mime='application/pdf')
            if path=='/api/save':
                with LOCK:
                    render(data)  # A saved edition must be printable without overflow.
                    name='bulletin-'+data['date']+'-'+re.sub(r'[^a-zA-Z0-9_-]','_',data['issue'])+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                    content=json.dumps(data,ensure_ascii=False,indent=2)
                    for file in (DATA/'current.json',DATA/(name+'.json')):
                        temp=file.with_suffix('.tmp');temp.write_text(content,encoding="utf-8");temp.chmod(0o600);temp.replace(file)
                    atomic_json(DATA/'draft.json',data)
                return self.respond({'ok':True,'name':name})
            if path=='/api/bundle':
                buffer=BytesIO()
                with LOCK,zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
                    for mode in ('reading','print','public'):archive.writestr(f'bulletin-{data["date"]}-{mode}.pdf',render(data,mode))
                    archive.writestr('bulletin-content.json',json.dumps(data,ensure_ascii=False,indent=2))
                return self.respond(buffer.getvalue(),mime='application/zip',filename='bulletin-'+data['date']+'.zip')
            return self.respond({'error':'기능을 찾을 수 없습니다.'},404)
        except (ValueError,KeyError,TypeError) as exc:return self.respond({'error':str(exc)},422)
        except PermissionError:return self.respond({'error':'문서 폴더에 저장할 권한이 없습니다. 운영체제의 폴더 접근 권한과 보안 프로그램 설정을 확인해 주세요.'},403)
        except Exception:return self.respond({'error':'저장 또는 PDF 생성에 실패했습니다. 실행창과 저장 공간을 확인해 주세요.'},500)

if __name__=='__main__':
    init_fonts()
    print(f'카리스 주보제작: http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
