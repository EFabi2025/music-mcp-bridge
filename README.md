# Spotify MCP Server

Un servidor MCP (Model Context Protocol) para integrar Spotify con Claude AI, permitiendo búsqueda, reproducción y gestión de playlists directamente desde conversaciones.

## 🎵 Características

- **Autenticación OAuth 2.0** con Spotify
- **Búsqueda** de canciones y álbumes
- **Control de reproducción** (play/pause)
- **Gestión de playlists** (crear, obtener, agregar canciones)
- **Análisis de audio** (características técnicas de canciones)
- **Información de perfil** de usuario
- **Manejo robusto de errores** y logging

## 📋 Requisitos

- Python 3.10+
- Cuenta de Spotify (gratuita o premium)
- Aplicación registrada en Spotify Developer Dashboard

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd spotify-mcp-server
```

### 2. Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales de Spotify

#### a) Crear aplicación en Spotify
1. Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Haz clic en "Create App"
3. Completa los campos:
   - **App name**: Tu nombre preferido
   - **App description**: Descripción de tu aplicación
   - **Redirect URI**: `http://127.0.0.1:8888/callback`
4. Acepta los términos y crea la aplicación
5. Copia el **Client ID** y **Client Secret**

#### b) Configurar credenciales localmente
```bash
# Copia el archivo de ejemplo
cp spotify_credentials_example.py spotify_credentials.py

# Edita el archivo con tus credenciales
# SPOTIFY_CLIENT_ID = "tu_client_id_real"
# SPOTIFY_CLIENT_SECRET = "tu_client_secret_real"
```

## ⚙️ Configuración en Claude/Cursor

Agrega la siguiente configuración a tu archivo `mcp.json`:

```json
{
  "mcpServers": {
    "spotify-mcp": {
      "command": "/ruta/completa/al/proyecto/venv/bin/python",
      "args": [
        "/ruta/completa/al/proyecto/fixed_server.py"
      ]
    }
  }
}
```

## 🎯 Uso

### Autenticación
```python
# Iniciar sesión (abrirá navegador para autorización)
login()
```

### Búsqueda
```python
# Buscar canciones
search_track("Bohemian Rhapsody Queen", limit=5)

# Buscar álbumes
search_album("Dark Side of the Moon", limit=3)
```

### Reproducción
```python
# Reproducir canción (requiere Spotify Premium)
play("track_id_aqui")

# Pausar reproducción
pause()
```

### Playlists
```python
# Obtener tus playlists
get_user_playlists(limit=20)

# Crear nueva playlist
create_playlist("Mi Playlist", "Descripción opcional")

# Agregar canciones a playlist
add_tracks_to_playlist("playlist_id", ["track_id_1", "track_id_2"])
```

### Análisis
```python
# Obtener características de audio
get_audio_features("track_id")

# Obtener perfil de usuario
get_profile()
```

## 🔒 Seguridad

- ✅ Las credenciales se almacenan localmente
- ✅ Los tokens se manejan automáticamente
- ✅ Autenticación OAuth 2.0 estándar
- ❌ **NUNCA** compartas tu `spotify_credentials.py`
- ❌ **NUNCA** subas archivos `.spotify_token_cache`

## 🛠️ Desarrollo

### Estructura del proyecto
```
spotify-mcp-server/
├── fixed_server.py              # Servidor MCP principal
├── spotify_credentials_example.py # Plantilla de credenciales
├── requirements.txt             # Dependencias
├── README.md                   # Este archivo
├── .gitignore                  # Archivos ignorados por Git
└── logs/                       # Logs del servidor (ignorado)
```

### Logging
Los logs se guardan en `logs/spotify_mcp.log` y incluyen:
- Eventos de autenticación
- Errores de API
- Operaciones exitosas
- Información de debugging

## 🐛 Solución de problemas

### Error de autenticación
- Verifica que las credenciales sean correctas
- Confirma que la Redirect URI esté configurada como `http://127.0.0.1:8888/callback`
- Asegúrate de que el puerto 8888 esté disponible

### Error de reproducción
- La reproducción requiere Spotify Premium
- Verifica que tengas un dispositivo activo en Spotify

### Error de permisos
- Confirma que hayas autorizado todos los scopes necesarios
- Reautentica si es necesario con `login()`

## 📄 Licencia

Este proyecto es de código abierto. Úsalo responsablemente y respeta los términos de servicio de Spotify.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

---

**⚠️ Importante**: Este servidor es para uso personal y educativo. Respeta los límites de rate de la API de Spotify y sus términos de servicio. 