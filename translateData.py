import csv
import sqlite3
import warnings
from googletrans import Translator

from config import DB_PATH, CSV_PATH

warnings.filterwarnings("ignore", category=FutureWarning)

# SQLite 데이터베이스 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 번역 및 업데이트
cursor.execute("SELECT ID, SUMMARY, TEXT FROM AMAZON_FINE_FOOD_REVIEWS WHERE SUMMARY_KOR = '' OR TEXT_KOR = ''")
rows = cursor.fetchall()

def translate():
    for idx, (id, summary, text) in enumerate(rows, 1):
        translator = Translator()
        summary_kor = translator.translate(summary, src='en', dest='ko').text
        text_kor = translator.translate(text, src='en', dest='ko').text
        
        cursor.execute('''
            UPDATE AMAZON_FINE_FOOD_REVIEWS
            SET SUMMARY_KOR = ?, TEXT_KOR = ?
            WHERE ID = ?
        ''', (summary_kor, text_kor, id))
        
        if idx % 50 == 0:
            conn.commit()
            print(f"{idx} 행 번역 완료")

    conn.commit()
    print("모든 데이터 번역 완료")

# 최초 초기화
max_retries = 3
attempt = 0

while attempt < max_retries:
    try:
        translate()
        break
    except Exception as e:
        attempt += 1
        print(f"번역 중 오류 발생: {e}. 재시도 {attempt}/{max_retries}")
        if attempt == max_retries:
            print("최대 재시도 횟수에 도달했습니다. 번역을 중단합니다.")
            break

# 연결 종료
conn.close()

print("데이터 가져오기 및 번역 완료")