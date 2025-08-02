import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List

#importando el trabajo previo
from src.data.modelos import Estacion
from src.data.extraction import SessionLocal


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
@app.get("/comunas", response_model=List[str], tags=["Comunas"])
def obtener_comunas(db: Session = Depends(get_db)):
    """
    Obtiene una lista de todas las comunas disponibles en la base de datos.
    """
    comunas_query = db.query(Estacion.comuna).distinct().all()
    return [comuna[0] for comuna in comunas_query]