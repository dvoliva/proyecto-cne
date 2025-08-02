import sys
import os
from datetime import datetime

# Asegurarse de que el directorio src esté en el path para importar los módulos correctamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

#importando el trabajo previo
from src.data.modelos import Estacion, Precio
from src.data.extraction import SessionLocal
from pydantic import BaseModel

# Definición de los modelos de respuesta utilizando Pydantic
class PrecioRespuesta(BaseModel):
    tipo_combustible: str
    precio_valor: float
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


#crear la aplicación FastAPI
app = FastAPI(
    title="API de Precios del Combustible en Chile",
    description="API para consultar precios de combustibles en estaciones de servicio en Chile.",
    version="1.0.0",
)

#dependencia para obtener la sesión de la base de datos
def get_db():
    """
    Dependencia para obtener una sesión de base de datos.
    Cierra la sesión al finalizar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#primer endpoint: pagina de inicio
@app.get("/", tags=["Inicio"])
def leer_inicio():
    return {"message": "Bienvenido a la API de Precios del Combustible en Chile. Usa /docs para ver la documentación."}

#segundo endpoint: obtener todas las comunas
@app.get("/api/comunas", response_model=List[str], tags=["Comunas"])
def obtener_comunas(db: Session = Depends(get_db)):
    """
    Obtiene una lista de todas las comunas disponibles en la base de datos.
    """
    comunas_query = db.query(Estacion.comuna).distinct().order_by(Estacion.comuna).all()
    return [comuna[0] for comuna in comunas_query]

#endpoint para obtener todas las estaciones de servicio por comuna
@app.get("/api/estaciones/comuna/{nombre_comuna}", response_model=List[EstacionBasicoRespuesta], tags=["Estaciones"])
def obtener_estaciones_por_comuna(nombre_comuna: str, db: Session = Depends(get_db)):
    """
    Obtiene una lista de estaciones de servicio en una comuna específica.
    """
    estaciones = db.query(Estacion).filter(Estacion.comuna == nombre_comuna).order_by(Estacion.marca).all()

    if not estaciones:
        raise HTTPException(status_code=404, detail="No se encontraron estaciones en esta comuna.")
    
    return estaciones

#endpoint para obtener detalles de una estación de servicio
@app.get("/api/estaciones/codigo/{codigo_estacion}", response_model=EstacionCompletoRespuesta, tags=["Estaciones"])
def obtener_estacion_por_codigo(codigo_estacion: str, db: Session = Depends(get_db)):
    """
    Obtiene los detalles de una estación de servicio por su código.
    """
    estacion = db.query(Estacion).filter(Estacion.codigo == codigo_estacion).first()

    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada.")

    return estacion
