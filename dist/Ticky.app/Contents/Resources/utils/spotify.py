import os
import json
import urllib.parse
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from PySide6.QtCore import QThread, Signal
from utils import config

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-modify-playback-state user-read-playback-state"

class SpotifyClient:
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret
        if not self.client_id or not self.client_secret:
            self.client_id, self.client_secret = config.load_spotify_credentials()
            
    def get_auth_url(self):
        """Generate Spotify OAuth URL."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "show_dialog": "true"
        }
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    def exchange_code_for_tokens(self, code):
        """Exchange redirect code for access & refresh tokens."""
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            r = requests.post(url, headers=headers, data=data, timeout=5)
            if r.status_code == 200:
                res = r.json()
                access = res.get("access_token")
                refresh = res.get("refresh_token")
                config.save_spotify_tokens(access, refresh)
                return True, access
            else:
                return False, f"HTTP {r.status_code}: {r.text}"
        except Exception as e:
            return False, str(e)

    def refresh_access_token(self):
        """Refresh the expired access token."""
        _, refresh_token = config.load_spotify_tokens()
        if not refresh_token:
            return None
            
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            r = requests.post(url, headers=headers, data=data, timeout=5)
            if r.status_code == 200:
                res = r.json()
                access = res.get("access_token")
                # Spotify might send a new refresh token as well
                new_refresh = res.get("refresh_token", refresh_token)
                config.save_spotify_tokens(access, new_refresh)
                return access
        except Exception:
            pass
        return None

    def get_headers(self):
        """Get auth headers, refreshing token if necessary."""
        access_token, _ = config.load_spotify_tokens()
        if not access_token:
            return None
        return {"Authorization": f"Bearer {access_token}"}

    def _make_request(self, method, endpoint, data=None):
        """Helper to make Spotify API requests, auto-refreshing on 401."""
        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = self.get_headers()
        if not headers:
            return None

        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=4)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=4)
            elif method == "PUT":
                r = requests.put(url, headers=headers, json=data, timeout=4)
            
            if r.status_code == 401: # Token expired
                new_access = self.refresh_access_token()
                if new_access:
                    headers = {"Authorization": f"Bearer {new_access}"}
                    if method == "GET":
                        r = requests.get(url, headers=headers, timeout=4)
                    elif method == "POST":
                        r = requests.post(url, headers=headers, json=data, timeout=4)
                    elif method == "PUT":
                        r = requests.put(url, headers=headers, json=data, timeout=4)
            return r
        except Exception:
            return None

    def get_current_playback(self):
        """Get currently playing track details."""
        r = self._make_request("GET", "me/player/currently-playing")
        if r and r.status_code == 200:
            try:
                data = r.json()
                item = data.get("item")
                if not item:
                    return None
                    
                album = item.get("album", {})
                images = album.get("images", [])
                image_url = images[0].get("url") if images else None
                
                artists = item.get("artists", [])
                artist_name = ", ".join([a.get("name") for a in artists]) if artists else "Unknown"
                
                return {
                    "is_playing": data.get("is_playing", False),
                    "title": item.get("name", "Unknown Track"),
                    "artist": artist_name,
                    "album_art": image_url,
                    "progress_ms": data.get("progress_ms", 0),
                    "duration_ms": item.get("duration_ms", 0),
                    "id": item.get("id")
                }
            except Exception:
                pass
        return None

    def play(self):
        """Resume Spotify playback."""
        self._make_request("PUT", "me/player/play")

    def pause(self):
        """Pause Spotify playback."""
        self._make_request("PUT", "me/player/pause")

    def next_track(self):
        """Skip to next track."""
        self._make_request("POST", "me/player/next")

    def previous_track(self):
        """Skip to previous track."""
        self._make_request("POST", "me/player/previous")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle incoming callback from Spotify."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        code_list = params.get("code")
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        
        if code_list:
            code = code_list[0]
            self.server.code = code
            self.wfile.write(b"<html><body style='background-color:#0F1115;color:#F2F4F8;font-family:sans-serif;text-align:center;padding:50px;'>")
            self.wfile.write(b"<h2>Ticky Spotify Authorization Successful!</h2>")
            self.wfile.write(b"<p>You can close this tab and return to Ticky Dev settings.</p>")
            self.wfile.write(b"</body></html>")
        else:
            self.wfile.write(b"<html><body style='background-color:#0F1115;color:#FF453A;font-family:sans-serif;text-align:center;padding:50px;'>")
            self.wfile.write(b"<h2>Authorization Failed</h2>")
            self.wfile.write(b"<p>No code parameter found in callback redirect.</p>")
            self.wfile.write(b"</body></html>")

    def log_message(self, format, *args):
        pass # Suppress command line logging clutter


class SpotifyOAuthServerThread(QThread):
    auth_completed = Signal(bool, str)

    def __init__(self, client_id, client_secret, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = SpotifyClient(client_id, client_secret)
        self.server = None

    def get_auth_url(self):
        return self.client.get_auth_url()

    def run(self):
        # Start local HTTP server
        try:
            self.server = HTTPServer(("127.0.0.1", 8888), OAuthCallbackHandler)
            self.server.code = None
            
            # Block and handle requests until code is set
            while self.server.code is None:
                self.server.handle_request()
                
            code = self.server.code
            # Exchange code for tokens
            success, message = self.client.exchange_code_for_tokens(code)
            if success:
                self.auth_completed.emit(True, "Access authorized successfully.")
            else:
                self.auth_completed.emit(False, f"Token exchange failed: {message}")
                
        except Exception as e:
            self.auth_completed.emit(False, f"Local server error: {str(e)}")
            
        finally:
            if self.server:
                self.server.server_close()


class SpotifyWorker(QThread):
    data_fetched = Signal(dict)

    def __init__(self, action, media_manager=None, parent=None, arg=None):
        super().__init__(parent)
        self.action = action
        self.media_manager = media_manager
        self.arg = arg
        
    def run(self):
        try:
            if not self.media_manager:
                from utils.media_backend import MediaManager
                self.media_manager = MediaManager()

            if self.action == "play":
                self.media_manager.play()
            elif self.action == "pause":
                self.media_manager.pause()
            elif self.action == "toggle":
                self.media_manager.toggle_play_pause()
            elif self.action == "next":
                self.media_manager.next_track()
            elif self.action == "prev":
                self.media_manager.previous_track()
            elif self.action == "seek" and self.arg is not None:
                self.media_manager.seek(self.arg)
            elif self.action == "poll":
                playback = self.media_manager.get_current_playback()
                self.data_fetched.emit(playback or {})
        except Exception:
            if self.action == "poll":
                self.data_fetched.emit({})

