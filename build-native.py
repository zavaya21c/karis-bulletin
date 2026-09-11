"""Python 설치 없이 도는 실행판을 만듭니다.

만들려는 운영체제에서 직접 실행해야 합니다.
Windows에서 돌리면 Windows 실행판이, Mac에서 돌리면 Mac 실행판이 나옵니다.
(다른 운영체제용으로는 만들 수 없습니다. PyInstaller는 교차 빌드를 지원하지 않습니다.)

    python build-native.py

끝나면 dist/KarisBulletin 폴더와 KarisBulletin-<운영체제>.zip 이 생깁니다.
교회에 전달할 때는 **폴더 전체**(또는 그 ZIP)를 주세요. 실행 파일 하나만 복사하면 동작하지 않습니다.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEP = os.pathsep  # Windows 는 ';', Mac·Linux 는 ':' 를 씁니다. 이걸 틀리면 자료가 빠집니다.

DATA = [('static', 'static'), ('assets', 'assets'),
        ('sample.json', '.'), ('presets.json', '.'), ('distribution.json', '.'),
        ('LICENSE.txt', '.')]
HIDDEN = ['layouts', 'ornaments', 'designs', 'typography', 'custom_designs', 'app_paths', 'render', 'server']


def label():
    system = platform.system()
    if system == 'Windows':
        return 'Windows'
    if system == 'Darwin':
        return 'Mac-AppleSilicon' if platform.machine() == 'arm64' else 'Mac-Intel'
    return system or 'Unknown'


def main():
    for source, _ in DATA:
        if not (ROOT / source).exists():
            raise SystemExit(f'필요한 자료가 없습니다: {source} · 압축을 모두 풀었는지 확인해 주세요.')

    subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                           'pyinstaller==6.22.2', '-r', str(ROOT / 'requirements.txt')])

    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--name', 'KarisBulletin', '--onedir']
    for source, target in DATA:
        command += ['--add-data', f'{source}{SEP}{target}']
    for module in HIDDEN:
        command += ['--hidden-import', module]
    command.append('launch.py')
    subprocess.check_call(command, cwd=ROOT)

    folder = ROOT / 'dist' / 'KarisBulletin'
    if not folder.is_dir():
        raise SystemExit('빌드 결과 폴더를 찾지 못했습니다. 위의 오류 메시지를 확인해 주세요.')

    for extra in ('사용안내.md', '새로운기능.md', 'LICENSE.txt', '실행판-만들기.md'):
        if (ROOT / extra).exists():
            shutil.copy2(ROOT / extra, folder / extra)

    # 이름에 점이 들어가므로 with_suffix 를 쓰면 안 됩니다 ('2.0-Windows' 가 확장자로 잘립니다).
    base = ROOT / f'KarisBulletin-2.0-{label()}'
    archive = Path(str(base) + '.zip')
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(base), 'zip', root_dir=folder.parent, base_dir=folder.name)

    print()
    print('완성했습니다.')
    print(f'  폴더 : {folder}')
    print(f'  압축 : {archive}')
    print()
    print('전달하기 전에 그 컴퓨터에서 실행 → 미리보기 → PDF 저장 → 저장 폴더 열기까지 확인해 주세요.')
    print('실행 파일 하나만 복사하면 동작하지 않습니다. 폴더 전체를 주셔야 합니다.')


if __name__ == '__main__':
    main()
