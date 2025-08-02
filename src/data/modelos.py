import os

from sqlalchemy import (create_engine, Column, Integer, String,
                        Float, DateTime, ForeignKey)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Configuración de la base de datos

#define la ubicación de la base de datos
DATABASE_URL = "sqlite:///./database.db"

#el motor que se usará para conectarse a la base de datos
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

#base declarativa que se usará para definir los modelos
Base = declarative_base()

#definir modelos (tablas)
class Estacion(Base):
    """
    modelo que representa una estación de servicio 
    en la base de datos
    """
    #nombre de la tabla
    __tablename__ = "estaciones"

    #columnas de la tabla
    # Columnas de la tabla
    codigo = Column(String, primary_key=True, index=True) # Usamos el código de la CNE como ID
    razon_social = Column(String)
    marca = Column(String, index=True)
    direccion = Column(String)
    comuna = Column(String, index=True)
    region = Column(String, index=True)
    latitud = Column(Float)
    longitud = Column(Float)

    #relacion: una estación puede tener muchos precios
    #'back_populates' conecta esta relacion con la de la tabla Precio
    #'cascade' asegura que al eliminar una estación, se eliminen sus precios asociados
    precios = relationship("Precio", back_populates="estacion", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Estacion(marca='{self.marca}', comuna='{self.comuna}')>"
    

class Precio(Base):
    """
    modelo que representa el precio de un tipo de combustible
    en una fecha específica para una estación.
    """
    __tablename__ = "precios"

    id = Column(Integer, primary_key=True, index=True) # ID propio autoincremental
    tipo_combustible = Column(String, index=True)
    precio_valor = Column(Integer)
    fecha_actualizacion = Column(DateTime)
    
    # Clave Foránea: Vincula este precio a una estación específica.
    estacion_codigo = Column(String, ForeignKey("estaciones.codigo"))
    
    # Relación inversa: Permite acceder al objeto Estacion desde un objeto Precio.
    estacion = relationship("Estacion", back_populates="precios")

    def __repr__(self):
        return f"<Precio(tipo='{self.tipo_combustible}', precio='{self.precio_valor}')>"

#funcion para crear la base de datos y las tablas
def crear_base_datos():
    """
    Crea la base de datos y las tablas si no existen.
    """
    Base.metadata.create_all(bind=engine)
    print("Base de datos y tablas creadas exitosamente.")


if __name__ == "__main__":
    #este bloque se ejecuta si el script se corre directamente
    crear_base_datos()
    print("Modelo de datos listo.")