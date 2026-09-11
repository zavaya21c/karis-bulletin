"""Open an existing bulletin studio or start it once."""
import errno
import os
import webbrowser
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from server import Handler, PORT, init_fonts


def main():
    url = f'http://127.0.0.1:{PORT}/'
    try:
        server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        try:
            with urlopen(url, timeout=3) as response:
                page = response.read(100000).decode('utf-8')
            if 'KARIS BULLETIN' not in page or '카리스 주보제작' not in page:
                raise ValueError('다른 프로그램이 사용 중입니다.')
        except Exception:
            print(f'{PORT}번 주소를 다른 프로그램이 사용하고 있거나 응답하지 않습니다. 실행 중인 프로그램을 확인해 주세요.')
            return 1
        print('카리스 주보제작이 이미 실행 중입니다. 브라우저를 엽니다.', flush=True)
        if not os.getenv('BULLETIN_NO_BROWSER'): webbrowser.open(url)
        return 0
    try:
        init_fonts()
        print(f'카리스 주보제작: {url}', flush=True)
        print('브라우저에서 사용하세요. 이 창은 사용 중에 열어 두세요. 종료: Control+C', flush=True)
        if not os.getenv('BULLETIN_NO_BROWSER'): webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n카리스 주보제작을 종료했습니다.')
    finally:
        server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
