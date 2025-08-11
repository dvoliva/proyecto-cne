import sys
import os
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from typing import List
from pydantic import BaseModel

# --- 1. CONFIGURACIÓN CENTRALIZADA DE LA BASE DE DATOS ---
# Cargar variables de entorno desde el archivo .env (para desarrollo local)
load_dotenv()

# Leer las credenciales de la base de datos desde el entorno
DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# construir la URL de conexión para Azure SQL
#si alguna de las variables de entorno no existe, esto fallará.
DATABASE_URL = (
    f"mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:1433/{DB_DATABASE}"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)

# Crear el motor de SQLAlchemy
engine = create_engine(DATABASE_URL)

# Crear una fábrica de sesiones que usaremos para comunicarnos con la BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importamos los modelos de la base de datos.
# Este truco asegura que Python encuentre la carpeta 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data.modelos import Estacion, Precio

# --- 2. MODELOS DE RESPUESTA (PYDANTIC) ---
class PrecioRespuesta(BaseModel):
    tipo_combustible: str
    precio_valor: int
    fecha_actualizacion: datetime

    class Config:
        orm_mode = True

class EstacionBasicoRespuesta(BaseModel):
    codigo: str
    marca: str
    direccion: str
    comuna: str

    class Config:
        orm_mode = True

class EstacionCompletoRespuesta(EstacionBasicoRespuesta):
    razon_social: str
    region: str
    latitud: float
    longitud: float
    precios: List[PrecioRespuesta] = []

    class Config:
        orm_mode = True

# --- 3. CREACIÓN DE LA APLICACIÓN Y DEPENDENCIAS ---
app = FastAPI(
    title="API de Precios de Combustibles en Chile",
    description="Consulta datos de estaciones de servicio y precios de combustibles en Chile.",
    version="1.0.0"
)

# Esta es la "llave mágica" que le pasamos a cada endpoint
# para que pueda hablar con la base de datos.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 4. ENDPOINTS DE LA API ---
# (El código de los endpoints no cambia, pero ahora usarán la nueva conexión a Azure)

@app.get("/", tags=["Inicio"])
def leer_inicio():
    """
    Página de bienvenida de la API.
    """
    return {"mensaje": "Bienvenido a la API de Combustibles. Ve a /docs para la documentación interactiva."}

@app.get("/api/comunas", response_model=List[str], tags=["Estaciones"])
def obtener_comunas(db: Session = Depends(get_db)):
    """
    Obtiene una lista única de todas las comunas con estaciones de servicio.
    """
    comunas_query = db.query(Estacion.comuna).distinct().order_by(Estacion.comuna).all()
    # Convertimos la lista de tuplas que nos da la BD a una lista simple de strings
    return [comuna[0] for comuna in comunas_query]

@app.get("/api/estaciones/comuna/{nombre_comuna}", response_model=List[EstacionBasicoRespuesta], tags=["Estaciones"])
def obtener_estaciones_por_comuna(nombre_comuna: str, db: Session = Depends(get_db)):
    """
    Obtiene una lista de estaciones de servicio para una comuna específica.
    """
    estaciones = db.query(Estacion).filter(Estacion.comuna == nombre_comuna).order_by(Estacion.marca).all()
    if not estaciones:
        raise HTTPException(status_code=404, detail=f"No se encontraron estaciones para la comuna: {nombre_comuna}")
    return estaciones

@app.get("/api/estaciones/codigo/{codigo_estacion}", response_model=EstacionCompletoRespuesta, tags=["Estaciones"])
def obtener_estacion_por_codigo(codigo_estacion: str, db: Session = Depends(get_db)):
    """
    Obtiene la información detallada y los precios de una estación específica por su código.
    """
    estacion = db.query(Estacion).filter(Estacion.codigo == codigo_estacion).first()
    if not estacion:
        raise HTTPException(status_code=404, detail=f"No se encontró la estación con el código: {codigo_estacion}")
    return estacion
