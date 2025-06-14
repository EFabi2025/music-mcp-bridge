# Configuración Detallada - Spotify MCP Server

## 🔧 Configuración paso a paso

### 1. Configuración de Spotify Developer

#### Crear aplicación en Spotify
1. Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Inicia sesión con tu cuenta de Spotify
3. Haz clic en **"Create App"**
4. Completa el formulario:
   ```
   App name: Spotify MCP Server
   App description: MCP Server for Claude AI integration
   Website: http://localhost (opcional)
   Redirect URI: http://127.0.0.1:8888/callback
   ```
5. Acepta los términos de servicio
6. Haz clic en **"Save"**

#### Obtener credenciales
1. En tu aplicación creada, haz clic en **"Settings"**
2. Copia el **Client ID**
3. Haz clic en **"View client secret"** y copia el **Client Secret**
4. Verifica que la **Redirect URI** sea exactamente: `http://127.0.0.1:8888/callback`

### 2. Configuración del proyecto

#### Clonar y configurar
```bash
# Clonar repositorio
git clone <repository-url>
cd spotify-mcp-server

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar credenciales
cp spotify_credentials_example.py spotify_credentials.py
```

#### Editar credenciales
Abre `spotify_credentials.py` y reemplaza:
```python
SPOTIFY_CLIENT_ID = "tu_client_id_real_aqui"
SPOTIFY_CLIENT_SECRET = "tu_client_secret_real_aqui"
```

### 3. Configuración en Claude/Cursor

#### Ubicar archivo mcp.json
- **macOS**: `~/.cursor/mcp.json` o `~/Library/Application Support/Claude/mcp.json`
- **Windows**: `%APPDATA%\Claude\mcp.json`
- **Linux**: `~/.config/claude/mcp.json`

#### Agregar configuración
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

**Importante**: Reemplaza `/ruta/completa/al/proyecto/` con la ruta real donde clonaste el repositorio.

### 4. Verificación

#### Probar instalación
```bash
# Activar entorno virtual
source venv/bin/activate

# Verificar dependencias
python -c "import mcp, spotipy; print('✅ Dependencias OK')"

# Verificar credenciales
python -c "from spotify_credentials import SPOTIFY_CLIENT_ID; print('✅ Credenciales configuradas')"
```

#### Primera autenticación
1. Reinicia Claude/Cursor
2. En una conversación, escribe: `login()`
3. Se abrirá tu navegador automáticamente
4. Autoriza la aplicación en Spotify
5. Regresa a Claude - deberías ver confirmación de autenticación exitosa

### 5. Solución de problemas comunes

#### Error: "Module not found"
```bash
# Verificar que el entorno virtual esté activado
which python  # Debe mostrar la ruta del venv

# Reinstalar dependencias
pip install --upgrade -r requirements.txt
```

#### Error: "Invalid client"
- Verifica que el Client ID y Client Secret sean correctos
- Confirma que la Redirect URI sea exactamente `http://127.0.0.1:8888/callback`
- Asegúrate de que no haya espacios extra en las credenciales

#### Error: "Port already in use"
- El puerto 8888 está ocupado
- Cierra otras aplicaciones que puedan usar ese puerto
- O cambia el puerto en `spotify_credentials.py` y en la configuración de Spotify

#### Error: "Permission denied"
- Verifica permisos del directorio del proyecto
- En macOS/Linux: `chmod +x fixed_server.py`

### 6. Configuración avanzada

#### Variables de entorno (opcional)
Puedes usar variables de entorno en lugar del archivo de credenciales:
```bash
export SPOTIFY_CLIENT_ID="tu_client_id"
export SPOTIFY_CLIENT_SECRET="tu_client_secret"
```

#### Logging personalizado
Para habilitar logs detallados, crea el directorio:
```bash
mkdir logs
```

Los logs se guardarán automáticamente en `logs/spotify_mcp.log`.

### 7. Seguridad

#### ✅ Buenas prácticas
- Nunca compartas tu archivo `spotify_credentials.py`
- Nunca subas archivos `.spotify_token_cache` a repositorios
- Usa el archivo `.gitignore` proporcionado
- Regenera credenciales si sospechas que fueron comprometidas

#### ❌ Evitar
- No hardcodees credenciales en el código
- No uses credenciales de producción para desarrollo
- No compartas tokens de acceso

---

¿Necesitas ayuda? Abre un issue en el repositorio con detalles del problema. 