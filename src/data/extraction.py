
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from modelos import Estacion, Precio, engine, crear_base_datos


load_dotenv() #carga las variables de entorno

#sessionmaker crea una fabrica de sesiones.
#cada vez que necesite comunicar con la base de datos,
#creo una nueva sesión a partir de esta fábrica.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


#funcion para obtener el token de acceso
def obtener_token():
    """
    Se conecta al endpoint de login https://api.cne.cl/api/login
    y obtiene el token de acceso.
    """
    #obtener las credenciales del entorno
    email = os.getenv('CNE_API_EMAIL')
    password = os.getenv('CNE_API_PASSWORD')
    login_url = "https://api.cne.cl/api/login"
    data = {
        "email": email,
        "password": password
    }

    try:
        # Realizar la solicitud POST al endpoint de login
        response = requests.post(login_url, json = data, timeout=10)
        #lanza un error si la respuesta no es 200 (éxito)
        response.raise_for_status()

        #extraer el token de la respuesta
        token = response.json().get('token') #obtener el valor de la clave 'token'
        print("token obtenido")
        return token
    
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el token: {e}")
        print(f"Status code: {response.status_code if 'response' in locals() else 'N/A'}")
        print(f"Response: {response.text if 'response' in locals() else 'N/A'}")
        return None

def obtener_estaciones(token: str):
    """
    usa el token de acceso para obtener el listado de las estaciones de servicio
    """
    if not token:
        print("No se proporcionó un token de acceso.")
        return None
    
    estaciones_url = "https://api.cne.cl/api/v4/estaciones"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print("obteniendo estaciones...")

    try:
        response = requests.get(estaciones_url, headers=headers, timeout=30)
        #lanza un error si la respuesta no es 200 (éxito)
        response.raise_for_status()

        #extraer los datos de la respuesta
        datos = response.json() 

        # Verificar si la respuesta es una lista o un diccionario
        if isinstance(datos, list):
            print(f"se encontraron {len(datos)} estaciones de servicio")
            return datos
        elif isinstance(datos, dict) and 'data' in datos:
            print(f"se encontraron {len(datos.get('data', []))} estaciones de servicio")
            return datos
        else:
            print(f"Formato inesperado de respuesta: {type(datos)}")
            return datos
    
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener las estaciones: {e}")
        return None

