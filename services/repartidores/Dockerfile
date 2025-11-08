FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# TODO: Define el comando para ejecutar la aplicación.
# El puerto debe ser el mismo que se expondrá en docker-compose.yml.
# Reemplaza [nombre_del_servicio] con el nombre de tu archivo principal (ej. main.py)
# CMD ["uvicorn", "[nombre_del_servicio]:app", "--host", "0.0.0.0", "--port", "8000"]
