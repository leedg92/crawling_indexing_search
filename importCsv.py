import csv
import sqlite3
import warnings
import sys
from pathlib import Path

from config import DB_PATH

warnings.filterwarnings("ignore", category=FutureWarning)

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
    
    return {header: max(types) if "TEXT" in types else min(types) 
            for header, types in column_types.items()}

def import_csv_to_db(csv_path, table_name, conn, cursor):
    total_rows = 0
    column_types = infer_column_types(csv_path)

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)
        
        # 테이블 생성 쿼리
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
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
    print(f"{csv_path}: 총 {total_rows} 행의 데이터를 {table_name} 테이블 import.")

def main(txt_file_path):
    # SQLite 데이터베이스 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 텍스트 파일에서 CSV 파일 경로와 테이블 이름 읽기
    with open(txt_file_path, 'r', encoding='utf-8') as txtfile:
        lines = txtfile.read().splitlines()

    # 각 CSV 파일을 SQLite에 삽입
    for line in lines:
        csv_path, table_name = line.split('|')
        if Path(csv_path).is_file():
            import_csv_to_db(csv_path, table_name, conn, cursor)
        else:
            print(f"파일을 찾을 수 없습니다: {csv_path}")

    # 데이터베이스 연결 종료
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("사용법: python importCsv.py <텍스트_파일_경로>")
        sys.exit(1)
    
    txt_file_path = sys.argv[1]
    if not Path(txt_file_path).is_file():
        print(f"오류: {txt_file_path} 파일이 존재하지 않습니다.")
        sys.exit(1)
    
    main(txt_file_path)
