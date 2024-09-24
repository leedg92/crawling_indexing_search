# 필요한 프로그램:
# 1. Elasticsearch (http://localhost:9200에서 실행 중이어야 함)
# 2. SQLite (amazon_reviews.db 파일이 필요함)

# 필요한 라이브러리:
# pip install pandas elasticsearch sentence-transformers spacy fastapi pydantic textblob uvicorn
# python -m spacy download ko_core_news_sm

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import pandas as pd
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import spacy
from fastapi import FastAPI
import sqlite3
from pydantic import BaseModel
from textblob import TextBlob
import sys  
import time  
from elasticsearch.helpers import bulk

from config import DB_PATH, ES_HOST, SPACY_MODEL, SENTENCE_TRANSFORMER_MODEL

# SQLite 연결 설정
conn = sqlite3.connect(DB_PATH)

# Elasticsearch 클라이언트 생성 부분을 수정
try:
    es = Elasticsearch([ES_HOST])
    es.info()  # Elasticsearch 연결 테스트
except Exception as e:
    print(f"Elasticsearch 연결 오류: {e}")
    exit(1)

# spaCy 모델 로드
nlp = spacy.load(SPACY_MODEL)

# Sentence Transformer 모델 로드
model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

# FastAPI 앱 생성
app = FastAPI()

# 검색 요청을 위한 Pydantic 모델
class SearchRequest(BaseModel):
    query: str

def create_index():
    index_name = "amazon_reviews"
    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "review_id": {"type": "keyword"},
                "product_id": {"type": "keyword"},
                "review": {"type": "text"},
                "review_kor": {"type": "text"},
                "summary": {"type": "text"},
                "summary_kor": {"type": "text"},
                "score": {"type": "float"},  # score 필드 추가
                "star_rating": {"type": "integer"},
                "helpful_votes": {"type": "integer"},
                "total_votes": {"type": "integer"},
                "verified_purchase": {"type": "boolean"},
                "review_headline": {"type": "text"},
                "review_date": {"type": "date"},
                "embedding": {"type": "dense_vector", "dims": 512}
            }
        }
    }
    
    try:
        es.indices.create(index=index_name, body=settings)
        print(f"인덱스 '{index_name}' 생성.")
    except Exception as e:
        print(f"인덱스 생성 중 오류 발생: {e}")

from elasticsearch.helpers import bulk

def index_data():
    print("데이터 색인 시작...")
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(ID) FROM AMAZON_FINE_FOOD_REVIEWS")
    max_id = cursor.fetchone()[0]
    
    batch_size = 100
    total_indexed = 0

    start_time = time.time()

    for start_id in range(1, max_id + 1, batch_size):
        end_id = min(start_id + batch_size - 1, max_id)
        
        cursor.execute("""
            SELECT ID, TEXT, TEXT_KOR, SUMMARY, SUMMARY_KOR, SCORE
            FROM AMAZON_FINE_FOOD_REVIEWS   
            WHERE id BETWEEN ? AND ?
        """, (start_id, end_id))
        
        actions = []
        for id, text, text_kor, summary, summary_kor, score in cursor:
            full_text = text + " " + summary
            embedding = model.encode(full_text).tolist()
            
            actions.append({
                "_index": "amazon_reviews",
                "_id": id,
                "_source": {
                    "id": id,
                    "review": text,
                    "review_kor": text_kor,
                    "summary": summary,
                    "summary_kor": summary_kor,
                    "score": float(score),
                    "embedding": embedding
                }
            })
        
        if actions:
            try:
                success, failed = bulk(es, actions, request_timeout=300)
                if failed:
                    print(f'문서 색인 실패: {len(failed)} 건')
                total_indexed += success
                print(f"진행 상황: {total_indexed} / {max_id} 문서 색인 완료")
            except Exception as e:
                print(f"색인 중 오류 발생: {e}")
        else:
            print(f"ID 범위 {start_id}-{end_id}에 데이터가 없음.")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"데이터 색인 완료. 총 {total_indexed}개 문서 처리. 소요 시간: {elapsed_time:.2f}초")

def index_exists():
    return es.indices.exists(index="amazon_reviews")

def get_index_count():
    try:
        return es.count(index="amazon_reviews")['count']
    except Exception as e:
        print(f"인덱스 카운트 확인 오류: {e}")
        return 0

def delete_index():
    index_name = "amazon_reviews"
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            print(f"인덱스 '{index_name}' 삭제.")
        else:
            print(f"인덱스 '{index_name}'가 존재하지 않음.")
    except Exception as e:
        print(f"인덱스 삭제 중 오류 발생: {e}")

def main():
    print("색인 시작")
    try:
        if index_exists():
            delete_option = input("기존 인덱스 삭제 ? (y/n): ")
            if delete_option.lower() == 'y':
                delete_index()
                create_index()
                index_data()
            else:
                print("기존 인덱스 유지.")
        else:
            print("인덱스 없음. 새로 생성")
            create_index()
            index_data()

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        conn.close()  # 데이터베이스 연결 종료

if __name__ == "__main__":
    main()
