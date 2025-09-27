FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.0.1 torchvision==0.15.2
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "nobi_bot.py"]