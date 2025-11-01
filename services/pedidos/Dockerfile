FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutar la aplicación con uvicorn en el puerto 8003 (coincide con docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
