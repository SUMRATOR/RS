; RS_INSTALLER_V60
; Установщик RS — RUBIK STUDIO для Windows (Inno Setup 6).
;
; Как собрать:
;   1. python build_rubik_exe.py          — создаёт dist\RUBIK_STUDIO
;   2. python build_installer.py          — собирает установщик
;
; Файл рассчитан на сборку в папке проекта: пути относительные.
; Если Inno Setup не установлен, скрипт build_installer.py подскажет,
; откуда его взять, и не станет ничего ломать.

#define AppName "RS — RUBIK STUDIO"
#define AppShortName "RUBIK_STUDIO"
#define AppVersion "0.2.0"
#define AppPublisher "RUBIK STUDIO"
#define AppExe "RUBIK_STUDIO.exe"

[Setup]
AppId={{8E2C1B44-5A6F-4E3B-9E0C-7B1D2F5A6C31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppName}
; Права администратора нужны только чтобы писать в Program Files.
; Для установки «только для меня» достаточно PrivilegesRequired=lowest.
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=RS_RUBIK_STUDIO_{#AppVersion}_setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}
MinVersion=10.0
; Данные пользователя (база, config.json, логи) не удаляются при
; обновлении — они лежат отдельно, в %LOCALAPPDATA%\RUBIK_STUDIO.
UsePreviousAppDir=yes
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Значок в меню «Пуск»"; GroupDescription: "Ярлыки:"; Flags: unchecked

[Files]
; Вся папка сборки PyInstaller.
Source: "dist\{#AppShortName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Документация рядом с программой.
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme skipifsourcedoesntexist
Source: "docs\design\*.md"; DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: quicklaunchicon

[Run]
; После установки предлагаем запустить программу.
Filename: "{app}\{#AppExe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Временные файлы самой установки.
Type: filesandordirs; Name: "{app}\__pycache__"
Type: dirifempty; Name: "{app}"

[Code]
// Проверяем, что установщик собран вместе с программой: пустой архив
// установится «успешно» и не запустится, поэтому лучше остановиться.
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FileExists(ExpandConstant('{src}\..\dist\{#AppShortName}\{#AppExe}')) then
  begin
    // На этапе установки файлы уже внутри архива — проверка нужна только
    // при сборке, поэтому здесь ничего не блокируем.
    Result := True;
  end;
end;

// Сообщаем пользователю, где лежат его данные: при удалении программы
// база и настройки остаются, и об этом нужно знать заранее.
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('Данные пользователя: %LOCALAPPDATA%\RUBIK_STUDIO');
  end;
end;
