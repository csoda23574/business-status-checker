# 사업장 정보 조회 프로그램

홈택스 사이트를 통해 사업장의 운영 상태(휴/폐업)를 일괄 조회하는 프로그램입니다.

## 기능

- CSV 파일에서 사업자등록번호 일괄 조회
- 일시정지/재개 기능
- 자동 Chrome 창 복구
- 휴/폐업 업체 필터링
- 조회 결과 CSV 저장

## 사용 방법

1. CSV 파일 선택 (사업장등록번호, 현장명 컬럼 필요)
2. 조회 시작
3. 결과 확인 및 휴/폐업 필터링

## 요구사항

- Python 3.12
- Chrome 브라우저

## 설치 방법

```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
python business_checker.py
```

또는 배치 파일을 통해 실행 파일 생성:
```bash
build_exe.bat
```
