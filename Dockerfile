FROM python:3.11-slim

# ffmpeg install
RUN apt-get update && apt-get install -y ffmpeg

# app setup
WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
