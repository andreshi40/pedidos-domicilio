from motor.motor_asyncio import AsyncIOMotorClient
import os

# Obtén la URL de la base de datos de las variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

# Crea el cliente de MongoDB
client = AsyncIOMotorClient(DATABASE_URL)

# Selecciona la base de datos
db = client.get_database()

# Función para obtener la colección
def get_collection(collection_name):
    return db[collection_name]
