# 使用官方 Python 映像作為基礎映像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製專案文件
COPY . /app/

# 安裝專案依賴
RUN pip install --no-cache-dir -r requirements.txt

# 設定容器啟動時執行的命令
CMD ["python", "你的主程式檔案.py"]