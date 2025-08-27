import sqlite3

# 원본과 대상 DB 연결
src = sqlite3.connect("trade_amount.sqlite3")
dst = sqlite3.connect("trade_amount.db")

# 커서 생성
src_cur = src.cursor()
dst_cur = dst.cursor()

# 원본 DB의 모든 테이블 이름 가져오기
src_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in src_cur.fetchall()]

for table in tables:
    # 1. 테이블 생성 SQL 가져오기
    src_cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
    create_sql = src_cur.fetchone()[0]

    # 2. 대상 DB에 동일 테이블 생성 (이미 존재하면 무시)
    try:
        dst_cur.execute(create_sql)
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 스킵

    # 3. 데이터 복사
    src_cur.execute(f"SELECT * FROM '{table}';")
    rows = src_cur.fetchall()

    if rows:
        placeholders = ",".join("?" * len(rows[0]))
        dst_cur.executemany(f"INSERT INTO '{table}' VALUES ({placeholders})", rows)

# 커밋 및 종료
dst.commit()
src.close()
dst.close()

print("모든 테이블을 trade_amount.db로 옮겼습니다.")
