FROM python:3.13-slim
WORKDIR /app
COPY servidor.py schema.sql ./
COPY public ./public
ENV PYTHONUNBUFFERED=1 HOSTED=1 DATA_DIR=/data
EXPOSE 5000
CMD ["python", "servidor.py"]
