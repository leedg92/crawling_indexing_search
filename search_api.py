from fastapi import FastAPI, Query
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
from googletrans import Translator

from config import ES_HOST, SENTENCE_TRANSFORMER_MODEL, API_HOST, SEARCH_API_PORT

app = FastAPI()

# Elasticsearch 클라이언트 생성
es = Elasticsearch([ES_HOST])

# 다국어 Sentence Transformer 모델 로드
model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

# Google 번역기 초기화
translator = Translator()

class SearchRequest(BaseModel):
    query: str
    index: str
    is_eng: str

@app.post("/search")
async def search(request: SearchRequest):
    query = request.query
    index = request.index
    is_eng = request.is_eng
    
    # 영어 번역 옵션이 켜져 있을 경우에만 번역
    if is_eng.upper() == 'Y':
        query = translator.translate(query, dest='en').text
        print(f"번역된 쿼리: {query}")

    
    query_embedding = model.encode(query).tolist()
    
    # TextBlob을 사용하여 쿼리의 감성 분석
    query_sentiment = TextBlob(query).sentiment.polarity

    # 인덱스의 매핑 정보를 가져와 텍스트 필드 추출
    mapping = es.indices.get_mapping(index=index)
    text_fields = [field for field, properties in mapping[index]['mappings']['properties'].items() 
                   if properties.get('type') == 'text']
    print(f"추출된 텍스트 필드: {text_fields}")

    search_body = {
        "_source": {"excludes": ["embedding"]},
        "query": {
            "multi_match": {
                "query": query,
                "fields": text_fields,
                "fuzziness": 2,  
                "minimum_should_match": "50%"  
            }
        }
    }

    
    

    results = es.search(index=index, body=search_body)
    print(f"검색 쿼리: {query}")
    print(f"검색 결과 수: {len(results['hits']['hits'])}")
    return results['hits']['hits']

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=SEARCH_API_PORT)