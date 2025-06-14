#!/usr/bin/env python3
"""
Fixed Spotify MCP Server
Un servidor MCP para Spotify con autenticación simplificada y token en memoria (Versión con URI fija)
"""

import os
import sys
import json
import threading
import webbrowser
import socket
import time
import base64
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler

# Redirigir prints a stderr para no interferir con el protocolo JSON
def log(message):
    print(message, file=sys.stderr)

# Importar credenciales
try:
    from spotify_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    log("Credenciales client_id y client_secret cargadas desde spotify_credentials.py")
except ImportError:
    log("Error: No se pudieron cargar las credenciales.")
    sys.exit(1)

# Definir URI de redirección explícitamente - esta URI debe estar registrada en el Dashboard de Spotify
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
log(f"Usando URI de redirección fija: {SPOTIFY_REDIRECT_URI}")

# Variables globales
spotify = None
token_info = None  # Almacenamos el token en memoria
auth_in_progress = False
auth_url = None
auth_code_received = threading.Event()
authorization_code = None

# Extraer información de la URI de redirección
try:
    redirect_uri_parts = urlparse(SPOTIFY_REDIRECT_URI)
    DEFAULT_PORT = int(redirect_uri_parts.port)
    CALLBACK_PATH = redirect_uri_parts.path
    HOST = redirect_uri_parts.hostname
    log(f"URI de redirección configurada: {SPOTIFY_REDIRECT_URI}")
    log(f"HOST: {HOST}, PORT: {DEFAULT_PORT}, PATH: {CALLBACK_PATH}")
except:
    log(f"Error al extraer información de {SPOTIFY_REDIRECT_URI}")
    DEFAULT_PORT = 8080
    CALLBACK_PATH = "/callback"
    HOST = "127.0.0.1"

# Handler para la autenticación OAuth
class AuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log(format % args)
    
    def do_GET(self):
        global authorization_code
        
        parsed_path = urlparse(self.path)
        log(f"Recibida solicitud en: {self.path}")
        
        # Verificar si es la ruta de callback
        if parsed_path.path == CALLBACK_PATH:
            query_params = parse_qs(parsed_path.query)
            log(f"Parámetros recibidos: {query_params}")
            
            if 'code' in query_params:
                authorization_code = query_params['code'][0]
                log(f"Código de autorización recibido: {authorization_code[:5]}...")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                # Respuesta HTML
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Autenticación Completada</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            margin-top: 50px;
                            background-color: #1DB954;
                            color: white;
                        }
                        .container {
                            max-width: 600px;
                            margin: 0 auto;
                            background-color: #191414;
                            padding: 30px;
                            border-radius: 10px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>¡Autenticación Completada!</h1>
                        <p>La autenticación con Spotify se ha completado correctamente.</p>
                        <p>Puedes cerrar esta ventana y volver a Claude.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
                
                # Señalizar que recibimos el código
                auth_code_received.set()
            else:
                if 'error' in query_params:
                    log(f"Error recibido: {query_params['error'][0]}")
                
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Error: No se recibio codigo de autorizacion")
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

# Clase personalizada para gestión de tokens sin archivos
class MemoryCacheHandler(CacheHandler):
    def __init__(self, token_info=None):
        self.token_info = token_info
        
    def get_cached_token(self):
        return self.token_info
    
    def save_token_to_cache(self, token_info):
        self.token_info = token_info
        return None

# Método para obtener token directamente sin usar la biblioteca spotipy
def get_token_directly(code):
    try:
        auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI
        }
        
        log(f"Solicitando token con code: {code[:5]}...")
        log(f"Usando redirect_uri: {SPOTIFY_REDIRECT_URI}")
        
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_info = response.json()
            log("Token obtenido correctamente con método directo")
            return token_info
        else:
            log(f"Error al obtener token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log(f"Excepción al obtener token: {str(e)}")
        return None

# Función para inicializar el cliente de Spotify
def initialize_spotify_client():
    global spotify, token_info
    
    # Si ya existe un cliente, devolverlo
    if spotify:
        return spotify
    
    # Si tenemos token en memoria, usarlo
    if token_info:
        try:
            # Crear manejador de autenticación con nuestro token en memoria
            scope = "user-read-private user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-modify-private playlist-modify-public user-follow-read user-follow-modify user-top-read user-read-recently-played user-library-read user-library-modify"
            
            # Usar siempre la misma URI que está definida globalmente
            log(f"Inicializando cliente con URI: {SPOTIFY_REDIRECT_URI}")
            
            # Crear auth manager con handler personalizado
            auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=scope,
                cache_handler=MemoryCacheHandler(token_info),
                open_browser=False
            )
            
            # Verificar si el token está expirado
            if auth_manager.is_token_expired(token_info):
                log("Token expirado, renovando...")
                try:
                    token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
                    log("Token renovado correctamente")
                except Exception as e:
                    log(f"Error al renovar token: {str(e)}")
                    token_info = None
                    return None
            
            # Crear cliente con el token válido
            spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            
            # Verificar que funciona
            try:
                user_info = spotify_client.me()
                log(f"Cliente verificado. Usuario: {user_info['display_name']}")
                spotify = spotify_client
                return spotify
            except Exception as e:
                log(f"Error al verificar cliente: {str(e)}")
                return None
        except Exception as e:
            log(f"Error al inicializar cliente: {str(e)}")
            return None
    
    # Si no tenemos token en memoria, devolver None
    return None

