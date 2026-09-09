import os
import time
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QSlider, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, QThread, Signal, QUrl, QByteArray, QPointF
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QConicalGradient, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from utils import config
from utils.spotify import SpotifyWorker
from utils.media_backend import MediaManager
from styles import theme
from styles import qss
from widgets.toolbar import ToolbarButton

# Raw SVG shapes using COLOR_PLACEHOLDER for dynamic coloring matching the design system
SVG_PREV = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M17.46 6.11c-.33-.17-.73-.14-1.04.08l-7 5c-.26.19-.42.49-.42.81s.16.63.42.81l7 5c.17.12.38.19.58.19.16 0 .31-.04.46-.11.33-.17.54-.51.54-.89V7c0-.37-.21-.72-.54-.89M16 15.06 11.72 12 16 8.94v6.11ZM6 6h2v12H6z"></path></svg>'
SVG_PLAY = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path><path d="m9 17 8-5-8-5z"></path></svg>'
SVG_PAUSE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path><path d="M13 8h2v8h-2zM9 8h2v8H9z"></path></svg>'
SVG_NEXT = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="m14.58 11.19-7-5c-.31-.22-.71-.25-1.04-.08S6 6.62 6 7v10c0 .37.21.72.54.89.14.07.3.11.46.11.2 0 .41-.06.58-.19l7-5c.26-.19.42-.49.42-.81s-.16-.63-.42-.81M8 15.06V8.95l4.28 3.06L8 15.07ZM16 6h2v12h-2z"></path></svg>'


class ElidedLabel(QLabel):
    """Subclass of QLabel that automatically elides text to fit container width."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)
        painter.end()


class CDPlayerWidget(QWidget):
    """Custom widget representing a rotating CD vinyl record displaying circular album art in the center."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(74, 74)
        
        self.album_pixmap = None
        self.rotation_angle = 0.0
        self.is_rotating = False
        
        # 60 FPS animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(16) # ~60 FPS
        self.timer.timeout.connect(self.rotate_tick)
        
        self.placeholder_pixmap = self.create_placeholder_pixmap("🎵", "#33353F")

    def create_placeholder_pixmap(self, text, color_hex):
        pixmap = QPixmap(74, 74)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 74, 74)
        
        painter.setPen(QColor("#FFFFFF"))
        font = QFont(theme.FONT_FAMILY, 22, QFont.Weight.Bold)
        painter.setFont(font)
        char = text[0].upper() if text else "🎵"
        painter.drawText(0, 0, 74, 74, Qt.AlignmentFlag.AlignCenter, char)
        painter.end()
        return pixmap

    def set_album_art(self, pixmap):
        self.album_pixmap = pixmap
        self.update()

    def set_placeholder(self, text, color_hex):
        self.album_pixmap = self.create_placeholder_pixmap(text, color_hex)
        self.update()

    def start_rotation(self):
        if not self.is_rotating:
            self.is_rotating = True
            self.timer.start()

    def stop_rotation(self):
        if self.is_rotating:
            self.is_rotating = False
            self.timer.stop()

    def rotate_tick(self):
        # 1.2 degrees per frame creates a smooth spinning visual speed
        self.rotation_angle = (self.rotation_angle + 1.2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Translate coordinate system to center
        painter.translate(37, 37)
        
        # Apply active rotation
        painter.rotate(self.rotation_angle)
        
        # 1. Draw CD base body with Conical Gradient to replicate metallic reflections
        gradient = QConicalGradient(QPointF(0, 0), 90)
        # Deep black vinyl base color to stand out from the card background
        base_color = QColor("#0b0c10")
        # Pronounced metallic sheen colors
        sheen_color = QColor(255, 255, 255, 45) # Brighter sheen reflection!
        dark_sheen = QColor(0, 0, 0, 180) # Deeper shadows for reflection contrast!
        
        gradient.setColorAt(0.0, base_color)
        gradient.setColorAt(0.18, sheen_color)
        gradient.setColorAt(0.35, dark_sheen)
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(0.68, sheen_color)
        gradient.setColorAt(0.85, dark_sheen)
        gradient.setColorAt(1.0, base_color)
        
        painter.setBrush(gradient)
        # Use a subtle silver outer rim border to define the CD boundary clearly
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.drawEllipse(-37, -37, 74, 74)
        
        # 2. Draw CD vinyl concentric track grooves (higher contrast)
        painter.setBrush(Qt.GlobalColor.transparent)
        pen = QPen(QColor(255, 255, 255, 15), 0.75)
        painter.setPen(pen)
        painter.drawEllipse(-33, -33, 66, 66)
        painter.drawEllipse(-29, -29, 58, 58)
        painter.drawEllipse(-25, -25, 50, 50)
        
        # 3. Draw circular album cover in center (increased size to 42px for better visibility)
        pix = self.album_pixmap if self.album_pixmap else self.placeholder_pixmap
        
        path = QPainterPath()
        path.addEllipse(-21, -21, 42, 42)
        
        painter.save()
        painter.setClipPath(path)
        scaled_pix = pix.scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(-21, -21, scaled_pix)
        painter.restore()
        
        # Album cover divider line & ring highlight
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(-21, -21, 42, 42)
        
        # 4. Spindle hole layout
        # Clear plastic center ring: radius 7px
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(0, 0, 0, 100)) # Semi-transparent center ring
        painter.drawEllipse(-7, -7, 14, 14)
        
        # Inner dark spindle spindle hole: radius 4px
        painter.setBrush(QColor(0, 0, 0, 240))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(-4, -4, 8, 8)
        
        painter.end()


