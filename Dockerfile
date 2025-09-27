FROM python:3.9
WORKDIR /app
RUN apt-get update && apt-get install -y poppler-utils
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "nobi_bot.py"]