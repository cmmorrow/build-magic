# build-magic.nsi
#
# Build-magic Windows installer script
#
# This script will build a Windows installer for build-magic.

#---------------------------------

!define VERSION "0.5.1rc1"
Name "build-magic ${VERSION}"
OutFile "build-magic-${VERSION}_amd64_installer.exe"

RequestExecutionLevel admin

Unicode True

InstallDir $PROGRAMFILES\build-magic

SetCompressor lzma

InstallDirRegKey HKLM "Software\build-magic" "Install_Dir"

#---------------------------------

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

#---------------------------------

Section "build-magic"
  SetOutPath $INSTDIR
  File /r .\build-magic\build-magic\*.*

  WriteRegStr HKLM "Software\build-magic" "Install_Dir" "$INSTDIR"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\build-magic" "DisplayName" "build-magic"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\build-magic" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\build-magic" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\build-magic" "NoRepair" 1
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

#---------------------------------

# Uninstall

Section "Uninstall"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\build-magic"
  DeleteRegKey HKLM "Software\build-magic"

  Delete "$INSTDIR\*.*"

  RMDir /r "$INSTDIR\build-magic_${VERSION}"
  RMDir $INSTDIR

SectionEnd
