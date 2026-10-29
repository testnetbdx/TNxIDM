@echo off
REM TNxIDM Windows build - run on Windows 10/11 with Python 3.12.
REM Creates dist\TNxIDM\TNxIDM.exe (onedir) and TNxIDM-PC-Windows-v1.0.zip
setlocal
python --version
pip install -r requirements.txt
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
pyinstaller --noconfirm --clean --onedir --windowed --name TNxIDM main.py
if not exist "dist\TNxIDM\TNxIDM.exe" (
  echo BUILD FAILED: dist\TNxIDM\TNxIDM.exe not found
  exit /b 1
)
powershell -Command "Compress-Archive -Path dist\TNxIDM -DestinationPath TNxIDM-PC-Windows-v1.0.zip -Force"
echo.
echo OK: TNxIDM-PC-Windows-v1.0.zip created
echo Self-test on Windows: dist\TNxIDM\TNxIDM.exe --self-test
endlocal
