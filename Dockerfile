FROM python:3.13.2

WORKDIR /app 

COPY . .

RUN pip install -r requirements.txt


CMD ["python", "main.py"]