FROM python:3.11-slim

WORKDIR /app

# Create data directory for Railway volume
RUN mkdir -p /app/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Create volume mount point
VOLUME /app/data

CMD ["python", "bot.py"]