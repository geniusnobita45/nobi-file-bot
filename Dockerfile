FROM python:3.9
WORKDIR /app
RUN apt-get update && apt-get install -y poppler-utils libgl1-mesa-glx libglib2.0-0
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "nobi_bot.py"]