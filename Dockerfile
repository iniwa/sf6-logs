FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared location: browsers installed as root must also be readable by UID 1000.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN python -m playwright install --with-deps chromium \
    && chmod -R a+rX /opt/playwright

COPY . .

RUN mkdir -p /app/data && chown -R 1000:1000 /app

EXPOSE 8510

ENV TZ=Asia/Tokyo

USER 1000:1000

CMD ["python", "app.py"]
