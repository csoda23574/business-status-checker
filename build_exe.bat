@echo off
chcp 65001 > nul

echo Python 환경 설정 및 exe 파일 생성을 시작합니다...

:: requirements.txt 인코딩이 UTF-8인지 확인 후 설치
powershell -Command "(Get-Content requirements.txt) | Set-Content -Encoding UTF8 requirements.txt"
"C:\Python312\python.exe" -m pip install -r requirements.txt
"C:\Python312\python.exe" -m pip install pyinstaller

:: exe 파일 생성
"C:\Python312\python.exe" -m PyInstaller --onefile --noconsole --name "사업장 정보 조회" ^
  --hidden-import webdriver_manager.chrome ^
  --hidden-import selenium ^
  --add-data "C:\Users\korin\AppData\Roaming\Python\Python312\site-packages\selenium;selenium" ^
  --hidden-import PyQt6 ^
  business_checker.py

:: 실행 파일 정리
if exist "dist\사업장 정보 조회.exe" (
    copy "dist\사업장 정보 조회.exe" "사업장 정보 조회.exe"
    rmdir /s /q build
    rmdir /s /q dist
    del "사업장 정보 조회.spec"
    echo 실행 파일이 생성되었습니다: 사업장 정보 조회.exe
) else (
    echo 실행 파일 생성에 실패했습니다.
)

echo 완료되었습니다!
pause
