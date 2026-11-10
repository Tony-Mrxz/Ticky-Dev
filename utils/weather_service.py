# utils/weather_service.py
"""
Weather service for Ticky:
- IP geolocation detection (ip-api.com) with config caching.
- Forecast retrieval using Open-Meteo (free, no API key required).
- Non-blocking background fetches via QThread/Signals.
- WMO Weather Code decoding to condition labels and icon types.
- Temperature unit conversion (°C / °F).
"""

import json
import time
import urllib.request
from PySide6.QtCore import QObject, Signal, QThread
from utils import config

# WMO Weather interpretation codes (WW)
WMO_CODE_MAP = {
    0: ("Clear Sky", "sun"),
    1: ("Mainly Clear", "sun_cloud"),
    2: ("Partly Cloudy", "cloud_sun"),
    3: ("Overcast", "cloud"),
    45: ("Foggy", "fog"),
    48: ("Depositing Rime Fog", "fog"),
    51: ("Light Drizzle", "drizzle"),
    53: ("Moderate Drizzle", "drizzle"),
    55: ("Dense Drizzle", "drizzle"),
    56: ("Light Freezing Drizzle", "freezing_rain"),
    57: ("Dense Freezing Drizzle", "freezing_rain"),
    61: ("Slight Rain", "rain"),
    63: ("Moderate Rain", "rain"),
    65: ("Heavy Rain", "heavy_rain"),
    66: ("Light Freezing Rain", "freezing_rain"),
    67: ("Heavy Freezing Rain", "freezing_rain"),
    71: ("Slight Snow", "snow"),
    73: ("Moderate Snow", "snow"),
    75: ("Heavy Snow", "heavy_snow"),
    77: ("Snow Grains", "snow"),
    80: ("Slight Rain Showers", "rain"),
    81: ("Moderate Rain Showers", "rain"),
    82: ("Violent Rain Showers", "heavy_rain"),
    85: ("Slight Snow Showers", "snow"),
    86: ("Heavy Snow Showers", "heavy_snow"),
    95: ("Thunderstorm", "thunder"),
    96: ("Thunderstorm with Slight Hail", "thunder_rain"),
    99: ("Thunderstorm with Heavy Hail", "thunder_rain"),
}

CACHE_TTL_SECONDS = 1200  # 20 minutes cache


def get_wmo_info(code: int):
    """Return (condition_text, icon_key) for a WMO weather code."""
    return WMO_CODE_MAP.get(code, ("Unknown", "cloud_sun"))


def c_to_f(celsius: float) -> float:
    return (celsius * 9.0 / 5.0) + 32.0


def format_temp(celsius: float, unit: str = None) -> str:
    if unit is None:
        unit = config.load_weather_unit("C")
    if celsius is None:
        return "--°"
    if unit.upper() == "F":
        val = round(c_to_f(celsius))
        return f"{val}°F"
    val = round(celsius)
    return f"{val}°C"