# Función para generar la URL de autorización directamente
def generate_auth_url():
    scope = "user-read-private user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-modify-private playlist-modify-public user-follow-read user-follow-modify user-top-read user-read-recently-played user-library-read user-library-modify"
    scope_encoded = quote(scope)
    
    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?client_id={SPOTIFY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={quote(SPOTIFY_REDIRECT_URI)}"
        f"&scope={scope_encoded}"
    )
    
    return auth_url

# Función para manejar el proceso de autenticación OAuth
def authenticate_user():
    global auth_in_progress, auth_url, authorization_code, spotify, token_info
    
    # Si ya está en curso, no iniciar otro proceso
    if auth_in_progress:
        return {
            "status": "in_progress",
            "message": "Ya hay un proceso de autenticación en curso. Revisa el navegador o usa login() nuevamente para ver la URL."
        }
    
    auth_in_progress = True
    auth_url = None
    authorization_code = None
    auth_code_received.clear()
    
    # Iniciar servidor HTTP para callback en puerto fijo
    try:
        server = HTTPServer((HOST, DEFAULT_PORT), AuthHandler)
        log(f"Servidor HTTP iniciado en {HOST}:{DEFAULT_PORT}")
    except Exception as e:
        log(f"Error al iniciar servidor HTTP: {str(e)}")
        auth_in_progress = False
        return {
            "status": "error",
            "message": f"No se pudo iniciar el servidor para autenticación: {str(e)}"
        }
    
    # Iniciar servidor en thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Generar URL de autorización directamente
    auth_url = generate_auth_url()
    log(f"URL de autorización generada: {auth_url}")
    
    # Abrir navegador
    try:
        webbrowser.open(auth_url)
        log("Navegador abierto con URL de autenticación")
    except:
        log("No se pudo abrir el navegador automáticamente")
    
    # Iniciar thread para esperar código de autorización
    def wait_for_auth():
        global auth_in_progress, spotify, token_info
        
        # Esperar por el código (timeout: 5 minutos)
        if auth_code_received.wait(300):
            try:
                # Intentar obtener el token directamente sin spotipy para más control
                new_token = get_token_directly(authorization_code)
                
                if not new_token:
                    log("No se pudo obtener token con método directo, intentando con spotipy")
                    # Intentar con spotipy como respaldo
                    auth_manager = SpotifyOAuth(
                        client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-read-private",
                        cache_handler=MemoryCacheHandler(),
                        open_browser=False
                    )
                    
                    new_token = auth_manager.get_access_token(authorization_code)
                
                # Guardar token en memoria
                token_info = new_token
                log("Token obtenido y guardado en memoria")
                
                # Inicializar cliente
                spotify = spotipy.Spotify(auth=token_info['access_token'])
                log("Cliente de Spotify inicializado correctamente")
                
                # Verificar que funciona
                try:
                    user_info = spotify.me()
                    log(f"Cliente verificado. Usuario: {user_info['display_name']}")
                except Exception as e:
                    log(f"Error al verificar cliente: {str(e)}")
                    spotify = None
            except Exception as e:
                log(f"Error durante autenticación: {str(e)}")
                spotify = None
        else:
            log("Timeout alcanzado esperando autenticación")
        
        # Detener servidor
        server.shutdown()
        auth_in_progress = False
    
    auth_thread = threading.Thread(target=wait_for_auth)
    auth_thread.daemon = True
    auth_thread.start()
    
    return {
        "status": "auth_started",
        "message": "Proceso de autenticación iniciado. Por favor, completa la autenticación en el navegador o copia la siguiente URL manualmente:\n" + auth_url,
        "auth_url": auth_url
    }

