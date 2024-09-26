import os
import time
import logging
from datetime import datetime, time as dt_time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import zipfile
import shutil
import urllib.request
import subprocess

from config import DOWNLOAD_PATH, KAGGLE_LOGIN_ID, KAGGLE_LOGIN_PW, API_HOST, CRAWLING_API_PORT

WAIT_TIME = 10  # 대기 시간 설정

app = FastAPI()

class SearchRequest(BaseModel):
    search_query: str
    dataset_count: int = 1

class WebAutomation:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        
        # 다운로드 속도 향상을 위한 옵션 추가
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        
        self.download_path = self.create_download_directory()
        
        # 다운로드 설정 변경
        prefs = {
            "download.default_directory": str(self.download_path),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # 성능 로깅 활성화
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        self.wait = WebDriverWait(self.driver, WAIT_TIME)

    def create_download_directory(self):
        base_path = Path(DOWNLOAD_PATH)
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path

    def login_to_kaggle(self):
        try:
            # Kaggle 로그인 페이지로 이동
            self.driver.get("https://www.kaggle.com/account/login?phase=emailSignIn&returnUrl=%2Fdatasets")
            
            # 이메일 입력
            email_input = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.send_keys(KAGGLE_LOGIN_ID)
            
            # 비밀번호 입력
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(KAGGLE_LOGIN_PW)
            
            # 로그인 버튼 클릭
            login_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            login_button.click()
            
            # 로그인 성공 확인 (avatar-image 요소가 있는지 확인)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='avatar-image']")))
            
            print("로그인 성공")
            return True
        except Exception as e:
            print(f"로그인 실패: {str(e)}")
            return False
        
    def search_and_downloadCSV(self, request):
        try:
            # 현재 날짜, 검색어, 갯수로 폴더 이름 생성
            folder_name = f"{datetime.now().strftime('%Y%m%d%H%M')}_{request.search_query}_{request.dataset_count}"
            download_path = self.download_path / folder_name
            download_path.mkdir(parents=True, exist_ok=True)

            # archive 폴더 생성
            archive_folder = download_path / 'archive'
            archive_folder.mkdir(parents=True, exist_ok=True)

            # 다운로드 경로 업데이트
            self.driver.execute_script(f"window.downloadPath = '{str(archive_folder)}'")
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(archive_folder)
            })

            # 1. 검색어 입력
            search_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search datasets']")))
            search_input.clear()
            search_input.send_keys(request.search_query)
            search_input.send_keys(Keys.RETURN)
            
            # 2. 필터 버튼 클릭
            filter_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@title='Filters' or @aria-label='Filters']")))
            filter_button.click()

            # 2-1. 필터 창 생길때까지 잠시 대기
            time.sleep(0.3)

            # 3. CSV 옵션 선택
            filter_modal = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='datasets-listing-filter-modal']")))
            csv_option = filter_modal.find_element(By.XPATH, ".//span[contains(text(), 'CSV')]")
            csv_option.click()
            
            # 4. Apply 버튼 클릭
            apply_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Apply']")))
            apply_button.click()
            
            # 5. 검색 결과 로딩 대기
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.MuiListItem-gutters.MuiListItem-divider")))
            
            # 데이터셋 선택 및 다운로드
            dataset_links = self.driver.find_elements(By.CSS_SELECTOR, "li.MuiListItem-gutters.MuiListItem-divider a[tabindex='0']")

            csv_file_paths = []

            # dataset_links의 길이가 요청한 dataset_count보다 적으면 예외 발생
            if len(dataset_links) < request.dataset_count:
                raise ValueError(f"요청한 데이터셋 개수({request.dataset_count})보다 적은 데이터셋이 발견되었습니다: {len(dataset_links)}개")

            for i in range(min(len(dataset_links), request.dataset_count)):
                try:
                    # i번째 데이터셋 링크 클릭
                    dataset_links[i].click()
                    
                    # 페이지 로딩 대기
                    self.wait.until(EC.presence_of_element_located((By.XPATH, "//i[text()='file_download']")))
                    time.sleep(0.5)
                    # 데이터셋 제목 가져오기
                    dataset_title = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
                    
                    # ZIP 파일 다운로드 경로
                    zip_path = archive_folder / 'archive.zip'
                    
                    # 다운로드 버튼 찾기 및 클릭
                    download_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]")))
                    download_button.click()
                    
                    # 다운로드 완료 대기 (타임아웃 없이)
                    while not zip_path.exists():
                        time.sleep(1)
                    
                    print(f"{i+1}번째 데이터셋 '{dataset_title}' 다운로드 완료")
                    
                    # ZIP 파일 압축 해제
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(archive_folder)
                    
                    # ZIP 파일 삭제
                    zip_path.unlink()
                    
                    # archive 폴더 이름 변경
                    new_folder_name = download_path / dataset_title
                    archive_folder.rename(new_folder_name)
                    print(f"'archive' 폴더를 '{dataset_title}'로 이름 변경했습니다.")
                    
                    # .csv 파일 경로 수집
                    for root, _, files in os.walk(new_folder_name):
                        for file in files:
                            if file.endswith('.csv'):
                                csv_file_paths.append(os.path.join(root, file))
                    
                    print(f"{i+1}번째 데이터셋 '{dataset_title}' 압축 해제 및 폴더 이름 변경 완료")
                    
                    # 검색 결과 페이지로 돌아가기
                    self.driver.back()
                    
                    # 검색 결과 페이지 로딩 대기
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.MuiListItem-gutters.MuiListItem-divider")))
                    
                    # 데이터셋 링크 목록 다시 가져오기 (페이지가 새로 로드되었으므로)
                    dataset_links = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.MuiListItem-gutters.MuiListItem-divider a[tabindex='0']")))
                
                except Exception as e:
                    print(f"{i+1}번째 데이터셋 다운로드 중 오류 발생: {str(e)}")
                    continue

            print(f"{min(request.dataset_count, len(dataset_links))}개의 데이터셋 다운로드 및 처리 완료")
            
            # crawling_done_list.txt 파일에 경로, 데이터셋 제목, CSV 파일 이름 저장
            with open(os.path.join(download_path, 'crawling_done_list.txt'), 'w') as f:
                for path in csv_file_paths:
                    csv_filename = os.path.basename(path)
                    table_name = f"{dataset_title}_{os.path.splitext(csv_filename)[0]}"
                    table_name = table_name.replace(' ', '_').upper()
                    f.write(f"{path}|{table_name}\n")

            print("crawling_done_list.txt 파일 생성 완료")

            # 브라우저 창 닫기
            self.driver.quit()
            
            return True
        except Exception as e:
            print(f"데이터셋 검색 및 다운로드 실패: {str(e)}")
            self.driver.quit()
            return False

@app.post("/crawl_kaggle")
async def crawl_kaggle(request: SearchRequest):
    if not request.search_query:
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")

    try:
        web_automation = WebAutomation()
        if web_automation.login_to_kaggle():
            if web_automation.search_and_downloadCSV(request):
                # 텍스트 파일 경로
                folder_name = f"{datetime.now().strftime('%Y%m%d%H%M')}_{request.search_query}_{request.dataset_count}"
                download_path = Path(DOWNLOAD_PATH) / folder_name
                crawling_done_list_path = os.path.join(download_path, 'crawling_done_list.txt')
                
                return {
                    "status": 200,
                    "message": f"{request.dataset_count}개의 데이터셋 다운로드 완료",
                    "crawling_done_list_path": str(crawling_done_list_path)
                }
            else:
                raise HTTPException(status_code=500, detail="데이터셋 검색 및 다운로드 실패")            
        else:
            raise HTTPException(status_code=401, detail="로그인 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=CRAWLING_API_PORT)
