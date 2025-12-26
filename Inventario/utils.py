import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.conf import settings # <--- IMPORTANTE: Para encontrar la ruta correcta

# Si modificas los scopes, elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_google_calendar_event(summary, description):
    """
    Crea un evento en Google Calendar y retorna el link.
    """
    creds = None
    
    # RUTA DINÁMICA: Busca los archivos en la raíz del proyecto (donde está manage.py)
    token_path = os.path.join(settings.BASE_DIR, 'token.json')
    credentials_path = os.path.join(settings.BASE_DIR, 'credentials.json')

    # 1. Cargar Token si existe
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # 2. Si no hay credenciales válidas, loguearse
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refrescando token: {e}")
                # Si falla el refresh, forzamos nuevo login borrando el token viejo
                os.remove(token_path)
                creds = None
        
        if not creds:
            # Verificar si existe el archivo json original
            if not os.path.exists(credentials_path):
                print(f"ERROR CRÍTICO: No se encuentra el archivo en: {credentials_path}")
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                # Abre el navegador para que el usuario acepte permisos
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Error en el flujo de autenticación: {e}")
                return None
            
        # Guardar el token para la próxima vez
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Configuración del evento (1 hora de duración por defecto)
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Mexico_City', # Ajusta tu zona horaria si es necesario
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Mexico_City',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Evento creado: {event.get('htmlLink')}")
        return event.get('htmlLink')

    except Exception as e:
        print(f"Ocurrió un error al conectar con Google Calendar: {e}")
        return None