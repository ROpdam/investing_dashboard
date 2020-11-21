FROM python:3.8
EXPOSE 8500
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD sh setup.sh && streamlit run app.py --server.port $PORT
