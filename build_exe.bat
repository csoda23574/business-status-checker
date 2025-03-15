@echo off
chcp 65001
echo Python 환경 설정 및 exe 파일 생성을 시작합니다...

:: Python 전체 경로로 pip 명령어 실행
"C:\Python312\python.exe" -m pip install -r requirements.txt
"C:\Python312\python.exe" -m pip install pyinstaller

:: exe 파일 생성 (Python -m pyinstaller 사용)
"C:\Python312\python.exe" -m PyInstaller --onefile --noconsole --name "사업장 정보 조회" ^
  --hidden-import webdriver_manager.chrome ^
  --hidden-import selenium ^
  --add-data "C:\Users\korin\AppData\Roaming\Python\Python312\site-packages\selenium;selenium" ^
  --hidden-import PyQt6 ^
  business_checker.py

:: 실행 파일 이동 및 정리
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
