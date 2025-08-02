
import os
import requests
from dotenv import load_dotenv

load_dotenv() #carga las variables de entorno

#funcion para obtener el token de acceso
def obtener_token():
    """
    Se conecta al endpoint de login https://api.cne.cl/api/login
    y obtiene el token de acceso.
    """
    email = os.getenv('CNE_API_EMAIL')
    password = os.getenv('CNE_API_PASSWORD')

    login_url = "https://api.cne.cl/api/login"
    data = {
        "email": email,
        "password": password
    }

    try:
        response = requests.post(login_url, json = data, timeout=10)
        #lanza un error si la respuesta no es 200 (éxito)
        response.raise_for_status()

        #extraer el token de la respuesta
        token = response.json().get('token')
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

        datos = response.json()
        # Verificar si es una lista directamente o un diccionario con 'data'
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

#ejecución del script
if __name__ == "__main__":
    #este bloque se ejecuta si el script se corre directamente

    #1 obtengo el token de acceso
    mi_token = obtener_token()

    #2 si obtengo el token, obtengo las estaciones
    if mi_token:
        datos_estaciones = obtener_estaciones(token=mi_token)

    #3 mostrar datos de ejemplo
        if datos_estaciones:
            # Manejar tanto lista directa como diccionario con 'data'
            estaciones = datos_estaciones if isinstance(datos_estaciones, list) else datos_estaciones.get('data', [])
            
            if len(estaciones) > 0:
                print("\n--- Ejemplo de una estación ---")
                primera_estacion = estaciones[0]
                # Usar las claves correctas según la estructura real
                print(f"Código: {primera_estacion.get('codigo')}")
                print(f"Razón Social: {primera_estacion.get('razon_social')}")
                print(f"Distribuidor: {primera_estacion.get('distribuidor', {}).get('marca')}")
                print(f"Dirección: {primera_estacion.get('ubicacion', {}).get('direccion')}")
                print(f"Comuna: {primera_estacion.get('ubicacion', {}).get('nombre_comuna')}")
                print(f"Región: {primera_estacion.get('ubicacion', {}).get('nombre_region')}")
                print("-----------------------------\n")