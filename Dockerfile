FROM python:3.8

LABEL maintainer "Robin Opdam"

WORKDIR /app

COPY . .
RUN pip install -r /requirements.txt

EXPOSE 8050

CMD ["python", "./app.py"]
