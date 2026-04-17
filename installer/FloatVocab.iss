[Setup]
AppId={{6D327A01-2A25-4B66-9C14-52E057C52D3D}
AppName=FloatVocab
AppVersion=1.0.0
AppPublisher=FloatVocab
DefaultDirName={autopf}\FloatVocab
DefaultGroupName=FloatVocab
UninstallDisplayIcon={app}\FloatVocab.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=..\dist\installer
OutputBaseFilename=FloatVocab-Setup

[Languages]
Name: "simplifiedchinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\FloatVocab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FloatVocab"; Filename: "{app}\FloatVocab.exe"
Name: "{autodesktop}\FloatVocab"; Filename: "{app}\FloatVocab.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FloatVocab.exe"; Description: "Launch FloatVocab"; Flags: nowait postinstall skipifsilent