def procesar_y_guardar_datos(estaciones_api: list):
    """
    procesa la lista de estaciones de la API y las guarda en la base de datos
    """
    if not estaciones_api:
        print("No hay estaciones para procesar.")
        return
    
    #pedir una sesion a la fábrica de sesiones
    db = SessionLocal()
    print("Procesando y guardando estaciones...")

    try:
        total_estaciones = len(estaciones_api)
        estaciones_nuevas = 0
        estaciones_actualizadas = 0
        
        for i, estacion_data in enumerate(estaciones_api):
            #imprimir progreso
            print(f"procesando {i+1}/{total_estaciones}: {estacion_data.get('distribuidor', {}).get('marca')} - {estacion_data.get('ubicacion', {}).get('comuna')}...", end='\r')

            # Función para convertir coordenadas con manejo de comas ya que arrojaba error.
            def convertir_coordenada(valor):
                if valor is None:
                    return None
                try:
                    return float(str(valor).replace(',', '.'))
                except (ValueError, TypeError):
                    return None

            #verificar si la estacion ya existe
            codigo_estacion = estacion_data.get('codigo')
            estacion_existente = db.query(Estacion).filter(Estacion.codigo == codigo_estacion).first()

            if not estacion_existente:
                #si no existe, crear una nueva estación
                nueva_estacion = Estacion(
                    codigo=estacion_data.get('codigo'),
                    razon_social=estacion_data.get('razon_social'),
                    marca=estacion_data.get('distribuidor', {}).get('marca'),
                    direccion=estacion_data.get('ubicacion', {}).get('direccion'),
                    comuna=estacion_data.get('ubicacion', {}).get('nombre_comuna'),
                    region=estacion_data.get('ubicacion', {}).get('nombre_region'),
                    latitud=convertir_coordenada(estacion_data.get('ubicacion', {}).get('latitud')),
                    longitud=convertir_coordenada(estacion_data.get('ubicacion', {}).get('longitud'))
                )
                db.add(nueva_estacion)
                db.flush()  # Hacer flush para obtener el ID sin commit completo
                estacion_para_precios = nueva_estacion
                estaciones_nuevas += 1
            else:
                #si ya existe, se actualiza la estación
                estacion_existente.razon_social = estacion_data.get('razon_social')
                estacion_existente.marca = estacion_data.get('distribuidor', {}).get('marca')
                estacion_existente.direccion = estacion_data.get('ubicacion', {}).get('direccion')
                estacion_existente.comuna = estacion_data.get('ubicacion', {}).get('nombre_comuna')
                estacion_existente.region = estacion_data.get('ubicacion', {}).get('nombre_region')
                estacion_existente.latitud = convertir_coordenada(estacion_data.get('ubicacion', {}).get('latitud'))
                estacion_existente.longitud = convertir_coordenada(estacion_data.get('ubicacion', {}).get('longitud'))
                
                # Eliminar precios antiguos
                db.query(Precio).filter(Precio.estacion_codigo == codigo_estacion).delete()
                estacion_para_precios = estacion_existente
                estaciones_actualizadas += 1

            #procesamos los precios para la estación(nueva o existente)
            precios_data = estacion_data.get('precios', {})
            for tipo_comb, info_precio in precios_data.items():
                fecha_str = f'{info_precio.get("fecha_actualizacion")} {info_precio.get("hora_actualizacion")}'
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')

                nuevo_precio = Precio(
                    tipo_combustible=tipo_comb,
                    precio_valor=int(float(info_precio.get('precio',0).replace(',','.'))),
                    fecha_actualizacion=fecha_obj,
                    estacion = estacion_para_precios
                )
                db.add(nuevo_precio)

        #al final del bucle, se confirman los cambios a la vez
        db.commit()
        print(f"\nProcesamiento completado:")
        print(f"- Estaciones nuevas: {estaciones_nuevas}")
        print(f"- Estaciones actualizadas: {estaciones_actualizadas}")
        print(f"- Total procesadas: {total_estaciones}")
    except Exception as e:
        print(f"Error al procesar y guardar datos: {e}")
        db.rollback()
    finally:
        db.close()

#ejecución del script
if __name__ == "__main__":
    #este bloque se ejecuta si el script se corre directamente

    #1 crear la base de datos y las tablas
    crear_base_datos()

    #2 obtengo el token de acceso
    mi_token = obtener_token()

    #3 si obtengo el token, obtengo las estaciones
    if mi_token:
        lista_estaciones = obtener_estaciones(token=mi_token)

    #4 procesar y guardar los datos de las estaciones
    procesar_y_guardar_datos(lista_estaciones)
    #3 mostrar datos de ejemplo
        # if datos_estaciones:
        #     # Manejar tanto lista directa como diccionario con 'data'
        #     estaciones = datos_estaciones if isinstance(datos_estaciones, list) else datos_estaciones.get('data', [])
            
        #     if len(estaciones) > 0:
        #         print("\n--- Ejemplo de una estación ---")
        #         primera_estacion = estaciones[0]
        #         # Usar las claves correctas según la estructura real
        #         print(f"Código: {primera_estacion.get('codigo')}")
        #         print(f"Razón Social: {primera_estacion.get('razon_social')}")
        #         print(f"Distribuidor: {primera_estacion.get('distribuidor', {}).get('marca')}")
        #         print(f"Dirección: {primera_estacion.get('ubicacion', {}).get('direccion')}")
        #         print(f"Comuna: {primera_estacion.get('ubicacion', {}).get('nombre_comuna')}")
        #         print(f"Región: {primera_estacion.get('ubicacion', {}).get('nombre_region')}")
        #         print("-----------------------------\n")