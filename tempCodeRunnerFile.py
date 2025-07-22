from PIL import Image, ImageTk
import customtkinter as ctk
import requests
from datetime import datetime
import re
import os
import sys

import os
from config import API_KEY # <-- This gets your secret key

# This finds your new 'assets' folder automatically!
script_dir = os.path.dirname(os.path.abspath(__file__))
BG_IMAGE_PATH = os.path.join(script_dir, "assets", "background.png")
ICON_PATHS = {
    'sun': os.path.join(script_dir, "assets", "sun.png"),
    'moon': os.path.join(script_dir, "assets", "moon.png")
}

# --- Color Scheme ---
MAIN_BG = "#87CEEB" # Light Sky Blue
TEXT_COLOR = "#2B2B2B" # Dark Gray
ACCENT_COLOR = "#4B8BBE" # Steel Blue
ERROR_COLOR = "#FF6B6B" # Light Red for errors
USER_MSG_BG = "#E0F7FA" # Very light cyan for user chat messages
BOT_MSG_BG = "#FFFFFF" # White for bot chat messages
CHAT_HISTORY_BG = "#F0F8FF" # AliceBlue (light background for chat history)

# --- CTk Settings ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- WeatherChatBot Class (No changes) ---
class WeatherChatBot:
    def __init__(self, weather_app):
        self.app = weather_app

    def process_message(self, message):
        message = message.lower().strip()
        response = ""
        city_to_query = None

        extracted_city = self._extract_city(message)
        if extracted_city:
            city_to_query = extracted_city
        elif self.app.last_city:
            city_to_query = self.app.last_city
        else:
            if any(word in message for word in ["temperature", "rain", "wind", "sun", "weather"]):
                 return "Please specify a city first (e.g., 'temperature in London' or search for a city)."

        if any(word in message for word in ["hi", "hello", "hey", "greetings"]):
            response = "Hello! How can I help you with the weather today?"

        elif "temperature" in message or "how hot" in message or "how cold" in message:
            if city_to_query:
                temp = self._get_current_data(city_to_query, 'temp_c')
                response = f"The current temperature in {city_to_query.capitalize()} is {temp}°C." if temp != "N/A" else f"Sorry, I couldn't get the temperature for {city_to_query.capitalize()}."

        elif "rain" in message or "precipitation" in message:
            if city_to_query:
                chance = self._get_forecast_data(city_to_query, 'daily_chance_of_rain')
                response = f"The chance of rain in {city_to_query.capitalize()} today is {chance}%." if chance != "N/A" else f"Sorry, I couldn't get the rain forecast for {city_to_query.capitalize()}."

        elif "wind" in message:
            if city_to_query:
                wind = self._get_current_data(city_to_query, 'wind_kph')
                response = f"The current wind speed in {city_to_query.capitalize()} is {wind} km/h." if wind != "N/A" else f"Sorry, I couldn't get the wind speed for {city_to_query.capitalize()}."

        elif "sun" in message:
            if city_to_query:
                if "rise" in message:
                    time = self._get_astro_data(city_to_query, 'sunrise')
                    response = f"Sunrise in {city_to_query.capitalize()} is at {time}." if time != "N/A" else f"Sorry, I couldn't get the sunrise time for {city_to_query.capitalize()}."
                elif "set" in message:
                    time = self._get_astro_data(city_to_query, 'sunset')
                    response = f"Sunset in {city_to_query.capitalize()} is at {time}." if time != "N/A" else f"Sorry, I couldn't get the sunset time for {city_to_query.capitalize()}."
                else:
                     response = "Are you asking about sunrise or sunset?"

        elif "weather" in message or "forecast" in message:
             if city_to_query:
                 condition = self._get_current_data(city_to_query, 'condition', sub_key='text')
                 response = f"The current condition in {city_to_query.capitalize()} is '{condition}'." if condition != "N/A" else f"Sorry, I couldn't get the current conditions for {city_to_query.capitalize()}."

        if not response:
            response = "I can tell you about temperature, rain, wind, or sun times for a city. How can I help?"

        return response

    def _extract_city(self, message):
        match = re.search(r'\b(?:in|for|at)\s+([a-zA-Z\s\-]+)(?:\?|$|\.)', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _fetch_helper(self, city, endpoint):
        try:
            if city == self.app.last_city:
                 if endpoint == "current" and self.app.current_data: return self.app.current_data
                 if endpoint == "forecast" and self.app.forecast_data: return self.app.forecast_data
                 if endpoint == "astronomy" and self.app.astro_data: return self.app.astro_data
            return self.app.fetch_weather_data(city, endpoint)
        except Exception as e:
            print(f"Chatbot fetch error for {city} ({endpoint}): {e}")
            if self.app and hasattr(self.app, '_add_chat_message'):
                 self.app._add_chat_message(f"Bot: ❌ Sorry, couldn't fetch {endpoint} data for {city.capitalize()}.", is_user=False)
            return None

    def _get_current_data(self, city, field, sub_key=None):
        data = self._fetch_helper(city, "current")
        if data and 'current' in data:
            if sub_key:
                 if field in data['current'] and isinstance(data['current'][field], dict) and sub_key in data['current'][field]:
                      return data['current'][field][sub_key]
            elif field in data['current']:
                return data['current'][field]
        return "N/A"

    def _get_forecast_data(self, city, field):
        data = self._fetch_helper(city, "forecast")
        if data and 'forecast' in data and 'forecastday' in data['forecast'] and len(data['forecast']['forecastday']) > 0:
            today_forecast = data['forecast']['forecastday'][0]
            if 'day' in today_forecast and field in today_forecast['day']:
                 return today_forecast['day'][field]
        return "N/A"

    def _get_astro_data(self, city, field):
        data = self._fetch_helper(city, "astronomy")
        if data and 'astronomy' in data and 'astro' in data['astronomy'] and field in data['astronomy']['astro']:
             return data['astronomy']['astro'][field]
        return "N/A"

# --- WeatherApp Class (Changes in color usage) ---
class WeatherApp:
    def __init__(self):
        self.app = None
        self.last_city = None
        self.chatbot = None
        self.bg_label = None
        self.bg_image_tk = None
        self.original_bg = None
        self.current_data = None
        self.forecast_data = None
        self.astro_data = None
        self.ui_elements = {
            "current": {}, "hourly": [], "daily": [], "astro": {}, "chat": []
        }
        self.initialize_app()

    def initialize_app(self):
        try:
            self.verify_api_key()
            self.verify_resources()
            self.check_connection()

            self.app = ctk.CTk()
            self.app.title("WeatherWise")
            self.app.geometry("1200x800")
            self.app.minsize(1000, 700)
            self.chatbot = WeatherChatBot(self)
            self.setup_background()
            self.setup_main_ui()
            self.update_time()
            self.app.mainloop()

        except FileNotFoundError as e:
             print(f"Initialization failed: Missing required resource file.")
             print(f"Details: {e}")
             try:
                  import tkinter.messagebox
                  tkinter.messagebox.showerror("Initialization Error", f"Failed to start: Missing Resource File\n\n{e}\n\nPlease ensure the file exists at the specified absolute path.")
             except ImportError: pass
             sys.exit(1)
        except ValueError as e:
             print(f"Initialization failed: Configuration error.")
             print(f"Details: {e}")
             try:
                  import tkinter.messagebox
                  tkinter.messagebox.showerror("Initialization Error", f"Failed to start: Configuration Error\n\n{e}")
             except ImportError: pass
             sys.exit(1)
        except requests.exceptions.ConnectionError as e:
             print(f"Initialization failed: Network error.")
             print(f"Details: {e}")
             try:
                  import tkinter.messagebox
                  tkinter.messagebox.showerror("Initialization Error", f"Failed to start: Network Error\n\n{e}\n\nPlease check your internet connection.")
             except ImportError: pass
             sys.exit(1)
        except Exception as e:
            # Catch other errors like the invalid color name
            print(f"An unexpected error occurred during initialization: {str(e)}")
            try:
                 import tkinter.messagebox
                 # Display the actual error message
                 tkinter.messagebox.showerror("Initialization Error", f"An unexpected error occurred:\n\n{e}")
            except ImportError: pass
            if self.app:
                 try: self.app.destroy()
                 except: pass
            sys.exit(1)

    def verify_api_key(self):
         if not API_KEY or not re.match(r"^[a-zA-Z0-9]{30}$", API_KEY):
              raise ValueError("Invalid or missing API Key format in configuration.")

    def verify_resources(self):
        missing_files = []
        required_files = [BG_IMAGE_PATH] + list(ICON_PATHS.values())
        for f_path in required_files:
            if not os.path.exists(f_path):
                missing_files.append(f_path)
        if missing_files:
            raise FileNotFoundError(f"Missing required file(s) at specified path(s): {', '.join(missing_files)}")

    def check_connection(self):
        try:
            test_url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q=London"
            response = requests.get(test_url, timeout=10)
            if response.status_code == 401 or response.status_code == 403:
                 raise ValueError("Invalid API key or permission issue.")
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise requests.exceptions.ConnectionError("Connection timed out.")
        except requests.exceptions.ConnectionError:
             raise requests.exceptions.ConnectionError("Network error.")
        except requests.exceptions.HTTPError as e:
             print(f"Warning: API check status {response.status_code}.")

    def setup_background(self):
        try:
            self.original_bg = Image.open(BG_IMAGE_PATH)
            self.bg_label = ctk.CTkLabel(self.app, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.app.after(100, self.update_background)
            self.app.bind("<Configure>", self.update_background, add='+')
        except Exception as e:
            print(f"Error loading background image: {str(e)}")
            self.app.configure(fg_color=MAIN_BG)

    def update_background(self, event=None):
        if not self.original_bg or not self.bg_label: return
        try:
            width = self.app.winfo_width()
            height = self.app.winfo_height()
            if width == 0 or height == 0: return
            resized_image = self.original_bg.resize((width, height), Image.Resampling.LANCZOS)
            self.bg_image_tk = ctk.CTkImage(light_image=resized_image, size=(width, height))
            self.bg_label.configure(image=self.bg_image_tk)
            self.bg_label.lower()
        except Exception as e: pass

    def setup_main_ui(self):
        self.main_frame = ctk.CTkFrame(
            self.app,
            fg_color=MAIN_BG, # USE SOLID COLOR
            corner_radius=20,
            border_width=1,
            border_color=ACCENT_COLOR
        )
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95, relheight=0.9)
        self.setup_header()
        self.setup_tabs()

    def setup_header(self):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(pady=15, padx=30, fill="x")
        self.location_entry = ctk.CTkEntry(
            header_frame, placeholder_text="Enter city name...", width=350, height=40,
            font=("Arial", 15), fg_color="white", text_color=TEXT_COLOR,
            border_color=ACCENT_COLOR, border_width=1
        )
        self.location_entry.pack(side="left", padx=(0, 10), fill='x', expand=True)
        self.location_entry.bind("<Return>", self.update_weather_wrapper)
        self.search_btn = ctk.CTkButton(
            header_frame, text="Search", command=self.update_weather_wrapper, width=100, height=40,
            font=("Arial", 15, "bold"), fg_color=ACCENT_COLOR, hover_color="#3A7BA0", text_color="white"
        )
        self.search_btn.pack(side="left", padx=10)
        self.time_label = ctk.CTkLabel(
            header_frame, text="--:--", font=("Arial", 28, "bold"), text_color=TEXT_COLOR, width=80
        )
        self.time_label.pack(side="right", padx=(20, 0))

    def setup_tabs(self):
        self.notebook = ctk.CTkTabview(
            self.main_frame,
            fg_color=MAIN_BG, # USE SOLID COLOR
            text_color=TEXT_COLOR,
            segmented_button_selected_color=ACCENT_COLOR,
            segmented_button_selected_hover_color="#3A7BA0",
            segmented_button_unselected_color=MAIN_BG, # USE SOLID COLOR
            segmented_button_unselected_hover_color=MAIN_BG,
            corner_radius=10,
            border_width=1,
            border_color=ACCENT_COLOR
        )
        self.notebook.pack(pady=(0, 20), padx=30, fill="both", expand=True)
        self.tab_current = self.notebook.add("Current")
        self.tab_hourly = self.notebook.add("Hourly")
        self.tab_daily = self.notebook.add("Daily")
        self.tab_astro = self.notebook.add("Astronomy")
        self.tab_chat = self.notebook.add("Chat")
        self.setup_current_tab(self.tab_current)
        self.setup_hourly_tab(self.tab_hourly)
        self.setup_daily_tab(self.tab_daily)
        self.setup_astro_tab(self.tab_astro)
        self.setup_chat_tab(self.tab_chat)
        self.notebook.set("Current")

    def setup_current_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self.ui_elements["current"]["icon"] = ctk.CTkLabel(parent, text="")
        self.ui_elements["current"]["icon"].grid(row=0, column=0, pady=(20, 10))
        self.ui_elements["current"]["temp"] = ctk.CTkLabel(parent, text="--°C", font=("Arial", 60, "bold"), text_color=TEXT_COLOR)
        self.ui_elements["current"]["temp"].grid(row=1, column=0, pady=0, sticky='n')
        self.ui_elements["current"]["condition"] = ctk.CTkLabel(parent, text="Enter a city to start", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["current"]["condition"].grid(row=2, column=0, pady=(0, 20))
        metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        metrics_frame.grid(row=3, column=0, pady=20, sticky="ew")
        metrics_frame.grid_columnconfigure((0, 1), weight=1)
        self.ui_elements["current"]["humidity"] = ctk.CTkLabel(metrics_frame, text="💧 Humidity: --%", font=("Arial", 16), text_color=TEXT_COLOR)
        self.ui_elements["current"]["humidity"].grid(row=0, column=0, padx=10, pady=8, sticky='e')
        self.ui_elements["current"]["wind"] = ctk.CTkLabel(metrics_frame, text="🌬️ Wind: -- km/h", font=("Arial", 16), text_color=TEXT_COLOR)
        self.ui_elements["current"]["wind"].grid(row=0, column=1, padx=10, pady=8, sticky='w')
        self.ui_elements["current"]["pressure"] = ctk.CTkLabel(metrics_frame, text="🌫️ Pressure: -- mb", font=("Arial", 16), text_color=TEXT_COLOR)
        self.ui_elements["current"]["pressure"].grid(row=1, column=0, padx=10, pady=8, sticky='e')
        self.ui_elements["current"]["visibility"] = ctk.CTkLabel(metrics_frame, text="👁️ Visibility: -- km", font=("Arial", 16), text_color=TEXT_COLOR)
        self.ui_elements["current"]["visibility"].grid(row=1, column=1, padx=10, pady=8, sticky='w')
        self.load_weather_icon(ICON_PATHS.get('sun'), size=(120, 120))

    def setup_hourly_tab(self, parent):
        self.hourly_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.hourly_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_daily_tab(self, parent):
        self.daily_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.daily_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_astro_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.astro_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.astro_frame.grid(row=0, column=0, rowspan=5, pady=20)
        self.ui_elements["astro"]["sunrise"] = ctk.CTkLabel(self.astro_frame, text="🌅 Sunrise: --:--", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["sunrise"].pack(pady=12)
        self.ui_elements["astro"]["sunset"] = ctk.CTkLabel(self.astro_frame, text="🌇 Sunset: --:--", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["sunset"].pack(pady=12)
        self.ui_elements["astro"]["moonrise"] = ctk.CTkLabel(self.astro_frame, text="🌄 Moonrise: --:--", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["moonrise"].pack(pady=12)
        self.ui_elements["astro"]["moonset"] = ctk.CTkLabel(self.astro_frame, text="🌃 Moonset: --:--", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["moonset"].pack(pady=12)
        self.ui_elements["astro"]["moon_phase"] = ctk.CTkLabel(self.astro_frame, text="🌖 Moon Phase: --", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["moon_phase"].pack(pady=12)
        self.ui_elements["astro"]["moon_illumination"] = ctk.CTkLabel(self.astro_frame, text="🌕 Illumination: --%", font=("Arial", 20), text_color=TEXT_COLOR)
        self.ui_elements["astro"]["moon_illumination"].pack(pady=12)

    def setup_chat_tab(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        self.chat_history = ctk.CTkScrollableFrame(parent,
                                                fg_color=CHAT_HISTORY_BG # USE SOLID COLOR
                                                )
        self.chat_history.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        input_frame = ctk.CTkFrame(parent, fg_color="transparent")
        input_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)
        self.chat_input = ctk.CTkEntry(
            input_frame, placeholder_text="Ask about weather...", font=("Arial", 14),
            fg_color="white", text_color=TEXT_COLOR, height=35, border_color=ACCENT_COLOR, border_width=1
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.chat_input.bind("<Return>", self.process_chat_input_wrapper)
        send_btn = ctk.CTkButton(
            input_frame, text="Send", command=self.process_chat_input_wrapper, width=80, height=35,
            fg_color=ACCENT_COLOR, hover_color="#3A7BA0", text_color="white", font=("Arial", 14, "bold")
        )
        send_btn.grid(row=0, column=1, sticky="e")
        self._add_chat_message("Bot: Hello! Ask me about the weather...", is_user=False)

    def update_time(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        self.app.after(1000, self.update_time)

    def update_weather_wrapper(self, event=None):
        self.show_loading(True)
        self.app.after(50, self.update_weather)

    def update_weather(self):
        city = self.location_entry.get().strip()
        if not city:
            self.show_error("Please enter a city name.")
            self.show_loading(False)
            return
        try:
            self.current_data = self.fetch_weather_data(city, "current")
            self.forecast_data = self.fetch_weather_data(city, "forecast")
            self.astro_data = self.fetch_weather_data(city, "astronomy")
            self.last_city = city.capitalize()
            self.clear_ui_data()
            self.update_current_tab()
            self.update_hourly_tab()
            self.update_daily_tab()
            self.update_astro_tab()
            self._add_chat_message(f"Bot: Showing weather information for {self.last_city}.", is_user=False)
        except requests.exceptions.HTTPError as e:
             if e.response.status_code == 400: self.show_error(f"City not found: '{city}'. Check spelling.")
             else: self.show_error(f"API Error: {e.response.status_code}. Could not fetch data.")
        except requests.exceptions.ConnectionError as e: self.show_error(f"Network Error: Check connection. ({e})")
        except Exception as e:
            self.show_error(f"Failed to update weather: {str(e)}")
            print(f"Detailed error: {e}")
        finally: self.show_loading(False)

    def fetch_weather_data(self, city, endpoint):
        base_url = "http://api.weatherapi.com/v1/"
        endpoints = {
            "current": f"current.json?key={API_KEY}&q={city}",
            "forecast": f"forecast.json?key={API_KEY}&q={city}&days=7",
            "astronomy": f"astronomy.json?key={API_KEY}&q={city}"
        }
        if endpoint not in endpoints: raise ValueError(f"Invalid API endpoint: {endpoint}")
        try:
            response = requests.get(base_url + endpoints[endpoint], timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout: raise requests.exceptions.ConnectionError(f"API request timed out.")
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.ConnectionError): raise requests.exceptions.ConnectionError(f"Network error: {e}")
            raise e

    def load_weather_icon(self, icon_path, size=(100, 100)):
        try:
             if not icon_path or not os.path.exists(icon_path):
                  # If placeholder path is defined, use it, otherwise show '?'
                  placeholder_path = ICON_PATHS.get('placeholder')
                  if placeholder_path and os.path.exists(placeholder_path):
                        print(f"Warning: Icon '{icon_path}' not found. Using placeholder.")
                        img = Image.open(placeholder_path)
                  else:
                        print(f"Error: Icon path not found or invalid: {icon_path}. Placeholder missing or undefined.")
                        self.ui_elements["current"]["icon"].configure(image=None, text="?")
                        return
             else:
                  img = Image.open(icon_path)

             ctk_img = ctk.CTkImage(light_image=img, size=size)
             self.ui_elements["current"]["icon"].configure(image=ctk_img, text="")
        except Exception as e:
             print(f"Error loading icon '{icon_path}': {e}")
             self.ui_elements["current"]["icon"].configure(image=None, text="?")

    def update_current_tab(self):
        if not self.current_data or 'current' not in self.current_data or 'location' not in self.current_data: return
        current = self.current_data['current']
        location = self.current_data['location']
        self.ui_elements["current"]["temp"].configure(text=f"{current.get('temp_c', '--')}°C")
        self.ui_elements["current"]["condition"].configure(text=current.get('condition', {}).get('text', 'N/A'))
        self.ui_elements["current"]["humidity"].configure(text=f"💧 Humidity: {current.get('humidity', '--')}%")
        self.ui_elements["current"]["wind"].configure(text=f"🌬️ Wind: {current.get('wind_kph', '--')} km/h")
        self.ui_elements["current"]["pressure"].configure(text=f"🌫️ Pressure: {current.get('pressure_mb', '--')} mb")
        self.ui_elements["current"]["visibility"].configure(text=f"👁️ Visibility: {current.get('vis_km', '--')} km")
        try:
             local_time_str = location.get('localtime', '')
             local_dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M")
             self.time_label.configure(text=local_dt.strftime("%H:%M"))
        except ValueError: pass
        is_day = current.get('is_day', 1)
        icon_key = 'sun' if is_day else 'moon'
        self.load_weather_icon(ICON_PATHS.get(icon_key), size=(120, 120))

    def update_hourly_tab(self):
        for widget in self.hourly_scroll.winfo_children(): widget.destroy()
        self.ui_elements["hourly"].clear()
        if not self.forecast_data or 'forecast' not in self.forecast_data or \
           'forecastday' not in self.forecast_data['forecast'] or \
           len(self.forecast_data['forecast']['forecastday']) == 0 or \
           'hour' not in self.forecast_data['forecast']['forecastday'][0]:
            ctk.CTkLabel(self.hourly_scroll, text="Hourly data not available.", text_color=TEXT_COLOR).pack(pady=20)
            return
        hours = self.forecast_data['forecast']['forecastday'][0]['hour']
        header_frame = ctk.CTkFrame(self.hourly_scroll, fg_color=ACCENT_COLOR, corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 5), padx=5)
        ctk.CTkLabel(header_frame, text="Time", width=70, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        ctk.CTkLabel(header_frame, text="Temp", width=60, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        ctk.CTkLabel(header_frame, text="Condition", font=("Arial", 13, "bold"), text_color="white", anchor='w').pack(side="left", padx=10, pady=3, fill='x', expand=True)
        ctk.CTkLabel(header_frame, text="Wind (km/h)", width=100, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        self.ui_elements["hourly"].append(header_frame)
        for i, hour in enumerate(hours):
            try: time_str = datetime.strptime(hour.get('time', ''), "%Y-%m-%d %H:%M").strftime("%H:%M")
            except ValueError: time_str = "--:--"
            temp, condition, wind = hour.get('temp_c', '-'), hour.get('condition', {}).get('text', 'N/A'), hour.get('wind_kph', '-')
            bg_color = "white" if i % 2 == 0 else "#F0F0F0"
            frame = ctk.CTkFrame(self.hourly_scroll, corner_radius=6, fg_color=bg_color)
            frame.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(frame, text=time_str, width=70, font=("Arial", 14), text_color=TEXT_COLOR, anchor='w').pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(frame, text=f"{temp}°C", width=60, font=("Arial", 14, "bold"), text_color=TEXT_COLOR, anchor='w').pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(frame, text=condition, font=("Arial", 14), text_color=TEXT_COLOR, anchor='w', justify='left').pack(side="left", padx=10, pady=4, fill='x', expand=True)
            ctk.CTkLabel(frame, text=f"{wind}", width=100, font=("Arial", 14), text_color=TEXT_COLOR, anchor='center').pack(side="left", padx=10, pady=4)
            self.ui_elements["hourly"].append(frame)

    def update_daily_tab(self):
        for widget in self.daily_scroll.winfo_children(): widget.destroy()
        self.ui_elements["daily"].clear()
        if not self.forecast_data or 'forecast' not in self.forecast_data or \
           'forecastday' not in self.forecast_data['forecast']:
            ctk.CTkLabel(self.daily_scroll, text="Daily data not available.", text_color=TEXT_COLOR).pack(pady=20)
            return
        days = self.forecast_data['forecast']['forecastday']
        header_frame = ctk.CTkFrame(self.daily_scroll, fg_color=ACCENT_COLOR, corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 5), padx=5)
        ctk.CTkLabel(header_frame, text="Date", width=120, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        ctk.CTkLabel(header_frame, text="Temp (°C)", width=120, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        ctk.CTkLabel(header_frame, text="Condition", font=("Arial", 13, "bold"), text_color="white", anchor='w').pack(side="left", padx=10, pady=3, fill='x', expand=True)
        ctk.CTkLabel(header_frame, text="Rain (%)", width=80, font=("Arial", 13, "bold"), text_color="white").pack(side="left", padx=10, pady=3)
        self.ui_elements["daily"].append(header_frame)
        for i, day_data in enumerate(days):
            day_info = day_data.get('day', {})
            try: date_str = datetime.strptime(day_data.get('date', ''), "%Y-%m-%d").strftime("%a, %d %b")
            except ValueError: date_str = "---"
            max_temp, min_temp = day_info.get('maxtemp_c', '-'), day_info.get('mintemp_c', '-')
            condition, rain_chance = day_info.get('condition', {}).get('text', 'N/A'), day_info.get('daily_chance_of_rain', '-')
            bg_color = "white" if i % 2 == 0 else "#F0F0F0"
            frame = ctk.CTkFrame(self.daily_scroll, corner_radius=6, fg_color=bg_color)
            frame.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(frame, text=date_str, width=120, font=("Arial", 14), text_color=TEXT_COLOR, anchor='w').pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(frame, text=f"↑{max_temp}° ↓{min_temp}°", width=120, font=("Arial", 14, "bold"), text_color=TEXT_COLOR, anchor='w').pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(frame, text=condition, font=("Arial", 14), text_color=TEXT_COLOR, anchor='w', justify='left').pack(side="left", padx=10, pady=4, fill='x', expand=True)
            ctk.CTkLabel(frame, text=f"{rain_chance}%", width=80, font=("Arial", 14), text_color=TEXT_COLOR, anchor='center').pack(side="left", padx=10, pady=4)
            self.ui_elements["daily"].append(frame)

    def update_astro_tab(self):
        if not self.astro_data or 'astronomy' not in self.astro_data or 'astro' not in self.astro_data['astronomy']:
             self.ui_elements["astro"]["sunrise"].configure(text="🌅 Sunrise: --:--")
             self.ui_elements["astro"]["sunset"].configure(text="🌇 Sunset: --:--")
             self.ui_elements["astro"]["moonrise"].configure(text="🌄 Moonrise: --:--")
             self.ui_elements["astro"]["moonset"].configure(text="🌃 Moonset: --:--")
             self.ui_elements["astro"]["moon_phase"].configure(text="🌖 Moon Phase: --")
             self.ui_elements["astro"]["moon_illumination"].configure(text="🌕 Illumination: --%")
             return
        astro = self.astro_data['astronomy']['astro']
        self.ui_elements["astro"]["sunrise"].configure(text=f"🌅 Sunrise: {astro.get('sunrise', '--:--')}")
        self.ui_elements["astro"]["sunset"].configure(text=f"🌇 Sunset: {astro.get('sunset', '--:--')}")
        self.ui_elements["astro"]["moonrise"].configure(text=f"🌄 Moonrise: {astro.get('moonrise', '--:--')}")
        self.ui_elements["astro"]["moonset"].configure(text=f"🌃 Moonset: {astro.get('moonset', '--:--')}")
        self.ui_elements["astro"]["moon_phase"].configure(text=f"🌖 Moon Phase: {astro.get('moon_phase', 'N/A')}")
        self.ui_elements["astro"]["moon_illumination"].configure(text=f"🌕 Illumination: {astro.get('moon_illumination', '--')}%")

    def process_chat_input_wrapper(self, event=None):
         message = self.chat_input.get().strip()
         if not message: return
         self.chat_input.delete(0, "end")
         self._add_chat_message("You: " + message, is_user=True)
         response = self.chatbot.process_message(message)
         self._add_chat_message("Bot: " + response, is_user=False)
         self.app.after(50, lambda: self.chat_history._parent_canvas.yview_moveto(1.0))

    def _add_chat_message(self, text, is_user=False):
        bubble_color = USER_MSG_BG if is_user else BOT_MSG_BG
        text_align = "left"
        frame_anchor = "w"
        padx = (5, 60) if is_user else (5, 5)
        is_error = text.startswith("Bot: ❌ Error:")
        if is_error:
            bubble_color = ERROR_COLOR # USE SOLID COLOR
            padx = (5, 5)
        frame = ctk.CTkFrame(self.chat_history, fg_color=bubble_color, corner_radius=12)
        frame.pack(fill="x", pady=(2, 5), padx=padx, anchor=frame_anchor)
        try: wrap_width = max(100, self.chat_history.winfo_width() - padx[0] - padx[1] - 20)
        except Exception: wrap_width = 500
        label = ctk.CTkLabel(frame, text=text, wraplength=wrap_width, justify=text_align,
                           font=("Arial", 14), text_color=TEXT_COLOR, anchor="w")
        label.pack(padx=10, pady=6, fill="x", expand=True)
        self.ui_elements["chat"].append(frame)
        self.app.after(50, lambda: self.chat_history._parent_canvas.yview_moveto(1.0))
        self.chat_history.bind("<Configure>", lambda e, lbl=label, p=padx: self._update_wraplength(e, lbl, p))

    def _update_wraplength(self, event, label, padding):
        try:
             new_wraplength = max(100, event.width - padding[0] - padding[1] - 20)
             label.configure(wraplength=new_wraplength)
        except Exception: pass

    def clear_ui_data(self):
        self.ui_elements["current"]["temp"].configure(text="--°C")
        self.ui_elements["current"]["condition"].configure(text="Loading...")
        self.ui_elements["current"]["humidity"].configure(text="💧 Humidity: --%")
        self.ui_elements["current"]["wind"].configure(text="🌬️ Wind: -- km/h")
        self.ui_elements["current"]["pressure"].configure(text="🌫️ Pressure: -- mb")
        self.ui_elements["current"]["visibility"].configure(text="👁️ Visibility: -- km")
        self.load_weather_icon(ICON_PATHS.get('sun'), size=(120, 120)) # Attempt default icon load
        for widget in self.hourly_scroll.winfo_children(): widget.destroy()
        self.ui_elements["hourly"].clear()
        ctk.CTkLabel(self.hourly_scroll, text="Loading hourly data...", text_color=TEXT_COLOR).pack(pady=20)
        for widget in self.daily_scroll.winfo_children(): widget.destroy()
        self.ui_elements["daily"].clear()
        ctk.CTkLabel(self.daily_scroll, text="Loading daily data...", text_color=TEXT_COLOR).pack(pady=20)
        self.ui_elements["astro"]["sunrise"].configure(text="🌅 Sunrise: --:--")
        self.ui_elements["astro"]["sunset"].configure(text="🌇 Sunset: --:--")
        self.ui_elements["astro"]["moonrise"].configure(text="🌄 Moonrise: --:--")
        self.ui_elements["astro"]["moonset"].configure(text="🌃 Moonset: --:--")
        self.ui_elements["astro"]["moon_phase"].configure(text="🌖 Moon Phase: --")
        self.ui_elements["astro"]["moon_illumination"].configure(text="🌕 Illumination: --%")

    def show_loading(self, show=True):
        if show:
            self.search_btn.configure(text="...", state="disabled")
            self.location_entry.configure(state="disabled")
        else:
            self.search_btn.configure(text="Search", state="normal")
            self.location_entry.configure(state="normal")
            for widget in self.hourly_scroll.winfo_children():
                 if isinstance(widget, ctk.CTkLabel) and "Loading" in widget.cget("text"): widget.destroy()
            for widget in self.daily_scroll.winfo_children():
                 if isinstance(widget, ctk.CTkLabel) and "Loading" in widget.cget("text"): widget.destroy()

    def show_error(self, message):
        error_message = f"Bot: ❌ Error: {message}"
        self._add_chat_message(error_message, is_user=False)
        print(f"Error Displayed: {message}")

# --- Main Execution Block ---
if __name__ == "__main__":
    try:
        app = WeatherApp()
    except Exception as e:
        print(f"FATAL: Application failed to initialize.")
        print(f"Error details: {e}")
        try:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Fatal Error", f"Application failed to initialize:\n\n{e}")
        except ImportError:
             print("Tkinter not available to show error dialog.")
        input("Press Enter to exit...")
        sys.exit(1)