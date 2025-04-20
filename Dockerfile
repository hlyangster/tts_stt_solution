FROM python:3.9-slim

# 更新系統套件並安裝安全更新
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露應用程式可能使用的埠
EXPOSE 5000

# 設定環境變數
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]