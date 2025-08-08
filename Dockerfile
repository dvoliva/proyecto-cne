#uso la imagen de python como base
#sistema operativo ligeron con python instalado
FROM python:3.12-slim

#establezco el entorno de trabajo
WORKDIR /app

#instalación de dependencias
#copio el archivo de requerimientos
COPY requirements.txt .
#instalo las dependendias
RUN pip install --no-cache-dir -r requirements.txt

#copio todo el código de mi proyecto
COPY ./src /app/src
# COPY .env /app/
# COPY database.db /app/  

#expongo el puerto 8000 para ejecutar la aplicación
EXPOSE 8000

#comando para ejecutar la aplicación
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
