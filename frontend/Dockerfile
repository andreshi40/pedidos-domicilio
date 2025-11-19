FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de dependencias.
COPY requirements.txt .

# Instala las dependencias.
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de la aplicación (código, templates, estáticos).
COPY . .

# Exponemos el puerto en el que la aplicación Flask se ejecutará.
EXPOSE 5000

# Ejecutar directamente la app para evitar necesidad de FLASK_APP en entorno.
CMD ["python", "app.py"]
