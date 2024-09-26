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
from fastapi import FastAPI, HTTPException, Request
import sqlite3
from pydantic import BaseModel
from textblob import TextBlob
import sys
import time
from elasticsearch.helpers import bulk
import uvicorn

from config import DB_PATH, ES_HOST, SPACY_MODEL, SENTENCE_TRANSFORMER_MODEL, API_HOST, INDEXING_API_PORT

# SQLite 연결 설정
conn = sqlite3.connect(DB_PATH)

# Elasticsearch 클라이언트 생성
try:
    es = Elasticsearch([ES_HOST])
    es.info()
except Exception as e:
    print(f"Elasticsearch 연결 오류: {e}")
    exit(1)

# spaCy 모델 로드
nlp = spacy.load(SPACY_MODEL)

# Sentence Transformer 모델 로드
model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

# FastAPI 앱 생성
app = FastAPI()

def get_table_schema(table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    schema = {}
    for column in columns:
        col_name = column[1]
        col_type = column[2].lower()
        
        if col_name == 'el_pri_key':
            continue
        
        if 'int' in col_type:
            es_type = 'integer'
        elif 'float' in col_type or 'real' in col_type:
            es_type = 'float'
        elif 'date' in col_type or 'time' in col_type:
            es_type = 'date'
        elif 'bool' in col_type:
            es_type = 'boolean'
        else:
            es_type = 'text'
        
        schema[col_name] = {"type": es_type}
    
    return schema

def create_index(table_name):
    index_name = f"{table_name.lower()}_index"  # 소문자로 변경
    schema = get_table_schema(table_name)
    
    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": schema
        }
    }
    
    try:
        es.indices.create(index=index_name, body=settings)
        print(f"인덱스 '{index_name}' 생성.")
    except Exception as e:
        print(f"인덱스 생성 중 오류 발생: {e}")

def get_last_indexed_id(table_name):
    index_name = f"{table_name}_index"
    try:
        result = es.search(index=index_name, body={
            "sort": [{"el_pri_key": "desc"}],
            "size": 1
        })
        if result['hits']['hits']:
            return result['hits']['hits'][0]['_source']['el_pri_key']
        return 0
    except Exception as e:
        print(f"마지막 색인 ID 조회 중 오류 발생: {e}")
        return 0

def index_data(table_name, start_id=1):
    print(f"{table_name} 테이블 데이터 색인 시작... (시작 ID: {start_id})")
    cursor = conn.cursor()
    cursor.execute(f"SELECT MAX(el_pri_key) FROM {table_name}")
    max_id = cursor.fetchone()[0]
    
    batch_size = 100
    total_indexed = 0

    start_time = time.time()

    for current_id in range(start_id, max_id + 1, batch_size):
        end_id = min(current_id + batch_size - 1, max_id)
        
        cursor.execute(f"SELECT * FROM {table_name} WHERE el_pri_key BETWEEN ? AND ?", (current_id, end_id))
        columns = [column[0] for column in cursor.description]
        
        actions = []
        for row in cursor.fetchall():
            doc = {columns[i]: row[i] for i in range(len(columns))}
            
            actions.append({
                "_index": f"{table_name.lower()}_index",  # 소문자로 변경
                "_id": str(row[0]),  # el_pri_key를 문자열로 변환
                "_source": doc
            })
        
        if actions:
            try:
                success, failed = bulk(es, actions, request_timeout=300)
                if failed:
                    print(f'문서 색인 실패: {len(failed)} 건')
                    for item in failed:
                        print(f"실패한 문서: {item}")  # 실패한 문서의 상세 정보 출력
                total_indexed += success
                print(f"진행 상황: {total_indexed} / {max_id - start_id + 1} 문서 색인 완료")
            except Exception as e:
                print(f"색인 중 오류 발생: {e}")
        else:
            print(f"ID 범위 {current_id}-{end_id}에 데이터가 없음.")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"데이터 색인 완료. 총 {total_indexed}개 문서 처리. 소요 시간: {elapsed_time:.2f}초")

def index_exists(table_name):
    return es.indices.exists(index=f"{table_name}_index")

def get_index_count(table_name):
    try:
        return es.count(index=f"{table_name}_index")['count']
    except Exception as e:
        print(f"인덱스 카운트 확인 오류: {e}")
        return 0

def delete_index(table_name):
    index_name = f"{table_name}_index"
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            print(f"인덱스 '{index_name}' 삭제.")
        else:
            print(f"인덱스 '{index_name}'가 존재하지 않음.")
    except Exception as e:
        print(f"인덱스 삭제 중 오류 발생: {e}")

@app.post("/index_table")
async def index_table(request: Request):
    try:
        data = await request.json()
        table_name = data.get("table_name")
        is_continue = data.get("is_continue", "N")
        
        if not table_name:
            raise HTTPException(status_code=400, detail="테이블 이름이 제공되지 않았습니다.")
        
        if is_continue.upper() == 'Y':
            if index_exists(table_name):
                last_indexed_id = get_last_indexed_id(table_name)
                create_index(table_name)
                index_data(table_name, start_id=last_indexed_id + 1)
            else:
                create_index(table_name)
                index_data(table_name)
        else:  # 'N' 또는 다른 값
            if index_exists(table_name):
                delete_index(table_name)
            create_index(table_name)
            index_data(table_name)
        
        return {"message": f"{table_name} 테이블 색인 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=INDEXING_API_PORT)
