# Kaggle 데이터 크롤링 + 데이터화 + 색인 + 검색 시스템 v0.2.0

Kaggle에서 제공하는 데이터셋을 크롤링해 데이터화하고, 의미 기반 검색 시스템을 구현.
이 사이드 프로젝트는 아마존 파인 푸드 리뷰에서 시작된 것이므로 TODO가 이어짐

## 주요 기능

1. Kaggle 데이터셋 자동 크롤링 및 다운로드
2. CSV 파일 데이터베이스 임포트
3. Elasticsearch를 이용한 데이터 색인 (구현 예정)
4. 의미 기반 검색 (구현 예정)

## 기술 스택

- Python 3.8+
- Anaconda 가상 환경
- SQLite3
- Selenium
- FastAPI
- pandas
- webdriver_manager

## 파일 구조

- `crawlingCsvFromKaggle.py`: Kaggle에서 데이터셋을 크롤링하고 다운로드하는 FastAPI 서버
- `importCsv.py`: CSV 파일을 SQLite 데이터베이스로 임포트
- `config.py`: 프로젝트 설정 파일 (git에서 제외됨)

## 설치 및 실행

1. Anaconda 가상 환경 생성 및 활성화:
   ```
   conda create -n kaggle_crawler python=3.8
   conda activate kaggle_crawler
   ```

2. 필요한 패키지 설치:
   ```
   pip install fastapi uvicorn selenium webdriver_manager pydantic
   ```

3. `config.py` 파일을 생성하고 필요한 설정을 추가해야 함.

4. Kaggle 데이터셋 크롤링 및 다운로드:
   ```
   python crawlingCsvFromKaggle.py
   ```

5. CSV 데이터 임포트:
   ```
   python importCsv.py <텍스트_파일_경로>
   ```

## 참고

- Kaggle 계정 정보가 필요함 (config.py에 설정)
- Chrome 웹 브라우저가 설치되어 있어야 함
- `config.py` 파일에는 민감한 정보가 포함될 수 있으므로 반드시 `.gitignore`에 추가하여 버전 관리에서 제외

## TODO

- Kaggle의 데이터를 크롤링해 색인하는 과정을 자동화로 구현(v0.2.x) [이 버전 이후로는 이 repository에 업로드]
    - ELK 스택 도입
        - Logstash: 애플리케이션 로그 및 메트릭 데이터 수집, 처리, 전송
        - Kibana: 데이터 시각화 및 모니터링    
- 웹서버를 열어 화면에서 색인 혹은 검색에 걸릴 항목을 사용자가 선택할 수 있도록 구현(v0.3.x)
    - 방향성 택 1
        - fastApi를 계속 사용하고 사이에 Java Spring기반 백엔드(브로커)를 둠
        - django로 바꿔서 백엔드 전체를 python으로 유지
    - 프론트엔드는 react
- 디자인 작업, 사용자 경험 개선 후 실제 사용자테스트 도입(v1.x.x)
    - CI/CD 파이프라인 구축 (Jenkins)
    - Docker 컨테이너화
    - Kubernetes를 이용한 배포 및 관리

- Kaggle뿐 아니라 크롤링가능한 사이트에 대한 자동화 구현(고도화)
	- 해당 자동화크롤링은 다른 사이드 프로젝트로 진행 후 추후 통합하기
