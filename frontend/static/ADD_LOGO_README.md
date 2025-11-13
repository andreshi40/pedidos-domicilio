Por favor coloca la imagen que adjuntaste en este ticket como `logo.png` dentro de `frontend/static/`.

Instrucciones rápidas (desde la raiz del repo):

# 1) Copiar el fichero (si lo tienes localmente en tu máquina):
cp /ruta/al/archivo/adjunto.png frontend/static/logo.png

# 2) (opcional) reconstruir y reiniciar el servicio frontend con docker-compose:
# reconstruye la imagen y levanta el servicio en background
docker compose up -d --build frontend

# 3) (alternativa, sin rebuild): copiar directamente al contenedor en ejecución (no siempre disponible)
# encuentra el id/nombre del contenedor frontend con: docker compose ps
# luego copiar el archivo dentro del contenedor
docker cp frontend/static/logo.png $(docker compose ps -q frontend):/app/frontend/static/logo.png
# y reinicia el contenedor
docker compose restart frontend

Notas:
- Ya actualicé las plantillas `frontend/templates/base.html` y `frontend/templates/index.html` para apuntar a `logo.png`.
- Después de copiar la imagen, permite unos segundos y recarga el navegador; si ves una versión cacheada, fuerza recarga con Ctrl+F5.
- Si quieres que yo añada el archivo `logo.png` directamente al repo, confirma y subiré el PNG (necesito que confirmes que la imagen adjunta aquí es la que quieres usar).
