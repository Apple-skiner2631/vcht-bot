FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY vcht-bot.py .

ENV DISCORD_TOKEN=""

CMD ["python", "vcht-bot.py"]
