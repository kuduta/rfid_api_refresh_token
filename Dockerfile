FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ติดตั้ง sqlite3 ไว้ใน container เพื่อให้เช็คไฟล์ users.db ได้
RUN apt update && apt install -y sqlite3

#ติดตั้ง eventlet เพื่อรองรับ Socket.IO
RUN pip install --no-cache-dir eventlet

COPY . .

CMD ["python", "app.py"]