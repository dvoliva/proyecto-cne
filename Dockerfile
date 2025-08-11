#uso la imagen de python como base
#sistema operativo ligeron con python instalado
FROM python:3.12-slim-bullseye

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Añadimos la llave GPG de Microsoft al llavero del sistema de forma segura.
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# Creamos la lista de fuentes apuntando a la llave que acabamos de añadir.
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# Actualizamos la lista de paquetes de nuevo y ahora instalamos el driver de SQL.
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*


#establezco el entorno de trabajo
WORKDIR /app

#instalación de dependencias
#copio el archivo de requerimientos
COPY requirements.txt .
#instalo las dependendias
RUN pip install --no-cache-dir -r requirements.txt

#copio todo el código de mi proyecto
COPY ./src /app/src

#expongo el puerto 8000 para ejecutar la aplicación
EXPOSE 8000

#comando para ejecutar la aplicación
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