class WeatherFetchWorker(QThread):
    """Background worker to fetch location and Open-Meteo weather data."""
    finished_data = Signal(dict)
    failed = Signal(str)

    def __init__(self, force_refresh: bool = False, custom_lat: float = None, custom_lon: float = None, custom_city: str = None):
        super().__init__()
        self.force_refresh = force_refresh
        self.custom_lat = custom_lat
        self.custom_lon = custom_lon
        self.custom_city = custom_city

    def run(self):
        try:
            # 1. Resolve Location
            lat = self.custom_lat
            lon = self.custom_lon
            city = self.custom_city
            country = ""

            # Check if user manually set a city in Settings
            manual_city = config.load_weather_city()
            if manual_city and (lat is None or lon is None):
                try:
                    import urllib.parse
                    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(manual_city)}&count=1&language=en&format=json"
                    req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "TickyApp/1.0"})
                    with urllib.request.urlopen(req_geo, timeout=5) as resp:
                        g_data = json.loads(resp.read().decode("utf-8"))
                        results = g_data.get("results", [])
                        if results:
                            r = results[0]
                            lat = r.get("latitude")
                            lon = r.get("longitude")
                            city = r.get("name", manual_city)
                            country = r.get("country", "")
                except Exception:
                    pass

            if lat is None or lon is None:
                saved_loc = config.load_weather_location()
                if saved_loc and not self.force_refresh and "lat" in saved_loc and "lon" in saved_loc and not manual_city:
                    lat = saved_loc["lat"]
                    lon = saved_loc["lon"]
                    city = saved_loc.get("city", "Unknown")
                    country = saved_loc.get("country", "")
                else:
                    # Detect via ip-api.com
                    try:
                        req_geo = urllib.request.Request(
                            "http://ip-api.com/json/",
                            headers={"User-Agent": "TickyApp/1.0"}
                        )
                        with urllib.request.urlopen(req_geo, timeout=5) as resp:
                            geo_data = json.loads(resp.read().decode("utf-8"))
                            if geo_data.get("status") == "success":
                                lat = geo_data.get("lat")
                                lon = geo_data.get("lon")
                                city = geo_data.get("city", "My Location")
                                country = geo_data.get("country", "")
                                config.save_weather_location({
                                    "lat": lat,
                                    "lon": lon,
                                    "city": city,
                                    "country": country,
                                    "updated_at": time.time()
                                })
                    except Exception:
                        # Fallback to saved location or default if IP lookup fails
                        if saved_loc:
                            lat = saved_loc.get("lat", 37.7749)
                            lon = saved_loc.get("lon", -122.4194)
                            city = saved_loc.get("city", "San Francisco")
                            country = saved_loc.get("country", "US")
                        else:
                            lat, lon, city, country = 37.7749, -122.4194, "San Francisco", "US"

            if lat is None or lon is None:
                self.failed.emit("Could not determine geographic location.")
                return

            # 2. Fetch Open-Meteo Weather
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
                f"&hourly=temperature_2m,weather_code,precipitation_probability"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,uv_index_max"
                f"&timezone=auto"
            )

            req = urllib.request.Request(url, headers={"User-Agent": "TickyApp/1.0"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data.get("current", {})
            hourly = data.get("hourly", {})
            daily = data.get("daily", {})

            current_code = current.get("weather_code", 0)
            cond_text, icon_key = get_wmo_info(current_code)

            # Build 6-8 hourly forecast pills starting from current hour
            hourly_times = hourly.get("time", [])
            hourly_temps = hourly.get("temperature_2m", [])
            hourly_codes = hourly.get("weather_code", [])
            hourly_precip = hourly.get("precipitation_probability", [])

            now_str = current.get("time", "")  # Format: "2026-11-10T04:15"
            start_idx = 0
            if now_str and hourly_times:
                now_hour_prefix = now_str[:13]  # "2026-11-10T04"
                for idx, t in enumerate(hourly_times):
                    if t.startswith(now_hour_prefix):
                        start_idx = idx
                        break

            hourly_items = []
            for i in range(start_idx, min(start_idx + 8, len(hourly_times))):
                t_raw = hourly_times[i]  # "2026-11-10T05:00"
                try:
                    hour_num = int(t_raw.split("T")[1].split(":")[0])
                    # Format as 12h: "5 AM", "12 PM"
                    period = "AM" if hour_num < 12 else "PM"
                    display_h = hour_num % 12
                    if display_h == 0:
                        display_h = 12
                    time_label = f"{display_h} {period}"
                    if i == start_idx:
                        time_label = "Now"
                except Exception:
                    time_label = t_raw

                h_code = hourly_codes[i] if i < len(hourly_codes) else 0
                _, h_icon = get_wmo_info(h_code)
                h_temp = hourly_temps[i] if i < len(hourly_temps) else 0.0
                h_rain = hourly_precip[i] if i < len(hourly_precip) else 0

                hourly_items.append({
                    "time": time_label,
                    "temp_c": h_temp,
                    "code": h_code,
                    "icon": h_icon,
                    "rain_prob": h_rain
                })

            # Daily High / Low
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            uv_indices = daily.get("uv_index_max", [])
            temp_max = max_temps[0] if max_temps else None
            temp_min = min_temps[0] if min_temps else None
            uv_index = uv_indices[0] if uv_indices else None

            result = {
                "city": city,
                "country": country,
                "lat": lat,
                "lon": lon,
                "temp_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "precipitation": current.get("precipitation"),
                "code": current_code,
                "condition": cond_text,
                "icon": icon_key,
                "temp_max_c": temp_max,
                "temp_min_c": temp_min,
                "uv_index": uv_index,
                "hourly": hourly_items,
                "fetched_at": time.time(),
            }

            self.finished_data.emit(result)

        except Exception as e:
            self.failed.emit(str(e))


class WeatherService(QObject):
    """Singleton-friendly service that caches and manages weather updates."""
    updated = Signal(dict)
    error = Signal(str)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = WeatherService()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cached_weather = None
        self._worker = None

    def get_cached_weather(self):
        """Returns cached weather if still fresh (within CACHE_TTL_SECONDS)."""
        if self.cached_weather:
            age = time.time() - self.cached_weather.get("fetched_at", 0)
            if age < CACHE_TTL_SECONDS:
                return self.cached_weather
        return None

    def refresh(self, force: bool = False):
        """Trigger an asynchronous refresh."""
        if not force:
            fresh = self.get_cached_weather()
            if fresh:
                self.updated.emit(fresh)
                return

        if self._worker and self._worker.isRunning():
            return  # Already fetching

        self._worker = WeatherFetchWorker(force_refresh=force)
        self._worker.finished_data.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_finished(self, data: dict):
        self.cached_weather = data
        self.updated.emit(data)

    def _on_worker_failed(self, error_msg: str):
        self.error.emit(error_msg)