class SpotifyPanel(QWidget):
    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.media_manager = MediaManager()
        self.is_expanded = False

        
        # State management
        self.current_track_id = None
        self.is_playing = False
        self.progress_ms = 0
        self.duration_ms = 0
        self.active_workers = [] # Thread references tracker list to prevent GC crashes
        
        # Album art loading
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.on_image_downloaded)
        self.cached_album_art = None
        
        # Layout & components
        self.init_ui()
        
        # Height Animation configuration
        self.setFixedHeight(0) # Collapsed by default
        self.height_anim = QPropertyAnimation(self, b"anim_height")
        self.height_anim.setDuration(250)
        
        # Ticking timer for local timeline update
        self.timeline_timer = QTimer(self)
        self.timeline_timer.setInterval(1000)
        self.timeline_timer.timeout.connect(self.on_timeline_tick)
        
        # API Polling timer
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(4000) # Poll Spotify Web API every 4s
        self.poll_timer.timeout.connect(self.poll_spotify_api)
        
        # Simulated/Demo mode variables
        self.demo_tracks = [
            {"title": "Blinding Lights", "artist": "The Weeknd", "duration_ms": 200000, "color": "#FF007F"},
            {"title": "Cruel Summer", "artist": "Taylor Swift", "duration_ms": 178000, "color": "#FF9F0A"},
            {"title": "Starboy", "artist": "The Weeknd", "duration_ms": 230000, "color": "#30D158"}
        ]
        self.demo_index = 0

    def get_anim_height(self):
        return self.height()

    def set_anim_height(self, h):
        self.setFixedHeight(h)
        if self.parent_window:
            self.parent_window.adjust_layout_height()

    anim_height = Property(int, get_anim_height, set_anim_height)

    def set_mini_mode(self, active):
        if active:
            self.setFixedWidth(340)
            self.layout().setContentsMargins(10, 10, 10, 10)
        else:
            self.setFixedWidth(320)
            self.layout().setContentsMargins(0, 10, 0, 0)

    def init_ui(self):
        self.setFixedWidth(320)
        
        # Panel main wrapper layout (adds 10px top spacing when expanded)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 10, 0, 0)
        main_layout.setSpacing(0)
        
        # Inner Card container (card height is 94px)
        self.card = QFrame(self)
        self.card.setObjectName("SpotifyPanelContainer")
        self.card.setFixedHeight(94)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(10)
        
        # 1. Album art cover image (integrated CDPlayerWidget)
        self.cd_widget = CDPlayerWidget(self.card)
        card_layout.addWidget(self.cd_widget)
        
        # 2. Right details layout
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)
        
        # Title and artist names
        self.lbl_title = ElidedLabel("Not Playing", self.card)
        self.lbl_title.setObjectName("SpotifySongTitle")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_artist = ElidedLabel("Spotify Integration", self.card)
        self.lbl_artist.setObjectName("SpotifySongArtist")
        self.lbl_artist.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        details_layout.addWidget(self.lbl_title)
        details_layout.addWidget(self.lbl_artist)
        
        # Timeline slider container
        self.timeline_container = QWidget(self.card)
        timeline_layout = QHBoxLayout(self.timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(6)
        
        self.slider = QSlider(Qt.Orientation.Horizontal, self.timeline_container)
        self.slider.setObjectName("SpotifyTimeline")
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.sliderPressed.connect(lambda: self.slider.setValue(self.slider.value())) 
        
        self.lbl_time = QLabel("0:00 / 0:00", self.timeline_container)
        self.lbl_time.setObjectName("SpotifyTimeLabel")
        
        timeline_layout.addWidget(self.slider)
        timeline_layout.addWidget(self.lbl_time)
        details_layout.addWidget(self.timeline_container)
        self.update_timeline_visibility()
        
        # Control Buttons row using unified ToolbarButton elements (without background hover glow)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(16)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center horizontally
        
        self.btn_prev = ToolbarButton(SVG_PREV, "Previous", self.card, draw_background_hover=False)
        self.btn_play = ToolbarButton(SVG_PLAY, "Play/Pause", self.card, draw_background_hover=False)
        self.btn_next = ToolbarButton(SVG_NEXT, "Next", self.card, draw_background_hover=False)
        
        self.btn_prev.clicked.connect(self.prev_clicked)
        self.btn_play.clicked.connect(self.play_clicked)
        self.btn_next.clicked.connect(self.next_clicked)
        
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next)
        
        details_layout.addLayout(ctrl_layout)
        card_layout.addLayout(details_layout)
        
        main_layout.addWidget(self.card)
        self.refresh_styles()

    def update_timeline_visibility(self):
        """Show timeline slider only when using Spotify API or Demo mode."""
        demo = config.load_spotify_demo_mode()
        backend_mode = config.load_spotify_backend_mode("gsmtc")
        show_timeline = demo or (backend_mode == "api")
        if hasattr(self, 'timeline_container'):
            self.timeline_container.setVisible(show_timeline)

    def refresh_styles(self):
        """Update buttons and SVG colors dynamically using current theme accent."""
        self.update_timeline_visibility()
        self.btn_prev.update()
        self.btn_play.update()
        self.btn_next.update()
        self.setStyleSheet(qss.get_spotify_panel_style())

    def spawn_worker(self, worker):
        """Register worker thread in local tracker list and launch it."""
        self.active_workers.append(worker)
        worker.finished.connect(lambda: self.cleanup_worker(worker))
        worker.start()

    def cleanup_worker(self, worker):
        """Clean up thread reference safely on completion to prevent garbage collection crashes."""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
            worker.deleteLater()

    def toggle(self):
        """Expand or collapse the Spotify panel height."""
        self.show() # Make sure the widget is shown so it is visible when animating!
        self.is_expanded = not self.is_expanded
        
        if self.parent_window and hasattr(self.parent_window, 'toolbar'):
            self.parent_window.toolbar.btn_music.setActive(self.is_expanded)
        
        # Stop timers and clean up active threads if collapsed
        if not self.is_expanded:
            self.timeline_timer.stop()
            self.poll_timer.stop()
            self.cd_widget.stop_rotation()
            
            # Quitting running background threads safely
            for worker in list(self.active_workers):
                worker.quit()
                worker.wait()
                self.cleanup_worker(worker)
                
            self.height_anim.setStartValue(self.height())
            self.height_anim.setEndValue(0)
            self.height_anim.start()
        else:
            self.update_playback()
            self.timeline_timer.start()
            if not config.load_spotify_demo_mode():
                self.poll_timer.start()
                
            self.height_anim.setStartValue(self.height())
            self.height_anim.setEndValue(104) # 94px card height + 10px spacing top
            self.height_anim.start()

    def update_playback(self):
        """Fetch current song parameters (Real API or Simulation)."""
        demo = config.load_spotify_demo_mode()
        
        if demo:
            track = self.demo_tracks[self.demo_index]
            self.lbl_title.setText(track["title"])
            self.lbl_artist.setText(track["artist"])
            self.duration_ms = track["duration_ms"]
            self.current_track_id = f"demo_{self.demo_index}"
            
            # Generate placeholder cover
            self.cd_widget.set_placeholder(track["title"], track["color"])
            
            # Format duration
            self.update_time_label()
            self.btn_play.set_svg_template(SVG_PLAY if not self.is_playing else SVG_PAUSE, "Play/Pause")
            
            # Sync CD rotation
            if self.is_playing:
                self.cd_widget.start_rotation()
            else:
                self.cd_widget.stop_rotation()
                
            self.refresh_styles()
        else:
            # Run non-blocking API query
            self.poll_spotify_api()

    def poll_spotify_api(self):
        """Query current playback state asynchronously using MediaManager via SpotifyWorker."""
        if config.load_spotify_demo_mode():
            return
            
        backend_mode = config.load_spotify_backend_mode("gsmtc")
        if backend_mode == "api":
            access, _ = config.load_spotify_tokens()
            if not access:
                self.lbl_title.setText("Not Connected")
                self.lbl_artist.setText("Connect in Settings")
                self.cd_widget.set_placeholder("?", "#555555")
                return
            
        worker = SpotifyWorker("poll", self.media_manager, self)
        worker.data_fetched.connect(self.on_api_data_received)
        self.spawn_worker(worker)

    def on_api_data_received(self, data):
        if not data:
            self.lbl_title.setText("No active playback")
            self.lbl_artist.setText("Open Spotify Desktop or Web Player")
            self.cd_widget.set_placeholder("🎵", theme.BORDER_COLOR)
            self.is_playing = False
            self.progress_ms = 0
            self.duration_ms = 0
            self.btn_play.set_svg_template(SVG_PLAY, "Play/Pause")
            self.cd_widget.stop_rotation()
            self.update_time_label()
            self.refresh_styles()
            return
            
        self.lbl_title.setText(data.get("title", "Unknown Track"))
        self.lbl_artist.setText(data.get("artist", "Unknown Artist"))
        self.is_playing = data.get("is_playing", False)
        self.progress_ms = data.get("progress_ms", 0)
        self.duration_ms = data.get("duration_ms", 0)
        
        # Capability flags update
        self.btn_prev.setEnabled(data.get("can_prev", True))
        self.btn_next.setEnabled(data.get("can_next", True))
        self.btn_play.setEnabled(data.get("can_play", True) or data.get("can_pause", True))
        
        # Sync Play/Pause Template
        self.btn_play.set_svg_template(SVG_PLAY if not self.is_playing else SVG_PAUSE, "Play/Pause")
        
        # Sync CD rotation
        if self.is_playing:
            self.cd_widget.start_rotation()
        else:
            self.cd_widget.stop_rotation()
        
        # Load Album Art
        art_bytes = data.get("album_art_bytes")
        art_url = data.get("album_art_url")
        track_id = data.get("id")
        
        if art_bytes:
            if track_id != self.current_track_id:
                self.current_track_id = track_id
                pixmap = QPixmap()
                if pixmap.loadFromData(art_bytes):
                    self.cd_widget.set_album_art(pixmap)
                else:
                    self.cd_widget.set_placeholder(data.get("title", "?"), theme.ACCENT_COLOR)
        elif art_url:
            if art_url != self.current_track_id:
                self.current_track_id = art_url
                self.network_manager.get(QNetworkRequest(QUrl(art_url)))
        else:
            self.current_track_id = None
            self.cd_widget.set_placeholder(data.get("title", "?"), theme.ACCENT_COLOR)
            
        self.update_time_label()
        self.refresh_styles()

    def on_image_downloaded(self, reply):
        """Triggered when network manager completes image query."""
        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Pass the raw QPixmap directly to the CD widget
                self.cd_widget.set_album_art(pixmap)
        reply.deleteLater()

    def on_timeline_tick(self):
        """Local ticker running every second to advance progress bar."""
        if not self.is_playing:
            return
            
        self.progress_ms += 1000
        if self.progress_ms >= self.duration_ms:
            self.progress_ms = 0
            if config.load_spotify_demo_mode():
                self.next_clicked() # Auto-advance in demo mode
            else:
                self.poll_spotify_api()
                
        self.update_time_label()

    def update_time_label(self):
        """Update slider position and duration label."""
        if self.duration_ms > 0:
            percentage = int((self.progress_ms / self.duration_ms) * 100)
            self.slider.setValue(percentage)
            
            prog_sec = (self.progress_ms // 1000) % 60
            prog_min = (self.progress_ms // 1000) // 60
            dur_sec = (self.duration_ms // 1000) % 60
            dur_min = (self.duration_ms // 1000) // 60
            
            self.lbl_time.setText(f"{prog_min}:{prog_sec:02d} / {dur_min}:{dur_sec:02d}")
        else:
            self.slider.setValue(0)
            self.lbl_time.setText("0:00 / 0:00")

    # Click interactions using crash-proof background workers
    def play_clicked(self):
        demo = config.load_spotify_demo_mode()
        self.is_playing = not self.is_playing
        self.btn_play.set_svg_template(SVG_PLAY if not self.is_playing else SVG_PAUSE, "Play/Pause")
        
        # Sync CD rotation
        if self.is_playing:
            self.cd_widget.start_rotation()
        else:
            self.cd_widget.stop_rotation()
            
        if demo:
            self.refresh_styles()
        else:
            worker = SpotifyWorker("toggle", self.media_manager, self)
            worker.finished.connect(self.poll_spotify_api)
            self.spawn_worker(worker)

    def next_clicked(self):
        demo = config.load_spotify_demo_mode()
        
        if demo:
            self.demo_index = (self.demo_index + 1) % len(self.demo_tracks)
            self.progress_ms = 0
            self.is_playing = True
            self.cd_widget.start_rotation()
            self.update_playback()
        else:
            worker = SpotifyWorker("next", self.media_manager, self)
            worker.finished.connect(lambda: QTimer.singleShot(400, self.poll_spotify_api))
            self.spawn_worker(worker)

    def prev_clicked(self):
        demo = config.load_spotify_demo_mode()
        
        if demo:
            self.demo_index = (self.demo_index - 1) % len(self.demo_tracks)
            self.progress_ms = 0
            self.is_playing = True
            self.cd_widget.start_rotation()
            self.update_playback()
        else:
            worker = SpotifyWorker("prev", self.media_manager, self)
            worker.finished.connect(lambda: QTimer.singleShot(400, self.poll_spotify_api))
            self.spawn_worker(worker)

