
import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from modelos import Estacion, Precio, engine, crear_base_datos

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    Procesa y guarda los datos de las estaciones de forma masiva para
    un rendimiento óptimo, manejando duplicados en el origen.
    """
    if not estaciones_api:
        print("No hay estaciones para procesar.")
        return

    db = SessionLocal()
    print("Iniciando procesamiento masivo de datos...")

    try:
        print("1/4 - Obteniendo estaciones existentes desde la base de datos...")
        codigos_en_db = {estacion.codigo for estacion in db.query(Estacion.codigo).all()}
        print(f" -> Se encontraron {len(codigos_en_db)} estaciones en la BD.")

        print("2/4 - Preparando y depurando los datos para la carga masiva...")
        estaciones_a_crear = []
        estaciones_a_actualizar = []
        precios_a_crear = []
        
        #el set evita que procesemos códigos duplicados que vengan de la API.
        codigos_procesados_en_lote = set()

        for estacion_data in estaciones_api:
            codigo_estacion = estacion_data.get('codigo')

            #si ya hemos visto este código en este mismo lote, se ignora y continua
            if not codigo_estacion or codigo_estacion in codigos_procesados_en_lote:
                continue
            
            #marco el código como procesado para este lote
            codigos_procesados_en_lote.add(codigo_estacion)
            
            def convertir_coordenada(valor):
                if valor is None: return None
                try: return float(str(valor).replace(',', '.'))
                except (ValueError, TypeError): return None
            
            datos_limpios = {
                'codigo': codigo_estacion,
                'razon_social': estacion_data.get('razon_social'),
                'marca': estacion_data.get('distribuidor', {}).get('marca'),
                'direccion': estacion_data.get('ubicacion', {}).get('direccion'),
                'comuna': estacion_data.get('ubicacion', {}).get('nombre_comuna'),
                'region': estacion_data.get('ubicacion', {}).get('nombre_region'),
                'latitud': convertir_coordenada(estacion_data.get('ubicacion', {}).get('latitud')),
                'longitud': convertir_coordenada(estacion_data.get('ubicacion', {}).get('longitud'))
            }

            if codigo_estacion not in codigos_en_db:
                estaciones_a_crear.append(datos_limpios)
            else:
                estaciones_a_actualizar.append(datos_limpios)

            precios_data = estacion_data.get('precios', {})
            for tipo_comb, info_precio in precios_data.items():
                fecha_str = f'{info_precio.get("fecha_actualizacion")} {info_precio.get("hora_actualizacion")}'
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                precios_a_crear.append({
                    'tipo_combustible': tipo_comb,
                    'precio_valor': int(float(info_precio.get('precio', 0).replace(',', '.'))),
                    'fecha_actualizacion': fecha_obj,
                    'estacion_codigo': codigo_estacion
                })
        
        print(f" -> Datos depurados: {len(estaciones_a_crear)} estaciones nuevas, {len(estaciones_a_actualizar)} para actualizar.")

        if estaciones_a_actualizar:
            print("3/4 - Actualizando estaciones existentes y borrando precios antiguos...")
            codigos_a_actualizar = [est['codigo'] for est in estaciones_a_actualizar]
            db.query(Precio).filter(Precio.estacion_codigo.in_(codigos_a_actualizar)).delete(synchronize_session=False)
            db.bulk_update_mappings(Estacion, estaciones_a_actualizar)

        if estaciones_a_crear:
            print("3/4 - Insertando nuevas estaciones...")
            db.bulk_insert_mappings(Estacion, estaciones_a_crear)

        if precios_a_crear:
            print("4/4 - Insertando todos los registros de precios...")
            db.bulk_insert_mappings(Precio, precios_a_crear)

        print("Confirmando todos los cambios en la base de datos...")
        db.commit()
        print("\n¡Procesamiento masivo completado exitosamente!")
        print(f"- Estaciones nuevas: {len(estaciones_a_crear)}")
        print(f"- Estaciones actualizadas: {len(estaciones_a_actualizar)}")

    except Exception as e:
        print(f"\n Error durante el procesamiento masivo: {e}")
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
