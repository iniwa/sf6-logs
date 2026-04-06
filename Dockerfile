FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && chown -R 1000:1000 /app

EXPOSE 8510

ENV TZ=Asia/Tokyo

USER 1000:1000

CMD ["python", "app.py"]
