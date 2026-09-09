import os
import asyncio
import time
from abc import ABC, abstractmethod
import winrt.windows.media.control as wmc
import winrt.windows.storage.streams as wss
from utils import config

def _run_async(coro):
    """Utility to safely run WinRT async coroutines across threads."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If called from a thread where loop is running
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=4)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class BaseMediaBackend(ABC):
    """Abstract interface for Ticky media playback backends."""
    
    @abstractmethod
    def get_current_playback(self) -> dict:
        """
        Fetch current playback state dictionary.
        Expected keys:
          - is_playing: bool
          - title: str
          - artist: str
          - album: str
          - album_art_bytes: bytes (or None)
          - album_art_url: str (or None)
          - progress_ms: int
          - duration_ms: int
          - can_play: bool
          - can_pause: bool
          - can_next: bool
          - can_prev: bool
          - can_seek: bool
          - id: str
          - source: str
        """
        pass

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def toggle_play_pause(self):
        pass

    @abstractmethod
    def next_track(self):
        pass

    @abstractmethod
    def previous_track(self):
        pass

    @abstractmethod
    def seek(self, position_ms: int):
        pass


class WindowsMediaBackend(BaseMediaBackend):
    """
    Windows GSMTC (Global System Media Transport Controls) backend.
    Interacts directly with native Windows Media Transport session manager.
    """
    
    def __init__(self):
        self._cached_artwork_id = None
        self._cached_artwork_bytes = None
        
    async def _get_manager(self):
        try:
            return await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        except Exception:
            return None

    async def _find_spotify_session(self):
        manager = await self._get_manager()
        if not manager:
            return None, None
            
        sessions = manager.get_sessions()
        if not sessions:
            return None, None

        spotify_desktop_playing = []
        spotify_desktop_paused = []
        spotify_web_playing = []
        spotify_web_paused = []
        browser_music_playing = []
        browser_music_paused = []
        other_playing = []
        other_paused = []

        browser_keywords = ["chrome", "msedge", "edge", "opera", "firefox", "brave", "vivaldi", "arc", "browser"]

        for s in sessions:
            app_id = (s.source_app_user_model_id or "").lower()
            try:
                props = await s.try_get_media_properties_async()
                playback = s.get_playback_info()
                if not props or not playback:
                    continue

                status_int = int(playback.playback_status)
                is_playing = (status_int == 4) # 4 = Playing
                
                title = (props.title or "").strip()
                artist = (props.artist or "").strip()
                album = (props.album_title or "").strip()
                
                if not title and not artist:
                    continue

                title_l = title.lower()
                artist_l = artist.lower()
                album_l = album.lower()
                
                pb_type = int(playback.playback_type) if playback.playback_type is not None else 0
                
                # Check for Spotify Desktop
                is_spotify_desktop = "spotify" in app_id
                
                # Check for explicit Spotify Web Player indicators
                is_spotify_web = (
                    "spotify" in album_l or
                    "spotify" in artist_l or
                    "spotify" in title_l or
                    "open.spotify.com" in app_id
                )

                # Check for general Browser Media / Music session
                is_browser = any(b in app_id for b in browser_keywords)

                if is_spotify_desktop:
                    if is_playing:
                        spotify_desktop_playing.append((s, "Spotify Desktop"))
                    else:
                        spotify_desktop_paused.append((s, "Spotify Desktop"))
                elif is_spotify_web:
                    if is_playing:
                        spotify_web_playing.append((s, "Spotify Web Player"))
                    else:
                        spotify_web_paused.append((s, "Spotify Web Player"))
                elif is_browser or pb_type == 1: # Music type or browser session
                    source_label = "Spotify Web Player" if is_browser else "Media Player"
                    if is_playing:
                        browser_music_playing.append((s, source_label))
                    else:
                        browser_music_paused.append((s, source_label))
                else:
                    if is_playing:
                        other_playing.append((s, "Media Player"))
                    else:
                        other_paused.append((s, "Media Player"))
            except Exception:
                continue

        # Prioritization:
        # 1. Active Spotify Desktop
        # 2. Active Explicit Spotify Web
        # 3. Active Browser Music / Web Player
        # 4. Active Other Media
        # 5. Paused Spotify Desktop
        # 6. Paused Explicit Spotify Web
        # 7. Paused Browser Music / Web Player
        # 8. Paused Other Media

        candidates = (
            spotify_desktop_playing +
            spotify_web_playing +
            browser_music_playing +
            other_playing +
            spotify_desktop_paused +
            spotify_web_paused +
            browser_music_paused +
            other_paused
        )

        if candidates:
            return candidates[0][0], candidates[0][1]

        return None, None

    async def _get_playback_async(self):
        session, source_name = await self._find_spotify_session()
        if not session:
            return {}

        try:
            props = await session.try_get_media_properties_async()
            playback = session.get_playback_info()
            timeline = session.get_timeline_properties()
            
            if not props or not playback:
                return {}

            status_int = int(playback.playback_status)
            is_playing = (status_int == 4) # 4 = Playing
            
            # Capability flags
            ctrls = playback.controls
            can_play = ctrls.is_play_enabled if ctrls else True
            can_pause = ctrls.is_pause_enabled if ctrls else True
            can_next = ctrls.is_next_enabled if ctrls else True
            can_prev = ctrls.is_previous_enabled if ctrls else True
            can_seek = False # Seek support check if available

            # Timeline
            progress_ms = 0
            duration_ms = 0
            if timeline:
                try:
                    if hasattr(timeline.position, 'total_seconds'):
                        progress_ms = int(timeline.position.total_seconds() * 1000)
                    if hasattr(timeline.end_time, 'total_seconds'):
                        duration_ms = int(timeline.end_time.total_seconds() * 1000)
                except Exception:
                    pass

            # Thumbnail artwork stream
            art_bytes = None
            track_id = f"{props.title}_{props.artist}_{props.album_title}"
            
            if props.thumbnail:
                if track_id == self._cached_artwork_id and self._cached_artwork_bytes:
                    art_bytes = self._cached_artwork_bytes
                else:
                    try:
                        stream = await props.thumbnail.open_read_async()
                        size = stream.size
                        if size > 0:
                            reader = wss.DataReader(stream)
                            await reader.load_async(size)
                            buf = bytearray(size)
                            reader.read_bytes(buf)
                            art_bytes = bytes(buf)
                            self._cached_artwork_id = track_id
                            self._cached_artwork_bytes = art_bytes
                    except Exception:
                        pass

            return {
                "is_playing": is_playing,
                "title": props.title or "Unknown Track",
                "artist": props.artist or "Unknown Artist",
                "album": props.album_title or "",
                "album_art_bytes": art_bytes,
                "album_art_url": None,
                "progress_ms": progress_ms,
                "duration_ms": duration_ms,
                "can_play": can_play,
                "can_pause": can_pause,
                "can_next": can_next,
                "can_prev": can_prev,
                "can_seek": can_seek,
                "id": track_id,
                "source": source_name
            }
        except Exception:
            return {}

    def get_current_playback(self) -> dict:
        return _run_async(self._get_playback_async())

    async def _control_action_async(self, action, arg=None):
        session, _ = await self._find_spotify_session()
        if not session:
            return False
        try:
            if action == "play":
                return await session.try_play_async()
            elif action == "pause":
                return await session.try_pause_async()
            elif action == "toggle":
                return await session.try_toggle_play_pause_async()
            elif action == "next":
                return await session.try_skip_next_async()
            elif action == "prev":
                return await session.try_skip_previous_async()
            elif action == "seek" and arg is not None:
                # 10,000 ticks per millisecond in Windows TimeSpan
                ticks = int(arg) * 10000
                return await session.try_change_playback_position_async(ticks)
        except Exception:
            pass
        return False

    def play(self):
        _run_async(self._control_action_async("play"))

    def pause(self):
        _run_async(self._control_action_async("pause"))

    def toggle_play_pause(self):
        _run_async(self._control_action_async("toggle"))

    def next_track(self):
        _run_async(self._control_action_async("next"))

    def previous_track(self):
        _run_async(self._control_action_async("prev"))

    def seek(self, position_ms: int):
        _run_async(self._control_action_async("seek", position_ms))


class SpotifyAPIBackend(BaseMediaBackend):
    """
    Spotify Web API backend (OAuth fallback).
    Uses SpotifyClient to make REST API requests to Spotify accounts.
    """
    def __init__(self, spotify_client):
        self.client = spotify_client

    def get_current_playback(self) -> dict:
        raw = self.client.get_current_playback()
        if not raw:
            return {}
        return {
            "is_playing": raw.get("is_playing", False),
            "title": raw.get("title", "Unknown Track"),
            "artist": raw.get("artist", "Unknown Artist"),
            "album": "",
            "album_art_bytes": None,
            "album_art_url": raw.get("album_art"),
            "progress_ms": raw.get("progress_ms", 0),
            "duration_ms": raw.get("duration_ms", 0),
            "can_play": True,
            "can_pause": True,
            "can_next": True,
            "can_prev": True,
            "can_seek": True,
            "id": raw.get("id"),
            "source": "Spotify Web API"
        }

    def play(self):
        self.client.play()

    def pause(self):
        self.client.pause()

    def toggle_play_pause(self):
        # Determine current state and toggle
        pb = self.get_current_playback()
        if pb.get("is_playing"):
            self.pause()
        else:
            self.play()

    def next_track(self):
        self.client.next_track()

    def previous_track(self):
        self.client.previous_track()

    def seek(self, position_ms: int):
        pass


class MediaManager:
    """
    Unified manager routing playback calls to either WindowsMediaBackend (GSMTC)
    or SpotifyAPIBackend based on user configuration.
    """
    def __init__(self, spotify_client=None):
        self.win_backend = WindowsMediaBackend()
        from utils.spotify import SpotifyClient
        self.api_client = spotify_client or SpotifyClient()
        self.api_backend = SpotifyAPIBackend(self.api_client)

    def get_active_backend(self) -> BaseMediaBackend:
        mode = config.load_spotify_backend_mode("gsmtc")
        if mode == "api":
            return self.api_backend
        return self.win_backend

    def get_current_playback(self) -> dict:
        return self.get_active_backend().get_current_playback()

    def play(self):
        self.get_active_backend().play()

    def pause(self):
        self.get_active_backend().pause()

    def toggle_play_pause(self):
        self.get_active_backend().toggle_play_pause()

    def next_track(self):
        self.get_active_backend().next_track()

    def previous_track(self):
        self.get_active_backend().previous_track()

    def seek(self, position_ms: int):
        self.get_active_backend().seek(position_ms)
