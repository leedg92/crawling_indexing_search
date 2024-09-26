import csv
import sqlite3
import warnings
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import DB_PATH, API_HOST, IMPORT_API_PORT

warnings.filterwarnings("ignore", category=FutureWarning)

app = FastAPI()

#컬럼 추론
def guess_type(value):
    try:
        int(value)
        return "INTEGER"
    except ValueError:
        try:
            float(value)
            return "REAL"
        except ValueError:
            return "TEXT"
        
# 샘플 1000개 데이터 분석
def infer_column_types(csv_path, sample_size=1000):
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)
        column_types = {header: set() for header in headers}
        
        for _ in range(sample_size):
            try:
                row = next(csvreader)
                for header, value in zip(headers, row):
                    column_types[header].add(guess_type(value))
            except StopIteration:
                break
    
    return {header: max(types) if "TEXT" in types else min(types) for header, types in column_types.items()}

def import_csv_to_db(csv_path, table_name, conn, cursor):
    total_rows = 0
    column_types = infer_column_types(csv_path)

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)
        
        # 테이블 생성 쿼리 
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            el_pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join([f"{header} {column_types[header]}" for header in headers])}
        )
        '''
        cursor.execute(create_table_query)

        # 데이터 삽입
        placeholders = ', '.join(['?' for _ in headers])
        insert_query = f'''
            INSERT INTO {table_name} 
            ({', '.join(headers)})
            VALUES ({placeholders})
        '''
        
        for row in csvreader:
            cursor.execute(insert_query, row)
            
            total_rows += 1
            if total_rows % 1000 == 0:
                conn.commit()
                print(f"{total_rows} 행 삽입 완료")

    conn.commit()
    print(f"{csv_path}: 총 {total_rows} 행의 데이터를 {table_name} 테이블에 import.")

class ImportRequest(BaseModel):
    txt_file_path: str

def process_csv_files(txt_file_path: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(txt_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            csv_path, table_name = line.strip().split(',')
            if Path(csv_path).is_file():
                import_csv_to_db(csv_path, table_name, conn, cursor)
            else:
                print(f"파일을 찾을 수 없습니다: {csv_path}")

    conn.close()

@app.post("/import_csv")
async def import_csv_api(request: ImportRequest):
    if not request.txt_file_path:
        raise HTTPException(status_code=400, detail="txt_file_path가 제공되지 않았습니다.")

    try:
        process_csv_files(request.txt_file_path)
        return {"message": "CSV 파일 가져오기가 완료되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=IMPORT_API_PORT)
