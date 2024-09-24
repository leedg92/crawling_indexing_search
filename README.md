# 아마존 파인 푸드 리뷰 데이터 처리 및 검색 시스템 v0.1.0

Kaggle에서 제공하는 아마존 파인 푸드 리뷰 데이터셋을 처리하고, 의미 기반 검색 시스템을 구현.

## 주요 기능

1. CSV 파일 데이터베이스 임포트
2. 리뷰 텍스트 번역 (영어 -> 한국어)
3. Elasticsearch를 이용한 데이터 색인
4. 의미 기반 검색 (한글 쿼리의 경우 영어로 번역 후 검색)

## 기술 스택

- Python 3.8+
- Anaconda 가상 환경
- SQLite3
- Elasticsearch 7.x
- FastAPI
- Sentence Transformers
- Google Translate API (googletrans)
- TextBlob
- pandas
- numpy
- scikit-learn

## 파일 구조

- `importCsv.py`: CSV 파일을 SQLite 데이터베이스로 임포트
- `translateData.py`: 데이터베이스의 영어 리뷰를 한국어로 번역 후 업데이트
- `indexingData.py`: 데이터를 Elasticsearch에 색인
- `search_api.py`: FastAPI 기반의 검색 API 서버
- `config.py`: 프로젝트 설정 파일 (git에서 제외됨)
- `requirements.txt`: 필요한 Python 패키지 목록

## 설치 및 실행

1. Anaconda 가상 환경 생성 및 활성화:
   ```
   conda create -n amazon_review python=3.8
   conda activate amazon_review
   ```

2. 필요한 패키지 설치:
   ```
   pip install -r requirements.txt
   ```

3. `config.py` 파일을 생성하고 필요한 설정을 추가해야함.

4. CSV 데이터 임포트:
   ```
   python importCsv.py
   ```

5. 데이터 번역:
   ```
   python translateData.py
   ```

6. Elasticsearch 색인:
   ```
   python indexingData.py
   ```

7. 검색 API 서버 실행:
   ```
   python search_api.py
   ```

## 참고

- Google Translate API의 사용 제한이 있음.
- Elasticsearch 서버가 실행 중이어야 함.
- `config.py` 파일에는 민감한 정보가 포함될 수 있으므로 반드시 `.gitignore`에 추가하여 버전 관리에서 제외.

## TODO

- 로컬 번역 라이브러리를 활용해 제한이 없게 실행(argostranslate 등)
    - 쿼리를 영어로 번역한다면 검색에 크게 문제는 없지만, 왠지 결과를 한글로 보고싶음.
- 번역의 품질 파인튜닝(가능유무는 아직 판단안됨)
- Kaggle의 데이터를 크롤링해 색인하는 과정을 자동화로 구현(v0.2.x) [이 버전 이후로는 repository를 새로 생성]
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
