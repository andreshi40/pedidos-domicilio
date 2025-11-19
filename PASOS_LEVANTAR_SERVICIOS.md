# Pasos para Levantar los Servicios

## Problema Detectado
Los contenedores Docker no están corriendo. Por eso la página no muestra restaurantes.

## Solución: Levantar la Stack Completa

### 1. Verificar que Docker está corriendo
```bash
# Verificar que el daemon de Docker está activo
docker info

# Si falla, inicia Docker Desktop o el servicio de Docker
# En WSL2/Linux:
sudo service docker start
```

### 2. Levantar todos los servicios
```bash
cd /home/andres/proyectos/pedidos-domicilio

# Crear archivo .env si no existe
[ -f .env ] || cp _env.example .env

# Levantar todos los contenedores
docker compose up -d --build
```

### 3. Verificar que los servicios están corriendo
```bash
# Ver estado de todos los contenedores
docker compose ps

# Deberías ver algo como:
# NAME                STATUS              PORTS
# api-gateway         running             0.0.0.0:8000->8000/tcp
# frontend            running             0.0.0.0:5000->5000/tcp
# authentication      running             0.0.0.0:8001->8001/tcp
# restaurantes-service running            0.0.0.0:8002->8002/tcp
# pedidos-service     running             0.0.0.0:8003->8003/tcp
# repartidores-service running            0.0.0.0:8004->8004/tcp
# ...más bases de datos
```

### 4. Esperar a que los servicios inicien completamente
```bash
# Los servicios tardan unos 20-30 segundos en estar listos
sleep 30

# Ver logs si hay problemas
docker compose logs --tail=50 frontend
docker compose logs --tail=50 api-gateway
docker compose logs --tail=50 restaurantes-service
```

### 5. Probar conectividad
```bash
# Ejecutar el script de diagnóstico
python3 test_connectivity.py

# O probar manualmente cada servicio
curl http://localhost:8000/health  # Gateway
curl http://localhost:8002/health  # Restaurantes
curl http://localhost:8002/api/v1/restaurantes?limit=3  # Lista de restaurantes
```

### 6. Abrir en el navegador
```
http://localhost:5000/
```

## Comandos Útiles

### Ver logs en tiempo real
```bash
docker compose logs -f frontend
docker compose logs -f api-gateway
docker compose logs -f restaurantes-service
```

### Reiniciar un servicio específico
```bash
docker compose restart frontend
docker compose restart api-gateway
```

### Detener todo
```bash
docker compose down
```

### Detener y eliminar volúmenes (reset completo)
```bash
docker compose down -v
```

## Troubleshooting

### Si el puerto 5000 está ocupado
```bash
# Ver qué proceso usa el puerto
lsof -i :5000
# O en Windows/WSL
netstat -ano | grep 5000

# Cambiar el puerto en docker-compose.yml si es necesario
```

### Si las bases de datos no inician
```bash
# Ver logs de las bases de datos
docker compose logs auth-db
docker compose logs restaurantes-db
docker compose logs pedidos-db

# A veces necesitan más tiempo. Espera 1 minuto y verifica de nuevo
```

### Si el frontend no puede conectar con el gateway
```bash
# Verificar que están en la misma red Docker
docker network ls
docker network inspect pedidos-domicilio_default

# Verificar variables de entorno del frontend
docker compose exec frontend env | grep API_GATEWAY
```