# Crear servidor MCP
mcp = FastMCP("Spotify MCP")

@mcp.tool()
def login() -> Dict[str, Any]:
    """
    Iniciar sesión en Spotify o verificar estado de autenticación.
    Si ya estás autenticado, simplemente lo confirma.
    Si no, inicia el proceso de autenticación automáticamente.
    """
    global spotify, token_info
    
    # Intentar usar cliente existente o inicializar desde token
    if not spotify:
        spotify = initialize_spotify_client()
    
    # Si ya tenemos cliente, confirmar autenticación
    if spotify:
        return {
            "status": "authenticated",
            "message": "Ya estás autenticado con Spotify."
        }
    
    # Si hay una autenticación en curso, informar al usuario
    if auth_in_progress:
        if auth_url:
            return {
                "status": "auth_in_progress",
                "message": "Proceso de autenticación en curso. Abre este enlace en tu navegador:",
                "auth_url": auth_url
            }
        else:
            return {
                "status": "auth_starting",
                "message": "Iniciando proceso de autenticación..."
            }
    
    # Iniciar nuevo proceso de autenticación (sin token existente)
    token_info = None
    return authenticate_user()

@mcp.tool()
def search_track(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Buscar canciones en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return [{"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}]
    
    # Realizar búsqueda
    try:
        results = spotify.search(q=query, type="track", limit=limit)
        tracks = results["tracks"]["items"]
        
        return [{
            "id": track["id"],
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],
            "preview_url": track["preview_url"]
        } for track in tracks]
    except Exception as e:
        log(f"Error al buscar canciones: {str(e)}")
        return [{"error": f"Error al buscar canciones: {str(e)}"}]

@mcp.tool()
def search_album(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Buscar álbumes en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return [{"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}]
    
    # Realizar búsqueda
    try:
        results = spotify.search(q=query, type="album", limit=limit)
        albums = results["albums"]["items"]
        
        return [{
            "id": album["id"],
            "name": album["name"],
            "artist": album["artists"][0]["name"],
            "release_date": album["release_date"],
            "total_tracks": album["total_tracks"],
            "images": album["images"]
        } for album in albums]
    except Exception as e:
        log(f"Error al buscar álbumes: {str(e)}")
        return [{"error": f"Error al buscar álbumes: {str(e)}"}]

@mcp.tool()
def play(track_id: str) -> Dict[str, Any]:
    """Reproducir una canción en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Iniciar reproducción
    try:
        spotify.start_playback(uris=[f"spotify:track:{track_id}"])
        return {"status": "success", "message": "Reproducción iniciada"}
    except Exception as e:
        log(f"Error al reproducir: {str(e)}")
        return {"status": "error", "message": f"Error al reproducir: {str(e)}"}

@mcp.tool()
def pause() -> Dict[str, Any]:
    """Pausar la reproducción actual en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Pausar reproducción
    try:
        spotify.pause_playback()
        return {"status": "success", "message": "Reproducción pausada"}
    except Exception as e:
        log(f"Error al pausar: {str(e)}")
        return {"status": "error", "message": f"Error al pausar: {str(e)}"}

@mcp.tool()
def create_playlist(name: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Crear una nueva playlist en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Crear playlist
    try:
        user_id = spotify.me()["id"]
        playlist = spotify.user_playlist_create(
            user=user_id,
            name=name,
            public=False,
            description=description
        )
        
        return {
            "id": playlist["id"],
            "name": playlist["name"],
            "description": playlist["description"],
            "url": playlist["external_urls"]["spotify"]
        }
    except Exception as e:
        log(f"Error al crear playlist: {str(e)}")
        return {"error": f"Error al crear playlist: {str(e)}"}

@mcp.tool()
def get_audio_features(track_id: str) -> Dict[str, Any]:
    """Obtener características de audio de una canción en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Obtener características
    try:
        features = spotify.audio_features(track_id)[0]
        
        return {
            "danceability": features["danceability"],
            "energy": features["energy"],
            "key": features["key"],
            "loudness": features["loudness"],
            "mode": features["mode"],
            "speechiness": features["speechiness"],
            "acousticness": features["acousticness"],
            "instrumentalness": features["instrumentalness"],
            "liveness": features["liveness"],
            "valence": features["valence"],
            "tempo": features["tempo"],
            "duration_ms": features["duration_ms"],
            "time_signature": features["time_signature"]
        }
    except Exception as e:
        log(f"Error al obtener características de audio: {str(e)}")
        return {"error": f"Error al obtener características de audio: {str(e)}"}

@mcp.tool()
def get_profile() -> Dict[str, Any]:
    """Obtener información del perfil de usuario en Spotify."""
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Obtener perfil
    try:
        user = spotify.me()
        
        return {
            "id": user["id"],
            "display_name": user["display_name"],
            "email": user.get("email", ""),
            "country": user.get("country", ""),
            "product": user["product"],
            "followers": user["followers"]["total"],
            "images": user["images"]
        }
    except Exception as e:
        log(f"Error al obtener perfil: {str(e)}")
        return {"error": f"Error al obtener perfil: {str(e)}"}

@mcp.tool()
def add_tracks_to_playlist(playlist_id: str, track_ids: List[str]) -> Dict[str, Any]:
    """
    Añadir canciones a una playlist existente en Spotify.
    
    Args:
        playlist_id: ID de la playlist a la que se añadirán las canciones
        track_ids: Lista de IDs de las canciones a añadir
        
    Returns:
        Información sobre el resultado de la operación
    """
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return {"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}
    
    # Verificar que hay tracks para añadir
    if not track_ids:
        return {"error": "No se proporcionaron IDs de canciones para añadir"}
    
    # Convertir IDs a formato URI de Spotify
    track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    log(f"Añadiendo {len(track_uris)} canciones a la playlist {playlist_id}")
    
    # Añadir tracks a la playlist
    try:
        result = spotify.playlist_add_items(playlist_id, track_uris)
        return {
            "status": "success",
            "message": f"Se añadieron {len(track_ids)} canciones a la playlist",
            "snapshot_id": result["snapshot_id"]
        }
    except Exception as e:
        log(f"Error al añadir canciones a playlist: {str(e)}")
        return {"error": f"Error al añadir canciones a playlist: {str(e)}"}

@mcp.tool()
def get_user_playlists(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Obtener las playlists del usuario actual.
    
    Args:
        limit: Número máximo de playlists a obtener
        
    Returns:
        Lista de playlists del usuario
    """
    global spotify
    
    # Verificar autenticación
    if not spotify:
        spotify = initialize_spotify_client()
        if not spotify:
            return [{"error": "No autenticado. Usa login() para iniciar sesión en Spotify."}]
    
    # Obtener playlists
    try:
        playlists = spotify.current_user_playlists(limit=limit)
        
        return [{
            "id": playlist["id"],
            "name": playlist["name"],
            "owner": playlist["owner"]["display_name"],
            "public": playlist["public"],
            "tracks_total": playlist["tracks"]["total"],
            "url": playlist["external_urls"]["spotify"]
        } for playlist in playlists["items"]]
    except Exception as e:
        log(f"Error al obtener playlists: {str(e)}")
        return [{"error": f"Error al obtener playlists: {str(e)}"}]

if __name__ == "__main__":
    log("Iniciando Spotify MCP Server (Versión Memoria)...")
    
    # Intentar inicializar cliente al inicio
    spotify = initialize_spotify_client()
    
    if spotify:
        log("Servidor iniciado con autenticación exitosa.")
    else:
        log("Servidor iniciado sin autenticación. Usa login() para autenticarte.")
    
    # Ejecutar servidor MCP
    mcp.run() 