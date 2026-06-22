@echo off
REM Masaustune ikonlu 'Jarvis' kisayolu olusturur (Windows)
cd /d "%~dp0"
set "TARGET=%~dp0baslat.bat"
set "ICON=%~dp0assets\jarvis.ico"
set "LNK=%USERPROFILE%\Desktop\Jarvis.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%ICON%'; $s.Description='Jarvis sesli asistan'; $s.Save()"
echo.
echo Masaustune 'Jarvis' kisayolu olusturuldu. Artik oraya cift tiklayabilirsin.
pause
