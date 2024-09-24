from fastapi import FastAPI
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
from googletrans import Translator

from config import ES_HOST, SENTENCE_TRANSFORMER_MODEL, ES_INDEX, API_HOST, API_PORT

app = FastAPI()

# Elasticsearch 클라이언트 생성
es = Elasticsearch([ES_HOST])

# 다국어 Sentence Transformer 모델 로드
model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

# Google 번역기 초기화
translator = Translator()

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search(request: SearchRequest):
    query = request.query
    
    # 쿼리를 영어로 번역
    translated_query = translator.translate(query, dest='en').text
    print(translated_query)
    query_embedding = model.encode(query).tolist()
    
    # TextBlob을 사용하여 번역된 쿼리의 감성 분석
    query_sentiment = TextBlob(translated_query).sentiment.polarity

    search_body = {
        "_source": {"excludes": ["embedding"]},
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": translated_query,
                            "fields": ["text^3", "summary^2"],
                            "fuzziness": "AUTO",
                            "minimum_should_match": "70%"
                        }
                    }
                ],
                "should": [
                    {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_embedding}
                            }
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "score": {
                                "gte": 0,
                                "lte": 5 if query_sentiment >= 0 else 2.5
                            }
                        }
                    }
                ]
            }
        },
        "min_score": 2.0
    }

    results = es.search(index=ES_INDEX, body=search_body)
    return results['hits']['hits']

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)