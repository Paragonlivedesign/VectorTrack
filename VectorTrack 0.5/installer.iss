[Setup]
AppId={{2EA49297-639A-41B2-AE60-0F6A31C08A34}
AppName=VectorTrack
AppVersion=0.5.8
AppPublisher=Paragon Live Design
AppPublisherURL=https://paragonlivedesign.com
DefaultDirName={autopf}\Paragon Live Design\VectorTrack
DefaultGroupName=Paragon Live Design\VectorTrack
OutputDir=dist\installer
OutputBaseFilename=VectorTrack-0.5.8-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=assets\vectortrack.ico
UninstallDisplayIcon={app}\VectorTrack.exe

#ifndef AppSource
#define AppSource "release"
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\VectorTrack"; Filename: "{app}\VectorTrack.exe"; IconFilename: "{app}\VectorTrack.exe"
Name: "{commondesktop}\VectorTrack"; Filename: "{app}\VectorTrack.exe"; Tasks: desktopicon; IconFilename: "{app}\VectorTrack.exe"

[Run]
Filename: "{app}\VectorTrack.exe"; Description: "Launch VectorTrack"; Flags: nowait postinstall skipifsilent

[Code]
const
  DataPath = '{localappdata}\Paragon\VectorTrack';

var
  RemoveData: Boolean;

procedure InitializeUninstallProgressForm();
begin
  RemoveData := False;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if DirExists(ExpandConstant(DataPath)) then
    begin
      RemoveData :=
        (MsgBox(
          'Keep VectorTrack data (sessions, settings, and logs)?' + #13#10#13#10 +
          'Click Yes to KEEP your data, or No to remove it.',
          mbConfirmation,
          MB_YESNO
        ) = IDNO);
    end;
  end
  else if CurUninstallStep = usPostUninstall then
  begin
    if RemoveData and DirExists(ExpandConstant(DataPath)) then
      DelTree(ExpandConstant(DataPath), True, True, True);
  end;
end;
