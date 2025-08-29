# 베이스 이미지 (Python 3.11 + slim 이미지 권장)
FROM python:3.11-slim

# 환경 변수 설정 (불필요한 pyc, 버퍼링 해제 등)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성
WORKDIR /app

# 종속성 복사 및 설치 (requirements.txt)
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 소스 코드 복사
COPY . .

# 기본 실행 명령 (토큰 먼저 받고 main 실행)
# 실제 운영에서는 스케줄러에서 `main.py` 호출 권장
CMD ["python", "main.py"]
