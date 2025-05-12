FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製必要文件
COPY requirements.txt .
COPY packages.txt .
COPY . .

# 安裝 Python 依賴
RUN pip install gradio==3.50.2 --no-cache-dir -r requirements.txt

# 設置環境變數
ENV PYTHONUNBUFFERED=1

# 暴露 Gradio 端口
EXPOSE 7860

# 啟動命令
CMD ["python", "app.py"]
