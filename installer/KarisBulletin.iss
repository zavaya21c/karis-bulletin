; 카리스 주보제작 Windows 설치 파일 스크립트 (Inno Setup 6 이상)
;
; 쓰는 순서
;   1. 먼저 상위 폴더에서  python build-native.py  를 실행해 dist\KarisBulletin 를 만듭니다.
;   2. Inno Setup(무료, jrsoftware.org)으로 이 파일을 열고 Build → Compile 을 누릅니다.
;   3. installer\Output\KarisBulletin-2.0-설치.exe 가 만들어집니다.

#define AppName "카리스 주보제작"
#define AppVersion "2.0.0"
#define AppExe "KarisBulletin.exe"

[Setup]
AppId={{7B2C4E10-9A31-4C77-9E2D-0B5A6D3F1C88}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\KarisBulletin
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=카리스주보제작-{#AppVersion}-설치
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

; 설치 첫 화면에 이용 조건을 보여 줍니다.
[Setup]
LicenseFile=..\LICENSE.txt

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
; dist\KarisBulletin 폴더 전체를 그대로 담습니다.
Source: "..\dist\KarisBulletin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\사용안내.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\새로운기능.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\사용안내"; Filename: "{app}\사용안내.md"
Name: "{group}\{#AppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "지금 카리스 주보제작 실행"; Flags: nowait postinstall skipifsilent

[Messages]
korean.WelcomeLabel2=이 프로그램은 교회 주보를 만드는 도구입니다.%n인터넷에 올리지 않고 이 컴퓨터 안에서만 동작합니다.%n%n편집 자료는 프로그램을 지워도 남습니다.
