from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service  # Service 추가
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager  # ChromeDriverManager 추가
import time
import os
import glob
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver

class BusinessCheckWorker(QThread):
    progress_updated = pyqtSignal(int, str, str)  # 진행상황, 상태메시지, 조회결과
    finished = pyqtSignal(list)  # 최종 결과
    error_occurred = pyqtSignal(str)  # 오류 메시지
    chrome_closed = pyqtSignal()  # Chrome 창 종료 감지 시그널

    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.is_paused = False
        self.is_running = True
        self.last_index = 0
        self.driver: Optional[WebDriver] = None
        self.results = []

    def init_driver(self) -> bool:  # 반환 타입을 bool로 변경
        try:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
                QThread.msleep(500)  # 이전 드라이버 완전 종료 대기

            options = webdriver.ChromeOptions()
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_experimental_option('detach', True)
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-logging')
            
            # 새로운 드라이버 인스턴스 생성
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            if self.driver is not None:
                self.driver.set_page_load_timeout(10)
                self.driver.get('about:blank')  # 먼저 빈 페이지 로드
                QThread.msleep(500)  # 초기화 대기
                self.driver.get('https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=43&tm2lIdx=4306000000&tm3lIdx=4306080000')
                QThread.msleep(1000)  # 홈택스 페이지 로딩 대기
                return True
            return False
                
        except Exception as e:
            self.error_occurred.emit(f"Chrome 드라이버 초기화 실패: {str(e)}")
            self.driver = None
            return False

    def check_driver_alive(self) -> bool:  # 반환 타입을 bool로 변경
        try:
            # Chrome 창 상태 확인
            if self.driver is None:
                return False
            current_url = self.driver.current_url
            return True
        except:
            return False

    def run(self):
        try:
            if not self.check_driver_alive():
                if not self.init_driver():
                    self.error_occurred.emit("Chrome 드라이버 초기화에 실패했습니다.")
                    return
            
            while self.is_running:
                # 일시정지 상태면 대기
                if self.is_paused:
                    QThread.msleep(100)
                    continue

                total_count = len(self.df)
                
                # 이미 모든 작업이 완료된 경우 종료
                if self.last_index >= total_count - 1:
                    self.finished.emit(self.results)
                    break
                
                # 메인 작업 루프
                for idx, row in enumerate(self.df.itertuples(), 1):
                    if idx <= self.last_index:
                        continue
                        
                    if not self.is_running or self.is_paused:
                        break

                    if not self.check_driver_alive():
                        self.last_index = idx - 1
                        self.progress_updated.emit(idx-1, row.현장명, "일시정지")
                        self.is_paused = True
                        self.chrome_closed.emit()
                        return  # run 메서드 종료

                    try:
                        business_number = str(row.사업장등록번호)
                        store_name = row.현장명
                        retry_count = 0
                        
                        while retry_count < 3 and self.is_running:
                            try:
                                if self.driver is None:
                                    raise Exception("Chrome 드라이버가 초기화되지 않았습니다.")
                                    
                                # 홈택스 페이지 로딩
                                url = 'https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=43&tm2lIdx=4306000000&tm3lIdx=4306080000'
                                try:
                                    self.driver.get(url)
                                except Exception:
                                    if not self.check_driver_alive():
                                        raise Exception("Chrome이 종료됨")
                                    raise
                                    
                                time.sleep(1.75)
                                
                                input_field = self.driver.find_element(By.ID, 'mf_txppWframe_bsno')
                                input_field.clear()
                                input_field.send_keys(business_number)
                                
                                search_button = self.driver.find_element(By.ID, 'mf_txppWframe_trigger5')
                                search_button.click()
                                
                                wait = WebDriverWait(self.driver, 10)
                                result = wait.until(EC.presence_of_element_located((By.ID, 'mf_txppWframe_grid2_cell_0_1')))
                                status = result.text
                                
                                self.results.append({
                                    '현장명': store_name,
                                    '사업장등록번호': business_number,
                                    '조회결과': status
                                })
                                
                                self.progress_updated.emit(idx, store_name, status)
                                time.sleep(1.75)
                                break
                                
                            except Exception as e:
                                if not self.check_driver_alive():
                                    raise Exception("Chrome이 종료됨")
                                retry_count += 1
                                if retry_count < 3:
                                    self.progress_updated.emit(idx, store_name, f"재시도 {retry_count}/3")
                                    time.sleep(2)
                                else:
                                    self.progress_updated.emit(idx, store_name, "조회 실패")
                                    self.results.append({
                                        '현장명': store_name,
                                        '사업장등록번호': business_number,
                                        '조회결과': '조회 실패'
                                    })
                        
                    except Exception as e:
                        if not self.check_driver_alive():
                            self.last_index = idx - 1
                            self.is_paused = True
                            self.chrome_closed.emit()
                            break

                if self.last_index >= total_count - 1:
                    if self.is_running:
                        self.finished.emit(self.results)
                    break

        except Exception as e:
            self.error_occurred.emit(f"조회 중 오류가 발생했습니다: {str(e)}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

    def pause(self):
        self.is_paused = True

    def resume(self):
        """일시 정지 상태에서 재개"""
        if not self.is_paused:
            return
            
        try:
            if not self.check_driver_alive():
                if not self.init_driver():
                    self.error_occurred.emit("Chrome 드라이버를 재시작할 수 없습니다.")
                    self.stop()
                    return
            
            self.is_paused = False
            if not self.isRunning():  # 스레드가 종료된 경우 다시 시작
                self.start()
                
        except Exception as e:
            self.error_occurred.emit(f"재개 중 오류 발생: {str(e)}")
            self.stop()

    def stop(self):
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        self.results = []  # 결과 초기화
        self.last_index = 0  # 인덱스 초기화

class BusinessChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("사업장 정보 조회")  # 윈도우 타이틀 변경
        self.setGeometry(100, 100, 600, 400)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # CSV 파일 선택 버튼
        self.csv_btn = QPushButton("CSV 파일 선택")
        self.csv_btn.clicked.connect(self.select_csv)
        layout.addWidget(self.csv_btn)
        
        # 파일 경로 표시 라벨
        self.file_label = QLabel("선택된 파일: 없음")
        layout.addWidget(self.file_label)
        
        # 진행상황 표시
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # 상태 메시지
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        self.status.setAcceptRichText(True)  # HTML 지원 활성화
        layout.addWidget(self.status)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("조회 시작")
        self.start_btn.clicked.connect(self.start_check)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        
        # 일시정지 버튼 추가
        self.pause_btn = QPushButton("일시정지")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        # 중지 버튼 추가
        self.stop_btn = QPushButton("중지")
        self.stop_btn.clicked.connect(self.stop_check)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.filter_btn = QPushButton("휴/폐업 필터링")
        self.filter_btn.clicked.connect(self.filter_results)
        self.filter_btn.setEnabled(False)
        button_layout.addWidget(self.filter_btn)
        
        self.clear_btn = QPushButton("파일 정리")
        self.clear_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(self.clear_btn)
        
        # 종료 버튼 추가
        self.exit_btn = QPushButton("종료")
        self.exit_btn.clicked.connect(self.force_quit)
        self.exit_btn.setStyleSheet("background-color: #ff6b6b;")
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
        
        # 데이터 저장용 변수
        self.df = None
        self.current_file = None
        
        # 상태 변수 추가
        self.is_paused = False
        self.last_index = 0  # 마지막으로 처리한 인덱스 저장
        self.worker = None  # worker는 start_check에서 초기화됨

    def toggle_pause(self):
        if not self.worker:
            return
            
        if self.worker.is_paused:
            self.status.append("조회를 재개합니다...")
            self.worker.resume()
            self.pause_btn.setText("일시정지")
        else:
            self.status.append("조회를 일시정지합니다...")
            self.worker.pause()
            self.pause_btn.setText("재개")

    def stop_check(self):
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker = None
        
        # 상태 초기화
        self.reset_state()
        
    def reset_state(self):
        self.df = None
        self.current_file = None
        self.last_index = 0
        self.is_paused = False
        
        # UI 초기화
        self.file_label.setText("선택된 파일: 없음")
        self.progress.setValue(0)
        self.status.clear()
        self.status.append("처리가 중지되었습니다. 새로운 CSV 파일을 선택해주세요.")
        
        # 버튼 상태 초기화
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.filter_btn.setEnabled(False)
        self.csv_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)

    def select_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, "CSV 파일 선택", "", "CSV Files (*.csv)")
        if filename:
            self.current_file = filename
            self.file_label.setText(f"선택된 파일: {os.path.basename(filename)}")
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.status.clear()
            self.status.append(f"CSV 파일이 선택되었습니다: {filename}")

    def start_check(self):
        try:
            if self.current_file is None:
                self.status.append("CSV 파일이 선택되지 않았습니다.")
                return

            self.df = pd.read_csv(self.current_file)
            self.progress.setMaximum(len(self.df))
            self.results = []  # 결과 초기화
            self.last_index = 0  # 인덱스 초기화
            
            # Worker 스레드 설정 및 시작
            self.worker = BusinessCheckWorker(self.df)
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.finished.connect(self.save_results)
            self.worker.error_occurred.connect(self.handle_error)
            self.worker.chrome_closed.connect(self.handle_chrome_closed)
            
            # UI 버튼 상태 변경
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.clear_btn.setEnabled(False)
            self.csv_btn.setEnabled(False)
            
            self.worker.start()
            
        except Exception as e:
            self.status.append(f"전체 오류 발생: {str(e)}")
            self.reset_state()

    def update_progress(self, index, store_name, status):
        self.progress.setValue(index)
        
        # HTML 스타일을 사용하여 색상 적용
        if "재시도" in status:
            self.status.append(f'<span style="color: red;">오류 발생</span>: {store_name} - 재시도 {status.split("/")[0][-1]}/3')
        elif status == "일시정지":  # 일시정지 상태일 때 처리 추가
            self.status.append(f'Chrome 종료 감지 - <span style="color: red;">일시정지</span>')
        else:
            if "조회 실패" in status:
                prefix = '<span style="color: red;">오류 발생</span>'
            else:
                prefix = '<span style="color: #0066ff;">조회 완료</span>'
            self.status.append(f"{prefix}: {store_name} - {status}")

    def save_results(self, results):
        results_df = pd.DataFrame(results)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_df.to_csv(f'business_status_{timestamp}.csv', index=False, encoding='utf-8-sig')
        
        # 통계 정보 계산
        if self.df is not None:  # None 체크 추가
            total_count = len(self.df)
            failed_count = len(results_df[results_df['조회결과'].str.contains('조회 실패', na=False)])
            success_count = total_count - failed_count
            closed_count = len(results_df[results_df['조회결과'].str.contains('휴업|폐업', na=False)])
            
            # 결과 표시
            self.status.append("\n=== 조회 결과 요약 ===")
            self.status.append(f"전체 사업장: {total_count}개")
            self.status.append(f"조회된 사업장: {success_count}개")
            self.status.append(f"조회되지 않은 사업장: {failed_count}개")
            self.status.append(f"휴/폐업 사업장: {closed_count}개")
            self.status.append("===================\n")
        
        self.filter_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.clear_btn.setEnabled(True)
        self.start_btn.setEnabled(True)

    def handle_error(self, error_message):
        self.status.append(error_message)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.clear_btn.setEnabled(True)
        self.start_btn.setEnabled(True)

    def filter_results(self):
        try:
            files = glob.glob('business_status_*.csv')
            latest_file = max(files, key=os.path.getctime)
            df = pd.read_csv(latest_file)
            
            closed_businesses = df[df['조회결과'].str.contains('휴업|폐업', na=False)]
            result = closed_businesses[['현장명', '사업장등록번호', '조회결과']]
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f'closed_businesses_{timestamp}.csv'
            result.to_csv(output_filename, index=False, encoding='utf-8-sig')
            
            # 통계 정보 업데이트
            total_count = len(df)
            failed_count = len(df[df['조회결과'].str.contains('조회 실패', na=False)])
            success_count = total_count - failed_count
            closed_count = len(result)
            
            self.status.append("\n=== 휴/폐업 필터링 결과 ===")
            self.status.append(f"전체 사업장: {total_count}개")
            self.status.append(f"조회된 사업장: {success_count}개")
            self.status.append(f"조회되지 않은 사업장: {failed_count}개")
            self.status.append(f"휴/폐업 사업장: {closed_count}개")
            self.status.append("===================\n")
            
            self.status.append(f"결과가 {output_filename}에 저장되었습니다.")
            
        except Exception as e:
            self.status.append(f"필터링 중 오류 발생: {str(e)}")

    def clear_files(self):
        try:
            patterns = ['business_status_*.csv', 'closed_businesses_*.csv']
            deleted_files = []
            
            for pattern in patterns:
                files = glob.glob(pattern)
                for file in files:
                    try:
                        os.remove(file)
                        deleted_files.append(file)
                    except Exception as e:
                        self.status.append(f"파일 {file} 삭제 실패: {str(e)}")
            
            if deleted_files:
                self.status.append("삭제된 파일 목록:")
                for file in deleted_files:
                    self.status.append(f"- {file}")
            else:
                self.status.append("삭제할 파일이 없습니다.")
                
        except Exception as e:
            self.status.append(f"파일 정리 중 오류 발생: {str(e)}")

    def handle_chrome_closed(self):
        """Chrome 창 종료 시 처리"""
        self.status.append('<span style="color: red;">Chrome 창이 종료되었습니다. 재개 버튼을 눌러 다시 시작하세요.</span>')
        self.pause_btn.setText("재개")
        
        # 작업이 진행 중일 때만 일시정지 처리
        if self.worker and self.worker.is_running:
            self.worker.is_paused = True
            self.worker.last_index = max(0, self.worker.last_index)  # 인덱스 보정
            
        # UI 버튼 상태 업데이트
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("재개")
        self.stop_btn.setEnabled(True)

    def force_quit(self):
        """앱의 모든 프로세스를 즉시 강제 종료"""
        try:
            if self.worker:
                # 워커가 실행 중이면 즉시 중지
                self.worker.is_running = False
                if self.worker.driver:
                    try:
                        # 메인 페이지로 이동하여 리소스 해제 촉진
                        self.worker.driver.get('about:blank')
                    except:
                        pass
                    finally:
                        # 드라이버 강제 종료
                        self.worker.driver.quit()
                # 워커 스레드 강제 종료
                self.worker.terminate()
                self.worker = None
        except:
            pass
        finally:
            # 앱 즉시 종료
            QApplication.exit(0)

    def closeEvent(self, event):
        """창 닫기 이벤트를 비동기로 처리"""
        event.ignore()  # 기본 종료 동작 무시
        QTimer.singleShot(0, self.force_quit)  # 비동기 종료

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BusinessChecker()
    window.show()
    sys.exit(app.exec())
