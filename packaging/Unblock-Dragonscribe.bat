@echo off
REM Windows tags files downloaded from a browser as "from the internet"
REM (Mark of the Web). That tag can carry over to every file in this folder
REM when the zip is extracted, and Windows will then refuse to load
REM Dragonscribe.exe's bundled DLLs ("Failed to load Python DLL ...
REM LoadLibrary: Access is denied").
REM
REM This removes that tag from everything in this folder. Run it once, then
REM launch Dragonscribe.exe normally.

powershell -NoLogo -NoProfile -Command "Get-ChildItem -LiteralPath '%~dp0' -Recurse | Unblock-File"

echo.
echo Done. You can now run Dragonscribe.exe.
pause
