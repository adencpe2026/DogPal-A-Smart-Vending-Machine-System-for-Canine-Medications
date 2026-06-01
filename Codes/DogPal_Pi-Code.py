"""
DogPal is a smart vending machine system for canine medications developed by the Cool Pals Group,
Batch 2026 Computer Engineering (CPE) students. To support documentation, maintenance, and future development,
the project's source codes were uploaded to a GitHub repository for future developers, researchers, and CPE students who may continue or enhance the system.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
from ultralytics import YOLO
import os
import time
import platform
import pygame
import threading
from datetime import datetime
import serial
import queue

# Hardware imports (only on Raspberry Pi)
HARDWARE_AVAILABLE = False
PICAMERA_AVAILABLE = False
try:
    if platform.machine().startswith('arm') or platform.machine().startswith('aarch'):
        import board
        import busio
        from adafruit_pca9685 import PCA9685

        HARDWARE_AVAILABLE = True
        try:
            from picamera2 import Picamera2
            PICAMERA_AVAILABLE = True
            print("Picamera2 detected")
        except ImportError:
            print("Picamera2 not available - using USB camera")
except ImportError:
    print("Hardware libraries not available - running in simulation mode")


def detect_arduino_port():
    """Auto-detect Arduino serial port for Windows or Linux/Raspberry Pi."""
    if platform.system() == "Windows":
        return "COM14"

    possible_ports = [
        "/dev/ttyACM0",
        "/dev/ttyACM1",
        "/dev/ttyUSB0",
        "/dev/ttyUSB1"
    ]

    for port in possible_ports:
        if os.path.exists(port):
            return port

    return "/dev/ttyACM0"


KNOWN_MEDS = [
    "Co-Amoxiclav",
    "Meloxicam",
    "Tolfenamic Acid",
    "Dermclens Spray",
    "NexGard",
    "Immunol Tablets",
    "Vetracin Gold",
    "Dextrose Powder",
    "Moxifloxacin",
    "Pet Tabs",
    "Petsup Dewormer",
    "Ivermectin",
    "Benadryl",
    "Cetirizine",
    "Fipronil",
    "Nefrotec"
]

PRESCRIPTION_MEDS = [
    "Co-Amoxiclav",
    "Meloxicam",
    "Tolfenamic Acid",
    "Dermclens Spray",
    "Moxifloxacin"
]

OTC_MEDS = [
    "Immunol Tablets",
    "Vetracin Gold",
    "Dextrose Powder",
    "Pet Tabs",
    "Petsup Dewormer",
    "Ivermectin",
    "NexGard",
    "Benadryl",
    "Cetirizine",
    "Fipronil",
    "Nefrotec"
]

CLASS_NAME_MAPPING = {
    "tolfe": "Tolfenamic Acid",
    "moxi": "Moxifloxacin",
    "spray": "Dermclens Spray",
    "derm_spray": "Dermclens Spray",
    "coamox": "Co-Amoxiclav",
    "melo": "Meloxicam",
    "sign": "sign"
}

MED_TO_SLOT = {
    "Immunol Tablets": 1,
    "Nefrotec": 2,
    "Tolfenamic Acid": 3,
    "Dermclens Spray": 4,
    "NexGard": 5,
    "Petsup Dewormer": 6,
    "Vetracin Gold": 7,
    "Dextrose Powder": 8,
    "Moxifloxacin": 9,
    "Pet Tabs": 10,
    "Ivermectin": 11,
    "Meloxicam": 12,
    "Benadryl": 13,
    "Cetirizine": 14,
    "Fipronil": 15,
    "Co-Amoxiclav": 16
}

MEDICINE_PRICES = {
    "Co-Amoxiclav": 80.00,
    "Meloxicam": 300.00,
    "Tolfenamic Acid": 400.00,
    "Dermclens Spray": 320.00,
    "NexGard": 800.00,
    "Immunol Tablets": 350.00,
    "Vetracin Gold": 40.00,
    "Dextrose Powder": 20.00,
    "Moxifloxacin": 200.00,
    "Pet Tabs": 40.00,
    "Petsup Dewormer": 100.00,
    "Ivermectin": 25.00,
    "Benadryl": 55.00,
    "Cetirizine": 160.00,
    "Fipronil": 67.00,
    "Nefrotec": 70.00
}

MEDICINE_SOUND_MAP = {
    "Co-Amoxiclav": "sounds/co_amoxiclav.wav",
    "Meloxicam": "sounds/meloxicam.wav",
    "Tolfenamic Acid": "sounds/tolfenamic_acid.wav",
    "Dermclens Spray": "sounds/dermclens_spray.wav",
    "NexGard": "sounds/nexgard.wav",
    "Immunol Tablets": "sounds/immunol_tablet.wav",
    "Vetracin Gold": "sounds/vetracin_gold.wav",
    "Dextrose Powder": "sounds/dextrose_powder.wav",
    "Moxifloxacin": "sounds/moxifloxacin.wav",
    "Pet Tabs": "sounds/pet_tabs.wav",
    "Petsup Dewormer": "sounds/petsup_dewormer.wav",
    "Ivermectin": "sounds/ivermectin.wav",
    "Benadryl": "sounds/benadryl.wav",
    "Cetirizine": "sounds/cetirizine.wav",
    "Fipronil": "sounds/fipronil.wav",
    "Nefrotec": "sounds/nefrotec.wav"
}

MEDICINE_INFO = {
    "Co-Amoxiclav": {
        "brand": "Dog Pal Veterinary Care",
        "type": "Prescription Medicine",
        "form": "Tablet / Antibiotic",
        "summary": "Broad-spectrum antibiotic used for common bacterial infections in dogs."
    },
    "Meloxicam": {
        "brand": "Dog Pal Veterinary Care",
        "type": "Prescription Medicine",
        "form": "Anti-inflammatory",
        "summary": "Used for pain, swelling, and inflammation relief in dogs."
    },
    "Tolfenamic Acid": {
        "brand": "Dog Pal Veterinary Care",
        "type": "Prescription Medicine",
        "form": "Anti-inflammatory",
        "summary": "Helps manage fever, pain, and inflammation in canine treatment."
    },
    "Dermclens Spray": {
        "brand": "Dog Pal Veterinary Care",
        "type": "Prescription Medicine",
        "form": "Topical Spray",
        "summary": "Topical wound and skin care spray for cleaning and infection support."
    },
    "NexGard": {
        "brand": "NexGard",
        "type": "OTC / Preventive",
        "form": "Chewable Tablet",
        "summary": "Fast-acting flea and tick protection for dogs."
    },
    "Immunol Tablets": {
        "brand": "Immunol",
        "type": "OTC Supplement",
        "form": "Tablet",
        "summary": "Supports immune health and daily wellness in dogs."
    },
    "Vetracin Gold": {
        "brand": "Vetracin",
        "type": "OTC Supplement",
        "form": "Tablet / Supplement",
        "summary": "A nutritional supplement for routine canine health support."
    },
    "Dextrose Powder": {
        "brand": "Dog Pal Essentials",
        "type": "OTC Supplement",
        "form": "Powder",
        "summary": "Provides quick energy support during weakness or recovery."
    },
    "Moxifloxacin": {
        "brand": "Dog Pal Veterinary Care",
        "type": "Prescription Medicine",
        "form": "Antibiotic",
        "summary": "Antibacterial medicine used for selected canine infections."
    },
    "Pet Tabs": {
        "brand": "Pet Tabs",
        "type": "OTC Supplement",
        "form": "Vitamin Tablet",
        "summary": "Daily multivitamin supplement for growth, health, and appetite support."
    },
    "Petsup Dewormer": {
        "brand": "Petsup",
        "type": "OTC Preventive",
        "form": "Tablet / Dewormer",
        "summary": "Helps remove intestinal worms and supports digestive health."
    },
    "Ivermectin": {
        "brand": "Dog Pal Veterinary Care",
        "type": "OTC / Controlled Use",
        "form": "Anti-parasitic",
        "summary": "Used against certain parasites; should be given with proper guidance."
    },
    "Benadryl": {
        "brand": "Benadryl",
        "type": "OTC Medicine",
        "form": "Antihistamine",
        "summary": "Helps relieve allergy symptoms such as itching and mild reactions."
    },
    "Cetirizine": {
        "brand": "Cetirizine",
        "type": "OTC Medicine",
        "form": "Antihistamine",
        "summary": "Used for allergy relief including itching and skin irritation."
    },
    "Fipronil": {
        "brand": "Fipronil",
        "type": "OTC Preventive",
        "form": "Topical Anti-Flea / Tick",
        "summary": "Topical treatment for fleas and ticks with lasting external protection."
    },
    "Nefrotec": {
        "brand": "Nefrotec",
        "type": "OTC Support",
        "form": "Tablet / Renal Support",
        "summary": "Supports kidney health and maintenance care in dogs."
    }
}

SLOT_TO_CH = {i: i - 1 for i in range(1, 17)}

PWM_FREQ = 50
PULSE_STOP_MS = 1.50
PULSE_RUN_MS = 1.30
DISPENSE_SEC = 2.5

ITEMS_PER_PAGE = 4
DETECTED_ITEMS_PER_PAGE = 3

ADMIN_PIN = "6767"


class ArduinoPaymentReader:
    """Reads payment updates, door/alarm status, and IR drop detection from Arduino over serial."""

    def __init__(self, port=None, baudrate=115200):
        self.port = port if port else detect_arduino_port()
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.thread = None

        self.payment_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.drop_queue = queue.Queue()

        self.current_total = 0
        self.main_doors_closed = True
        self.drawer_closed = True

        self.blocked_ir_sensors = set()
        self.drop_detected = False
        self.drop_count = 0

    def update_drop_detected(self):
        self.drop_detected = len(self.blocked_ir_sensors) > 0

    def connect(self):
        try:
            print(f"Using Arduino port: {self.port}")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(1.0)
            self.running = True
            self.thread = threading.Thread(target=self.read_loop, daemon=True)
            self.thread.start()
            print(f"Connected to Arduino on {self.port}")
            return True
        except PermissionError:
            print(f"Arduino connection failed on {self.port}: Access denied. Another app is already using this port.")
            return False
        except Exception as e:
            print(f"Arduino connection failed on {self.port}: {e}")
            return False

    def read_loop(self):
        while self.running and self.ser:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                print("ARDUINO:", line)

                if line.startswith("PAY:"):
                    parts = line.split(":")
                    if len(parts) == 3:
                        inserted = int(parts[1])
                        total = int(parts[2])
                        self.current_total = total
                        self.payment_queue.put(("PAY", inserted, total))

                elif line.startswith("RESET:"):
                    self.current_total = 0
                    self.payment_queue.put(("RESET", 0, 0))

                elif line == "SYSTEM_READY":
                    self.payment_queue.put(("READY", 0, self.current_total))
                    self.status_queue.put(("READY", 0, self.current_total))

                elif line == "ALARM:ONE_OR_MORE_MAIN_SWITCH_OPEN":
                    self.main_doors_closed = False
                    self.status_queue.put(("DOOR_ALARM", 1, 0))

                elif line == "MAIN_SWITCHES_CLOSED":
                    self.main_doors_closed = True
                    self.status_queue.put(("DOOR_SAFE", 0, 0))

                elif line == "DRAWER:OPEN LED:ON":
                    self.drawer_closed = False
                    self.status_queue.put(("DRAWER_OPEN", 1, 0))

                elif line == "DRAWER:CLOSED LED:OFF":
                    self.drawer_closed = True
                    self.status_queue.put(("DRAWER_CLOSED", 0, 0))

                elif line.startswith("DROP:"):
                    try:
                        self.drop_count = int(line.split(":")[1])
                        self.drop_queue.put(("DROP", self.drop_count))
                    except Exception:
                        pass

                elif line.startswith("IR") and ":" in line:
                    try:
                        sensor_name, state = line.split(":", 1)
                        sensor_name = sensor_name.strip()
                        state = state.strip()

                        if state == "BLOCKED":
                            self.blocked_ir_sensors.add(sensor_name)
                        elif state == "CLEAR":
                            self.blocked_ir_sensors.discard(sensor_name)

                        self.update_drop_detected()
                    except Exception:
                        pass

                elif line.startswith("ALARM:SHAKING_DETECTED"):
                    self.status_queue.put(("SHAKE_ALARM", 1, 0))

            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(0.2)

    def reset_total(self):
        self.current_total = 0
        if self.ser:
            try:
                self.ser.write(b"RESET\n")
            except Exception as e:
                print(f"Failed to send RESET to Arduino: {e}")

    def reset_drop_count(self):
        self.drop_count = 0
        self.blocked_ir_sensors.clear()
        self.drop_detected = False
        try:
            while True:
                self.drop_queue.get_nowait()
        except queue.Empty:
            pass

        if self.ser:
            try:
                self.ser.write(b"RESET_DROP\n")
            except Exception as e:
                print(f"Failed to send RESET_DROP to Arduino: {e}")

    def close(self):
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass


class ThermalPrinter:
    """Handles 58mm thermal printer printing through /dev/rfcomm0"""

    def __init__(self, device="/dev/rfcomm0"):
        self.device = device

    def _write(self, data: bytes):
        with open(self.device, "wb") as printer:
            printer.write(data)
            printer.flush()

    def print_receipt(self, medicine_name, price, qty=1):
        total = price * qty
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        line_width = 32

        def center(text):
            return text.center(line_width)

        def money(value):
            return f"PHP {value:,.2f}"

        receipt = []
        receipt.append(b"\x1B\x40")
        receipt.append(b"\x1B\x61\x01")
        receipt.append(b"\x1B\x45\x01")
        receipt.append((center("DOGPAL") + "\n").encode("utf-8"))
        receipt.append(b"\x1B\x45\x00")
        receipt.append((center("Medicine Vendo Machine") + "\n").encode("utf-8"))
        receipt.append((center("Dispensing Receipt") + "\n").encode("utf-8"))
        receipt.append(b"--------------------------------\n")

        receipt.append(b"\x1B\x61\x00")
        receipt.append((f"Date : {now}\n").encode("utf-8"))
        receipt.append((f"Item : {medicine_name}\n").encode("utf-8"))
        receipt.append((f"Qty  : {qty}\n").encode("utf-8"))
        receipt.append((f"Price: {money(price)}\n").encode("utf-8"))
        receipt.append((f"Total: {money(total)}\n").encode("utf-8"))
        receipt.append(b"--------------------------------\n")

        receipt.append(b"\x1B\x61\x01")
        receipt.append((center("Thank you for choosing DOGPAL!") + "\n").encode("utf-8"))
        receipt.append((center("Please keep this receipt.") + "\n").encode("utf-8"))
        receipt.append(b"\n\n\n")

        try:
            self._write(b"".join(receipt))
            print(f"Receipt printed for {medicine_name} x{qty}")
            return True
        except Exception as e:
            print(f"Printer error: {e}")
            return False


class HardwareController:
    """Handles servo control for medicine dispensing"""

    def __init__(self):
        self.pca = None
        if HARDWARE_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.pca = PCA9685(i2c)
                self.pca.frequency = PWM_FREQ
                print("Hardware initialized successfully")
            except Exception as e:
                print(f"Hardware initialization failed: {e}")
                self.pca = None

    def ms_to_16bit(self, ms, freq=PWM_FREQ):
        period_ms = 1000.0 / freq
        return int((ms / period_ms) * 65535)

    def servo_run(self, channel, run_ms=PULSE_RUN_MS, stop_ms=PULSE_STOP_MS, duration=DISPENSE_SEC):
        if self.pca is None:
            print(f"[SIMULATION] Dispensing from channel {channel} for {duration}s")
            time.sleep(duration)
            return True

        try:
            ch = self.pca.channels[channel]
            ch.duty_cycle = self.ms_to_16bit(run_ms)
            time.sleep(duration)
            ch.duty_cycle = self.ms_to_16bit(stop_ms)
            return True
        except Exception as e:
            print(f"Servo error: {e}")
            return False

    def stop_all_servos(self):
        if self.pca is None:
            return

        try:
            for ch in range(16):
                self.pca.channels[ch].duty_cycle = self.ms_to_16bit(PULSE_STOP_MS)
        except Exception as e:
            print(f"Error stopping servos: {e}")


class MedicineDispenserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dog Pal Medicine Dispenser")
        # Raspberry Pi / Tkinter kiosk fullscreen.
        # Do NOT use root.overrideredirect(True) here because it can cause
        # the app to minimize or lose focus when switching frames on Raspberry Pi.
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#1a1a2e")
        # ESC key support: works even when a child widget has focus.
        self.root.bind("<Escape>", self.handle_escape)
        self.root.bind_all("<Escape>", self.handle_escape)
        self.root.bind("<F11>", lambda e: self.keep_root_fullscreen())

        self.hardware = HardwareController()
        self.printer = ThermalPrinter("/dev/rfcomm0")

        arduino_port = detect_arduino_port()
        self.payment_reader = ArduinoPaymentReader(arduino_port, 115200)
        self.payment_connected = self.payment_reader.connect()

        self.sound_available = False
        self.loaded_sounds = {}
        self.door_alarm_sound = None
        self.door_alarm_playing = False

        self.alarm_popup = None
        self.active_popup = None
        self.service_mode_active = False
        self.alarm_authorized = False
        self.alarm_latched = False
        self.entered_pin = ""
        self.pin_mask_var = None
        self.alarm_message_var = None
        self.alarm_pin_feedback_var = None
        self.overlay_action_frame = None
        self.overlay_keypad_frame = None
        self.overlay_logs_frame = None
        self.overlay_bottom_frame = None
        self.pin_box = None
        self.logs_text_widget = None
        self.log_filter_var = None
        self.current_log_filter = "ALL"
        self.btn_alarm_disarm = None
        self.btn_alarm_service = None
        self.btn_exit_service = None

        self.current_drop_count = 0
        self.expected_drop_count = 0

        self.event_logs = []
        self.max_log_entries = 400
        self.app_start_time = time.time()

        try:
            pygame.mixer.init()
            self.default_sound = pygame.mixer.Sound("sounds/default.wav")

            for med, path in MEDICINE_SOUND_MAP.items():
                if os.path.exists(path):
                    self.loaded_sounds[med] = pygame.mixer.Sound(path)

            if os.path.exists("sounds/door_alarm.wav"):
                self.door_alarm_sound = pygame.mixer.Sound("sounds/door_alarm.wav")

            self.sound_available = True
            print("Medicine sound system initialized")
        except Exception as e:
            print("Sound system disabled:", e)

        print("\n=== System Configuration ===")
        print(f"Platform: {platform.machine()}")
        print(f"System: {platform.system()}")
        print(f"Hardware Control: {'Enabled' if HARDWARE_AVAILABLE else 'Simulation'}")
        print(f"Camera: {'Picamera2' if PICAMERA_AVAILABLE else 'USB/Webcam'}")
        print(f"Arduino Port: {arduino_port}")
        print(f"Arduino Payment: {'Connected' if self.payment_connected else 'Not Connected'}")
        print("============================\n")

        self.model = None
        self.load_model()

        self.camera = None
        self.camera_running = False
        self.preview_active = False
        self.video_label = None
        self.current_mode = None
        self.detected_medicines = []
        self.captured_image = None
        self.use_picamera = PICAMERA_AVAILABLE
        self.latest_frame = None

        self.current_page = 0
        self.detected_page = 0
        self.filtered_meds = sorted(KNOWN_MEDS)

        self.confidence_threshold = 0.25

        self.setup_styles()
        self.create_main_layout()
        # Start in Manual mode without opening the camera.
        # On laptops, continuously reading the webcam while the camera panel is hidden
        # can make OTC medicine buttons feel frozen or not clickable.
        # The camera starts only when Image Scan preview is used.
        self.switch_mode('manual')
        self.log_event("SYSTEM", "Application started")
        self.process_arduino_events()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(250, self.keep_root_fullscreen)

    def keep_root_fullscreen(self):
        """Keep the main window fullscreen without using root.overrideredirect()."""
        try:
            self.root.deiconify()
            self.root.attributes("-fullscreen", True)
            self.root.lift()
            self.root.focus_force()
        except Exception as e:
            print(f"Fullscreen restore warning: {e}")

    def make_fullscreen_popup(self, popup, bg="#16213e"):
        """Make a child prompt a true fullscreen overlay with no title bar."""
        try:
            popup.overrideredirect(True)
        except Exception:
            pass

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        popup.geometry(f"{screen_w}x{screen_h}+0+0")
        popup.configure(bg=bg)
        popup.transient(self.root)
        popup.lift()
        popup.attributes("-topmost", True)
        popup.focus_force()
        popup.focus_set()

        try:
            popup.grab_set()
        except Exception:
            pass

        popup.bind("<Escape>", self.handle_escape)
        popup.bind("<Alt-F4>", lambda e: "break")
        popup.protocol("WM_DELETE_WINDOW", lambda: None)
        self.active_popup = popup

    def close_active_popup(self):
        """Close the current fullscreen prompt safely without exiting the app."""
        popup = getattr(self, "active_popup", None)
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.grab_release()
            except Exception:
                pass
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except Exception:
                pass
            self.active_popup = None
            self.keep_root_fullscreen()
            return True
        return False

    def handle_escape(self, event=None):
        """ESC = terminate the whole Dog Pal program immediately."""
        print("ESC pressed - terminating Dog Pal program")

        # Best-effort cleanup before force exit
        try:
            self.log_event("SYSTEM", "ESC pressed - force terminate")
        except Exception:
            pass

        try:
            self.stop_door_alarm()
        except Exception:
            pass

        try:
            self.stop_camera()
        except Exception:
            pass

        try:
            self.hardware.stop_all_servos()
        except Exception:
            pass

        try:
            self.payment_reader.close()
        except Exception:
            pass

        try:
            pygame.mixer.quit()
        except Exception:
            pass

        # Close Tkinter normally first
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

        # Hard kill so fullscreen, popups, grab_set(), and background threads cannot trap the app
        os._exit(0)

    def get_medicine_info(self, medicine):
        default_type = "Prescription Medicine" if medicine in PRESCRIPTION_MEDS else "OTC Medicine"
        return MEDICINE_INFO.get(
            medicine,
            {
                "brand": "Dog Pal",
                "type": default_type,
                "form": "Medicine",
                "summary": "Veterinary medicine for canine care."
            }
        )

    def format_elapsed_time(self):
        elapsed = time.time() - self.app_start_time
        return f"+{elapsed:.1f}s"

    def log_event(self, category, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        elapsed = self.format_elapsed_time()
        entry = f"[{timestamp}] [{elapsed}] [{category}] {message}"
        self.event_logs.append(entry)

        if len(self.event_logs) > self.max_log_entries:
            self.event_logs = self.event_logs[-self.max_log_entries:]

        if self.logs_text_widget is not None:
            self.refresh_logs_view()

    def get_filtered_logs(self):
        if self.current_log_filter == "ALL":
            return self.event_logs
        token = f"[{self.current_log_filter}]"
        return [entry for entry in self.event_logs if token in entry]

    def set_log_filter(self, filter_name):
        self.current_log_filter = filter_name
        if self.log_filter_var is not None:
            self.log_filter_var.set(f"Showing: {filter_name}")
        self.refresh_logs_view()

    def refresh_logs_view(self):
        if self.logs_text_widget is None:
            return

        try:
            filtered_logs = self.get_filtered_logs()

            self.logs_text_widget.config(state='normal')
            self.logs_text_widget.delete("1.0", tk.END)

            if not filtered_logs:
                self.logs_text_widget.insert(tk.END, f"No {self.current_log_filter.lower()} logs available.\n")
            else:
                for entry in filtered_logs:
                    self.logs_text_widget.insert(tk.END, entry + "\n")

            self.logs_text_widget.see(tk.END)
            self.logs_text_widget.config(state='disabled')
        except Exception as e:
            print(f"Failed to refresh logs view: {e}")

    def build_service_logs_panel(self):
        if self.overlay_logs_frame is None:
            return

        for widget in self.overlay_logs_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.overlay_logs_frame,
            text="Logs",
            font=('Segoe UI', 14, 'bold'),
            bg="#7f0000",
            fg="white"
        ).pack(pady=(0, 4))

        filter_bar = tk.Frame(self.overlay_logs_frame, bg="#7f0000")
        filter_bar.pack(pady=(0, 4))

        self.log_filter_var = tk.StringVar(value=f"Showing: {self.current_log_filter}")

        filter_names = ["ALL", "TRANSACTION", "ALARM", "DROP", "SYSTEM"]
        for filter_name in filter_names:
            bg = "#34495e" if self.current_log_filter != filter_name else "#16a085"
            active_bg = "#4a6278" if self.current_log_filter != filter_name else "#1abc9c"

            tk.Button(
                filter_bar,
                text=filter_name,
                command=lambda f=filter_name: self.set_log_filter(f),
                font=('Segoe UI', 9, 'bold'),
                width=11,
                height=1,
                bg=bg,
                fg="white",
                activebackground=active_bg,
                activeforeground="white",
                relief=tk.FLAT
            ).pack(side=tk.LEFT, padx=4)

        tk.Label(
            self.overlay_logs_frame,
            textvariable=self.log_filter_var,
            font=('Segoe UI', 9, 'bold'),
            bg="#7f0000",
            fg="#ffe5e5"
        ).pack(pady=(0, 4))

        logs_box = tk.Frame(self.overlay_logs_frame, bg="#111111", bd=0, relief=tk.FLAT, height=230)
        logs_box.pack(fill=tk.X, expand=False, padx=6, pady=(0, 4))
        logs_box.pack_propagate(False)

        self.logs_text_widget = scrolledtext.ScrolledText(
            logs_box,
            wrap=tk.WORD,
            width=92,
            height=9,
            font=('Consolas', 9),
            bg="#111111",
            fg="#eaeaea",
            insertbackground="white",
            relief=tk.FLAT,
            borderwidth=0
        )
        self.logs_text_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.logs_text_widget.config(state='disabled')

        self.refresh_logs_view()

    def play_medicine_sound(self, medicine):
        if not self.sound_available:
            return
        try:
            sound = self.loaded_sounds.get(medicine, self.default_sound)
            sound.play()
        except Exception as e:
            print(f"Sound error for {medicine}: {e}")

    def start_door_alarm(self):
        if self.service_mode_active:
            return

        if not self.sound_available or self.door_alarm_sound is None:
            print("Door alarm sound file not available")
            return

        if not self.door_alarm_playing:
            try:
                self.door_alarm_sound.play(loops=-1)
                self.door_alarm_playing = True
                print("Door alarm started")
            except Exception as e:
                print(f"Door alarm sound error: {e}")

    def stop_door_alarm(self):
        if not self.sound_available or self.door_alarm_sound is None:
            return

        if self.door_alarm_playing:
            try:
                self.door_alarm_sound.stop()
                self.door_alarm_playing = False
                print("Door alarm stopped")
            except Exception as e:
                print(f"Door alarm stop error: {e}")

    def reset_alarm_auth(self):
        self.alarm_authorized = False
        self.entered_pin = ""
        if self.pin_mask_var is not None:
            self.pin_mask_var.set("")
        if self.alarm_pin_feedback_var is not None:
            self.alarm_pin_feedback_var.set("Enter Admin PIN")
        self.update_alarm_actions()

    def update_alarm_actions(self):
        if self.overlay_action_frame is None:
            return

        if self.service_mode_active:
            if self.btn_alarm_disarm is not None:
                self.btn_alarm_disarm.config(state="disabled")
            if self.btn_alarm_service is not None:
                self.btn_alarm_service.config(state="disabled")

            if self.btn_exit_service is not None:
                if self.payment_reader.main_doors_closed:
                    self.btn_exit_service.config(
                        state="normal",
                        bg="#2c5f8d",
                        activebackground="#3a7dbf",
                        text="EXIT SERVICE MODE"
                    )
                else:
                    self.btn_exit_service.config(
                        state="disabled",
                        bg="#555555",
                        activebackground="#555555",
                        text="CLOSE ALL MAIN DOORS FIRST"
                    )
        else:
            if self.btn_alarm_disarm is not None:
                if self.alarm_authorized and self.payment_reader.main_doors_closed:
                    self.btn_alarm_disarm.config(
                        state="normal",
                        text="Disarm Alarm"
                    )
                else:
                    self.btn_alarm_disarm.config(
                        state="disabled",
                        text="Disarm Alarm"
                    )

            if self.btn_alarm_service is not None:
                self.btn_alarm_service.config(
                    state="normal" if self.alarm_authorized else "disabled",
                    text="Enter Service Mode"
                )

            if self.btn_exit_service is not None:
                self.btn_exit_service.config(
                    state="disabled",
                    bg="#2c5f8d",
                    activebackground="#3a7dbf",
                    text="Exit Service Mode"
                )

    def refresh_alarm_overlay(self):
        if self.alarm_popup is None or not self.alarm_popup.winfo_exists():
            return

        self.alarm_popup.lift()
        self.alarm_popup.attributes("-topmost", True)

        bg = "#7f0000"

        if self.service_mode_active:
            title_text = "SERVICE MODE"
            status_text = "Authorized maintenance mode is active."

            if self.payment_reader.main_doors_closed:
                message_text = (
                    "All main doors are closed.\n\n"
                    "Review logs below or press EXIT SERVICE MODE to return the machine to normal operation."
                )
            else:
                message_text = (
                    "Machine is in service mode.\n\n"
                    "Review logs below.\n"
                    "Close all main doors first, then EXIT SERVICE MODE will become available."
                )
        else:
            title_text = "WARNING"

            if self.payment_reader.main_doors_closed:
                status_text = "All main doors are now closed."
                message_text = (
                    "Alarm is still latched.\n\n"
                    "An authorized person must enter the Admin PIN and press DISARM ALARM.\n"
                    "The warning will not disappear automatically."
                )
            else:
                status_text = "One or more main doors are open."
                message_text = (
                    "Alarm is active.\n\n"
                    "Enter Admin PIN to choose one of these actions:\n"
                    "- Disarm Alarm (only if all doors are closed)\n"
                    "- Enter Service Mode (for authorized maintenance)"
                )

        self.alarm_popup.configure(bg=bg)

        for child in self.alarm_popup.winfo_children():
            try:
                child.configure(bg=bg)
            except Exception:
                pass
            for sub in child.winfo_children():
                try:
                    sub.configure(bg=bg)
                except Exception:
                    pass

        if hasattr(self, "alarm_title_label") and self.alarm_title_label is not None:
            self.alarm_title_label.config(text=title_text, bg=bg)

        if hasattr(self, "alarm_status_label") and self.alarm_status_label is not None:
            self.alarm_status_label.config(text=status_text, bg=bg)

        if self.alarm_message_var is not None:
            self.alarm_message_var.set(message_text)

        if hasattr(self, "alarm_message_label") and self.alarm_message_label is not None:
            self.alarm_message_label.config(bg=bg)

        if hasattr(self, "alarm_container") and self.alarm_container is not None:
            self.alarm_container.config(bg=bg)

        if self.overlay_action_frame is not None:
            self.overlay_action_frame.config(bg=bg)

        if self.overlay_keypad_frame is not None:
            self.overlay_keypad_frame.config(bg=bg)

        if self.overlay_logs_frame is not None:
            self.overlay_logs_frame.config(bg=bg)

        if self.overlay_bottom_frame is not None:
            self.overlay_bottom_frame.config(bg=bg)

        if self.pin_box is not None:
            if self.service_mode_active:
                self.pin_box.pack_forget()
            else:
                self.pin_box.pack(pady=(0, 10))

        if self.overlay_action_frame is not None:
            if self.service_mode_active:
                self.overlay_action_frame.pack_forget()
            else:
                self.overlay_action_frame.pack(pady=(0, 8))

        if self.overlay_keypad_frame is not None:
            if self.service_mode_active:
                self.overlay_keypad_frame.pack_forget()
            else:
                self.overlay_keypad_frame.pack(pady=(0, 8))

        if self.overlay_logs_frame is not None:
            if self.service_mode_active:
                self.overlay_logs_frame.pack(fill=tk.X, expand=False, pady=(4, 4))
                self.build_service_logs_panel()
            else:
                self.overlay_logs_frame.pack_forget()
                self.logs_text_widget = None
                self.log_filter_var = None

        if self.btn_exit_service is not None:
            if self.service_mode_active:
                self.btn_exit_service.pack(pady=(0, 4))
            else:
                self.btn_exit_service.pack_forget()

        self.update_alarm_actions()

    def show_alarm_popup(self):
        if self.alarm_popup is not None and self.alarm_popup.winfo_exists():
            self.refresh_alarm_overlay()
            try:
                self.alarm_popup.grab_set()
            except Exception:
                pass
            return

        self.alarm_popup = tk.Toplevel(self.root)
        self.alarm_popup.overrideredirect(True)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.alarm_popup.geometry(f"{screen_w}x{screen_h}+0+0")

        self.alarm_popup.attributes("-topmost", True)
        self.alarm_popup.configure(bg="#7f0000")
        self.alarm_popup.focus_force()
        self.alarm_popup.focus_set()
        self.alarm_popup.lift()

        try:
            self.alarm_popup.grab_set()
        except Exception:
            pass

        # ESC is intentionally blocked on alarm screen so security is not bypassed.
        self.alarm_popup.bind("<Escape>", self.handle_escape)
        self.alarm_popup.bind("<Alt-F4>", lambda e: "break")
        self.alarm_popup.protocol("WM_DELETE_WINDOW", lambda: None)

        self.pin_mask_var = tk.StringVar(value="")
        self.alarm_message_var = tk.StringVar(value="")
        self.alarm_pin_feedback_var = tk.StringVar(value="Enter Admin PIN")

        self.alarm_container = tk.Frame(self.alarm_popup, bg="#7f0000")
        self.alarm_container.pack(fill=tk.BOTH, expand=True)

        center_panel = tk.Frame(self.alarm_container, bg="#7f0000")
        center_panel.place(relx=0.5, rely=0.53, anchor="center")

        self.alarm_title_label = tk.Label(
            center_panel,
            text="WARNING",
            font=('Segoe UI', 18, 'bold'),
            bg="#7f0000",
            fg="white"
        )
        self.alarm_title_label.pack(pady=(4, 4))

        self.alarm_status_label = tk.Label(
            center_panel,
            text="One or more main doors are open.",
            font=('Segoe UI', 13, 'bold'),
            bg="#7f0000",
            fg="#ffe5e5"
        )
        self.alarm_status_label.pack(pady=(0, 6))

        self.alarm_message_label = tk.Label(
            center_panel,
            textvariable=self.alarm_message_var,
            font=('Segoe UI', 10),
            bg="#7f0000",
            fg="white",
            justify="center",
            wraplength=760
        )
        self.alarm_message_label.pack(pady=(0, 6))

        self.pin_box = tk.Frame(center_panel, bg="#111111", bd=0, relief=tk.FLAT)

        tk.Label(
            self.pin_box,
            text="Admin PIN",
            font=('Segoe UI', 13, 'bold'),
            bg="#111111",
            fg="white"
        ).pack(padx=20, pady=(12, 5))

        tk.Label(
            self.pin_box,
            textvariable=self.pin_mask_var,
            font=('Segoe UI', 20, 'bold'),
            bg="#111111",
            fg="#2ecc71",
            width=12
        ).pack(padx=20, pady=(0, 5))

        tk.Label(
            self.pin_box,
            textvariable=self.alarm_pin_feedback_var,
            font=('Segoe UI', 10, 'bold'),
            bg="#111111",
            fg="#dddddd"
        ).pack(padx=20, pady=(0, 10))

        self.pin_box.pack(pady=(0, 10))

        self.overlay_action_frame = tk.Frame(center_panel, bg="#7f0000")
        self.overlay_action_frame.pack(pady=(0, 8))

        self.btn_alarm_disarm = tk.Button(
            self.overlay_action_frame,
            text="Disarm Alarm",
            command=self.disarm_alarm,
            font=('Segoe UI', 12, 'bold'),
            width=15,
            height=2,
            bg="#16a085",
            fg="white",
            activebackground="#1abc9c",
            activeforeground="white",
            relief=tk.FLAT,
            state="disabled"
        )
        self.btn_alarm_disarm.pack(side=tk.LEFT, padx=6)

        self.btn_alarm_service = tk.Button(
            self.overlay_action_frame,
            text="Enter Service Mode",
            command=self.enter_service_mode,
            font=('Segoe UI', 12, 'bold'),
            width=15,
            height=2,
            bg="#f39c12",
            fg="white",
            activebackground="#f1c40f",
            activeforeground="white",
            relief=tk.FLAT,
            state="disabled"
        )
        self.btn_alarm_service.pack(side=tk.LEFT, padx=6)

        self.overlay_keypad_frame = tk.Frame(center_panel, bg="#7f0000")
        self.overlay_keypad_frame.pack(pady=(0, 8))

        keypad_rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["CLEAR", "0", "ENTER"]
        ]

        for row_values in keypad_rows:
            row = tk.Frame(self.overlay_keypad_frame, bg="#7f0000")
            row.pack(pady=3)
            for value in row_values:
                if value == "CLEAR":
                    cmd = self.clear_alarm_pin
                elif value == "ENTER":
                    cmd = self.submit_alarm_pin
                else:
                    cmd = lambda v=value: self.add_alarm_pin_digit(v)

                btn = tk.Button(
                    row,
                    text=value,
                    command=cmd,
                    font=('Segoe UI', 13, 'bold'),
                    width=6,
                    height=2,
                    bg="#222222",
                    fg="white",
                    activebackground="#555555",
                    activeforeground="white",
                    relief=tk.FLAT
                )
                btn.pack(side=tk.LEFT, padx=4)

        self.overlay_logs_frame = tk.Frame(center_panel, bg="#7f0000")

        self.overlay_bottom_frame = tk.Frame(center_panel, bg="#7f0000")
        self.overlay_bottom_frame.pack(pady=(5, 4))

        self.btn_exit_service = tk.Button(
            self.overlay_bottom_frame,
            text="Exit Service Mode",
            command=self.exit_service_mode,
            font=('Segoe UI', 11, 'bold'),
            width=24,
            height=2,
            bg="#2c5f8d",
            fg="white",
            activebackground="#3a7dbf",
            activeforeground="white",
            relief=tk.FLAT,
            state="disabled"
        )

        tk.Label(
            center_panel,
            text="Customer controls are disabled while this screen is active.",
            font=('Segoe UI', 9, 'bold'),
            bg="#7f0000",
            fg="#ffe5e5"
        ).pack(pady=(4, 0))

        self.refresh_alarm_overlay()

    def close_alarm_popup(self):
        if self.alarm_popup is not None:
            try:
                self.alarm_popup.grab_release()
            except Exception:
                pass
            try:
                if self.alarm_popup.winfo_exists():
                    self.alarm_popup.destroy()
            except Exception:
                pass
        if self.active_popup is self.alarm_popup:
            self.active_popup = None
        self.alarm_popup = None
        self.overlay_action_frame = None
        self.overlay_keypad_frame = None
        self.overlay_logs_frame = None
        self.overlay_bottom_frame = None
        self.pin_box = None
        self.btn_alarm_disarm = None
        self.btn_alarm_service = None
        self.btn_exit_service = None
        self.pin_mask_var = None
        self.alarm_message_var = None
        self.alarm_pin_feedback_var = None
        self.logs_text_widget = None
        self.log_filter_var = None

    def add_alarm_pin_digit(self, digit):
        if self.service_mode_active and self.alarm_authorized:
            return

        if len(self.entered_pin) < 8:
            self.entered_pin += digit
            if self.pin_mask_var is not None:
                self.pin_mask_var.set("*" * len(self.entered_pin))
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Press ENTER to validate")

    def clear_alarm_pin(self):
        self.entered_pin = ""
        if self.pin_mask_var is not None:
            self.pin_mask_var.set("")
        if self.alarm_pin_feedback_var is not None:
            if self.service_mode_active and self.alarm_authorized:
                self.alarm_pin_feedback_var.set("Authorized for service mode")
            else:
                self.alarm_pin_feedback_var.set("Enter Admin PIN")

    def submit_alarm_pin(self):
        if self.entered_pin == ADMIN_PIN:
            self.alarm_authorized = True
            self.entered_pin = ""
            if self.pin_mask_var is not None:
                self.pin_mask_var.set("")
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Authorized. Choose Disarm or Service Mode.")
            self.update_alarm_actions()
        else:
            self.alarm_authorized = False
            self.entered_pin = ""
            if self.pin_mask_var is not None:
                self.pin_mask_var.set("")
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Incorrect PIN")
            self.update_alarm_actions()

    def disarm_alarm(self):
        if not self.alarm_authorized:
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Enter valid Admin PIN first")
            return

        if self.service_mode_active:
            return

        if not self.payment_reader.main_doors_closed:
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Cannot disarm while a main door is still open")
            return

        print("Alarm disarmed by authorized user")
        self.log_event("ALARM", "Alarm disarmed by authorized user")
        self.alarm_latched = False
        self.stop_door_alarm()
        self.close_alarm_popup()
        self.reset_alarm_auth()

    def enter_service_mode(self):
        if not self.alarm_authorized:
            if self.alarm_pin_feedback_var is not None:
                self.alarm_pin_feedback_var.set("Enter valid Admin PIN first")
            return

        self.service_mode_active = True
        self.stop_door_alarm()
        self.log_event("ALARM", "Entered service mode")

        print("Service mode enabled by authorized user")
        self.refresh_alarm_overlay()

    def exit_service_mode(self):
        if not self.service_mode_active:
            return

        if not self.payment_reader.main_doors_closed:
            return

        print("Service mode exited by authorized user")
        self.log_event("ALARM", "Exited service mode")
        self.service_mode_active = False
        self.alarm_latched = False
        self.stop_door_alarm()
        self.close_alarm_popup()
        self.reset_alarm_auth()

    def process_arduino_events(self):
        try:
            while True:
                msg = self.payment_reader.status_queue.get_nowait()

                if msg[0] == "DOOR_ALARM":
                    print("WARNING: Main door is open")
                    self.log_event("ALARM", "One or more main doors opened")
                    self.alarm_latched = True
                    self.show_alarm_popup()

                    if not self.service_mode_active:
                        self.start_door_alarm()
                        try:
                            self.root.bell()
                        except Exception:
                            pass
                    else:
                        self.stop_door_alarm()

                    self.refresh_alarm_overlay()

                elif msg[0] == "DOOR_SAFE":
                    print("Main doors closed")
                    self.log_event("ALARM", "All main doors closed")

                    if self.alarm_latched:
                        self.show_alarm_popup()

                        if not self.service_mode_active:
                            self.start_door_alarm()
                        else:
                            self.stop_door_alarm()

                        self.refresh_alarm_overlay()
                    else:
                        self.stop_door_alarm()
                        self.close_alarm_popup()
                        self.reset_alarm_auth()

                elif msg[0] == "DRAWER_OPEN":
                    print("Drawer is open")
                    self.log_event("ALARM", "Drawer opened")
                    if self.alarm_popup is not None and self.alarm_popup.winfo_exists():
                        self.refresh_alarm_overlay()

                elif msg[0] == "DRAWER_CLOSED":
                    print("Drawer is closed")
                    self.log_event("ALARM", "Drawer closed")
                    if self.alarm_popup is not None and self.alarm_popup.winfo_exists():
                        self.refresh_alarm_overlay()

                elif msg[0] == "READY":
                    print("Arduino is ready")
                    self.log_event("SYSTEM", "Arduino ready")

                elif msg[0] == "SHAKE_ALARM":
                    print("WARNING: Shaking detected")
                    self.log_event("ALARM", "Shaking detected")
                    self.alarm_latched = True
                    self.show_alarm_popup()

                    if not self.service_mode_active:
                        self.start_door_alarm()
                        try:
                            self.root.bell()
                        except Exception:
                            pass
                    else:
                        self.stop_door_alarm()

                    self.refresh_alarm_overlay()

        except queue.Empty:
            pass

        self.root.after(30, self.process_arduino_events)

    def load_model(self):
        model_path = 'model/best.pt'

        if not os.path.exists(model_path):
            alt_path = 'runs/detect/object_detector/weights/best.pt'
            if os.path.exists(alt_path):
                model_path = alt_path

        try:
            self.model = YOLO(model_path)
            print(f"Model loaded successfully: {model_path}")
        except Exception as e:
            messagebox.showwarning(
                "Model Warning",
                f"Failed to load YOLO model:\n{e}\n\n"
                "Image detection will not work.\n"
                f"Please ensure model is at: {model_path}"
            )
            self.model = None

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Mode.TButton',
                        font=('Segoe UI', 15, 'bold'),
                        padding=(25, 15),
                        background='#2c5f8d',
                        foreground='white',
                        borderwidth=2,
                        relief='raised')
        style.map('Mode.TButton',
                  background=[('active', '#3a7dbf'), ('pressed', '#1e4d73')])

        style.configure('ModeActive.TButton',
                        font=('Segoe UI', 15, 'bold'),
                        padding=(25, 15),
                        background='#e94560',
                        foreground='white',
                        borderwidth=2,
                        relief='sunken')
        style.map('ModeActive.TButton',
                  background=[('active', '#ff5577')])

        style.configure('Med.TButton',
                        font=('Segoe UI', 12, 'bold'),
                        padding=(18, 10),
                        background='#16a085',
                        foreground='white',
                        borderwidth=0,
                        anchor='center')
        style.map('Med.TButton',
                  background=[('active', '#1abc9c')])

        style.configure('Nav.TButton',
                        font=('Segoe UI', 11, 'bold'),
                        padding=10,
                        background='#34495e',
                        foreground='white')
        style.map('Nav.TButton',
                  background=[('active', '#4a6278')])

        style.configure('Dispense.TButton',
                        font=('Segoe UI', 13, 'bold'),
                        padding=12,
                        background='#e94560',
                        foreground='white',
                        borderwidth=0)
        style.map('Dispense.TButton',
                  background=[('active', '#f72c5b')])

        style.configure('Camera.TButton',
                        font=('Segoe UI', 12, 'bold'),
                        padding=10,
                        background='#27ae60',
                        foreground='white',
                        borderwidth=0)
        style.map('Camera.TButton',
                  background=[('active', '#2ecc71')])

        style.configure('PopupPrimary.TButton',
                        font=('Segoe UI', 14, 'bold'),
                        padding=(18, 12),
                        background='#e94560',
                        foreground='white',
                        borderwidth=0)
        style.map('PopupPrimary.TButton',
                  background=[('active', '#ff5577')])

        style.configure('PopupSecondary.TButton',
                        font=('Segoe UI', 14, 'bold'),
                        padding=(18, 12),
                        background='#2c5f8d',
                        foreground='white',
                        borderwidth=0)
        style.map('PopupSecondary.TButton',
                  background=[('active', '#3a7dbf')])

        style.configure('Qty.TButton',
                        font=('Segoe UI', 18, 'bold'),
                        padding=(16, 10),
                        background='#16a085',
                        foreground='white',
                        borderwidth=0)
        style.map('Qty.TButton',
                  background=[('active', '#1abc9c')])

    def create_main_layout(self):
        header = tk.Frame(self.root, bg="#16213e", height=230)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg="#16213e")
        title_frame.pack(pady=(15, 8))

        title = tk.Label(title_frame, text="Dog Pal",
                         font=('Segoe UI', 28, 'bold'),
                         bg="#16213e", fg="#e94560")
        title.pack()

        subtitle = tk.Label(title_frame,
                            text="A Smart Vending Machine System for Canine Medications",
                            font=('Segoe UI', 12),
                            bg="#16213e", fg="#bdc3c7")
        subtitle.pack()

        mode_frame = tk.Frame(header, bg="#16213e")
        mode_frame.pack(pady=15)

        self.btn_mode_image = ttk.Button(mode_frame, text="Image Scan",
                                         style='Mode.TButton',
                                         command=lambda: self.switch_mode('image'))
        self.btn_mode_image.pack(side=tk.LEFT, padx=15)

        self.btn_mode_manual = ttk.Button(mode_frame, text="Manual",
                                          style='Mode.TButton',
                                          command=lambda: self.switch_mode('manual'))
        self.btn_mode_manual.pack(side=tk.LEFT, padx=15)

        content = tk.Frame(self.root, bg="#1a1a2e")
        content.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)

        self.left_frame = tk.Frame(content, bg="#0f3460", width=730)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        camera_label = tk.Label(self.left_frame, text="Camera Preview",
                                font=('Segoe UI', 13, 'bold'),
                                bg="#0f3460", fg="white", pady=8)
        camera_label.pack()

        self.camera_container = tk.Frame(self.left_frame, bg="black",
                                         width=690, height=400)
        self.camera_container.pack(padx=8, pady=5)
        self.camera_container.pack_propagate(False)

        self.video_label = tk.Label(self.camera_container, bg="black",
                                    text="Camera Starting...",
                                    font=('Segoe UI', 14),
                                    fg="#7f8c8d")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(content, bg="#16213e", width=520)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=8, pady=8)
        self.right_frame.pack_propagate(False)

        self.results_frame = tk.Frame(self.right_frame, bg="#16213e")
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    def show_camera_panel(self):
        if self.left_frame.winfo_ismapped():
            return
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.right_frame.pack_forget()
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=8, pady=8)
        self.right_frame.pack_propagate(False)

    def hide_camera_panel(self):
        if self.left_frame.winfo_ismapped():
            self.left_frame.pack_forget()
        self.right_frame.pack_forget()
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.right_frame.pack_propagate(False)

    def switch_mode(self, mode):
        self.preview_active = False

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        self.btn_mode_image.configure(style='Mode.TButton')
        self.btn_mode_manual.configure(style='Mode.TButton')

        self.current_mode = mode
        self.current_page = 0
        self.detected_page = 0
        self.detected_medicines = []
        self.captured_image = None

        if mode == 'image':
            self.btn_mode_image.configure(style='ModeActive.TButton')
            self.show_camera_panel()
            self.show_image_mode()
            self.video_label.config(image='', text="Camera Ready", fg="#7f8c8d")
        elif mode == 'manual':
            # Stop hidden webcam polling so the OTC button grid stays responsive.
            self.stop_camera()
            self.btn_mode_manual.configure(style='ModeActive.TButton')
            self.hide_camera_panel()
            self.show_manual_mode()

        self.root.after(50, self.keep_root_fullscreen)

    def show_image_mode(self):
        btn_frame = tk.Frame(self.results_frame, bg="#16213e")
        btn_frame.pack(pady=10, padx=15, fill=tk.X)

        self.btn_start_camera = ttk.Button(btn_frame, text="Start Preview",
                                           style='Camera.TButton',
                                           command=self.start_camera_image)
        self.btn_start_camera.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_capture = ttk.Button(btn_frame, text="Capture & Detect",
                                      style='Camera.TButton',
                                      command=self.capture_and_process_image,
                                      state='disabled')
        self.btn_capture.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        detected_label = tk.Label(self.results_frame,
                                  text="Detected Medicines:",
                                  font=('Segoe UI', 12, 'bold'),
                                  bg="#16213e", fg="white")
        detected_label.pack(pady=(5, 5))

        self.detected_container = tk.Frame(self.results_frame, bg="#16213e")
        self.detected_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.detected_pagination_frame = tk.Frame(self.results_frame, bg="#16213e")
        self.detected_pagination_frame.pack(fill=tk.X, padx=15, pady=5)

        self.btn_detected_prev = ttk.Button(self.detected_pagination_frame, text="Previous",
                                            style='Nav.TButton',
                                            command=self.prev_detected_page)
        self.btn_detected_prev.pack(side=tk.LEFT, padx=5)
        self.btn_detected_prev.pack_forget()

        self.detected_page_label = tk.Label(self.detected_pagination_frame,
                                            text="",
                                            font=('Segoe UI', 10, 'bold'),
                                            bg="#16213e", fg="white")
        self.detected_page_label.pack(side=tk.LEFT, expand=True)

        self.btn_detected_next = ttk.Button(self.detected_pagination_frame, text="Next",
                                            style='Nav.TButton',
                                            command=self.next_detected_page)
        self.btn_detected_next.pack(side=tk.RIGHT, padx=5)
        self.btn_detected_next.pack_forget()

    def start_camera_image(self):
        if not self.camera_running or self.camera is None:
            self.start_camera()
        self.preview_active = True
        self.btn_start_camera.config(state='disabled', text="Preview Active")
        self.btn_capture.config(state='normal')

    def capture_and_process_image(self):
        if not self.camera_running or self.camera is None:
            self.start_camera()
        if self.model is None:
            messagebox.showerror("Error", "YOLO model not loaded!\n\nCannot perform object detection.")
            return

        try:
            if self.use_picamera:
                frame = self.camera.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ret = True
            else:
                ret, frame = self.camera.read()

            if not ret and self.latest_frame is not None:
                frame = self.latest_frame.copy()
                ret = True
        except Exception as e:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
                ret = True
            else:
                messagebox.showerror("Camera Error", f"Failed to capture image:\n{e}")
                return

        if ret:
            self.captured_image = frame.copy()
            self.preview_active = False
            self.detect_medicines_in_image()
            self.btn_start_camera.config(state='normal', text="Resume Preview")
            self.btn_capture.config(state='disabled')

    def detect_medicines_in_image(self):
        try:
            results = self.model.predict(
                source=self.captured_image,
                conf=self.confidence_threshold,
                save=False,
                verbose=False
            )

            result = results[0]
            boxes = result.boxes

            if len(boxes) == 0:
                self.show_no_detection_error()
                return

            classes = self.model.names

            sign_detected = False
            detected_meds = []

            for box in boxes:
                class_id = int(box.cls[0])
                class_name = classes[class_id].lower()
                confidence = float(box.conf[0])

                if class_name == "sign":
                    sign_detected = True
                else:
                    full_name = CLASS_NAME_MAPPING.get(class_name, class_name.title())
                    detected_meds.append({
                        'name': full_name,
                        'confidence': confidence,
                        'box': box.xyxy[0].tolist()
                    })

            self.display_detection_result(boxes, classes, sign_detected)

            if not sign_detected:
                self.show_no_sign_error()
            elif len(detected_meds) == 0:
                self.show_no_medicines_detected(sign_detected=True)
            else:
                detected_meds.sort(key=lambda x: x['confidence'], reverse=True)
                self.detected_medicines = [med['name'] for med in detected_meds]
                self.detected_page = 0
                self.update_detected_list()

        except Exception as e:
            messagebox.showerror("Detection Error", f"Error during detection:\n{e}")
            self.show_no_detection_error()

    def display_detection_result(self, boxes, classes, sign_detected):
        frame_rgb = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_image)

        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

        colors = {'sign': (255, 215, 0), 'medicine': (0, 255, 0)}

        for box in boxes:
            class_id = int(box.cls[0])
            class_name = classes[class_id].lower()
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            if class_name == "sign":
                color = colors['sign']
                display_name = "Sign"
            else:
                color = colors['medicine']
                display_name = CLASS_NAME_MAPPING.get(class_name, class_name.title())

            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)

            label = f"{display_name}"
            bbox = draw.textbbox((x1, y1 - 20), label, font=font)
            draw.rectangle(bbox, fill=color)
            draw.text((x1, y1 - 20), label, fill='black', font=font)

        frame_resized = pil_image.resize((690, 400))
        imgtk = ImageTk.PhotoImage(image=frame_resized)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk, text="")

    def show_no_sign_error(self):
        self.detected_medicines = []
        for widget in self.detected_container.winfo_children():
            widget.destroy()
        tk.Label(self.detected_container,
                 text="No Sign Detected\n\nPlease try again",
                 font=('Segoe UI', 11),
                 bg="#16213e", fg="#e74c3c",
                 pady=15).pack()

    def show_no_medicines_detected(self, sign_detected=False):
        self.detected_medicines = []
        for widget in self.detected_container.winfo_children():
            widget.destroy()
        tk.Label(self.detected_container,
                 text="No medicines detected\n\nTry capturing again",
                 font=('Segoe UI', 11),
                 bg="#16213e", fg="#f39c12",
                 pady=15).pack()

    def show_no_detection_error(self):
        self.detected_medicines = []

        frame_rgb = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (690, 400))
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk, text="")

        for widget in self.detected_container.winfo_children():
            widget.destroy()

        tk.Label(self.detected_container,
                 text="Nothing Detected\n\nPlease try again",
                 font=('Segoe UI', 11),
                 bg="#16213e", fg="#e74c3c",
                 pady=15).pack()

    def update_detected_list(self):
        for widget in self.detected_container.winfo_children():
            widget.destroy()

        if self.detected_medicines:
            total_pages = math.ceil(len(self.detected_medicines) / DETECTED_ITEMS_PER_PAGE)
            start_idx = self.detected_page * DETECTED_ITEMS_PER_PAGE
            end_idx = min(start_idx + DETECTED_ITEMS_PER_PAGE, len(self.detected_medicines))

            for med in self.detected_medicines[start_idx:end_idx]:
                med_frame = tk.Frame(self.detected_container, bg="#0f3460",
                                     relief=tk.RAISED, borderwidth=1)
                med_frame.pack(fill=tk.X, pady=2)

                content_frame = tk.Frame(med_frame, bg="#0f3460")
                content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

                tk.Label(content_frame, text=f"{med}",
                         font=('Segoe UI', 10, 'bold'),
                         bg="#0f3460", fg="#2ecc71",
                         anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

                ttk.Button(content_frame, text="Dispense",
                           style='Med.TButton',
                           command=lambda m=med: self.show_quantity_popup(m)
                           ).pack(side=tk.RIGHT)

            if total_pages > 1:
                self.detected_page_label.config(text=f"Page {self.detected_page + 1} of {total_pages}")
                self.btn_detected_prev.pack(side=tk.LEFT, padx=5)
                self.btn_detected_next.pack(side=tk.RIGHT, padx=5)
                self.btn_detected_prev.config(state='normal' if self.detected_page > 0 else 'disabled')
                self.btn_detected_next.config(state='normal' if self.detected_page < total_pages - 1 else 'disabled')
            else:
                self.detected_page_label.config(text="")
                self.btn_detected_prev.pack_forget()
                self.btn_detected_next.pack_forget()

    def prev_detected_page(self):
        if self.detected_page > 0:
            self.detected_page -= 1
            self.update_detected_list()

    def next_detected_page(self):
        total_pages = math.ceil(len(self.detected_medicines) / DETECTED_ITEMS_PER_PAGE)
        if self.detected_page < total_pages - 1:
            self.detected_page += 1
            self.update_detected_list()

    def show_manual_mode(self):
        self.manual_outer = tk.Frame(self.results_frame, bg="#16213e")
        self.manual_outer.pack(fill=tk.BOTH, expand=True)

        self.manual_container = tk.Frame(self.manual_outer, bg="#16213e")
        self.manual_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)

        self.filtered_meds = sorted(OTC_MEDS)
        self.render_manual_grid()

    def render_manual_grid(self):
        for widget in self.manual_container.winfo_children():
            widget.destroy()

        meds = list(self.filtered_meds)
        if not meds:
            tk.Label(self.manual_container,
                     text="No medicines found",
                     font=('Segoe UI', 11),
                     bg="#16213e", fg="#e74c3c").pack(expand=True)
            return

        # Keep the original OTC medicine card UI, but make it reliable on laptops.
        # The old fixed 3-row x 4-column layout can overflow narrower laptop screens,
        # leaving some OTC buttons hard to open/click. This keeps the same cards and
        # button style while choosing a safer number of columns for the available width.
        self.manual_container.update_idletasks()
        available_width = self.manual_container.winfo_width()
        if available_width <= 1:
            available_width = self.right_frame.winfo_width()
        if available_width <= 1:
            available_width = self.root.winfo_screenwidth()

        if available_width < 760:
            cols = 2
        elif available_width < 1050:
            cols = 3
        else:
            cols = 4

        rows = math.ceil(len(meds) / cols)

        grid = tk.Frame(self.manual_container, bg="#16213e")
        grid.pack(expand=True)

        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1, uniform="col")
        for r in range(rows):
            grid.grid_rowconfigure(r, weight=1, uniform="row")

        for idx, med in enumerate(meds):
            r = idx // cols
            c = idx % cols

            card = tk.Frame(grid, bg="#0f3460", relief=tk.RAISED, borderwidth=1)
            card.grid(row=r, column=c, padx=18, pady=14, sticky="nsew")

            btn = ttk.Button(
                card,
                text=med,
                style='Med.TButton',
                command=lambda m=med: self.show_quantity_popup(m),
                width=22
            )
            btn.pack(padx=18, pady=14, fill=tk.BOTH, expand=True)

            # Extra laptop/touchpad reliability: clicking anywhere on the medicine
            # card opens the same confirmation popup as the button.
            card.bind("<Button-1>", lambda event, m=med: self.show_quantity_popup(m))
            btn.bind("<Return>", lambda event, m=med: self.show_quantity_popup(m))

    def start_camera(self):
        if self.camera_running and self.camera is not None:
            return

        self.camera_running = True

        if self.use_picamera:
            try:
                self.camera = Picamera2()
                config = self.camera.create_video_configuration(main={"size": (640, 480)})
                self.camera.configure(config)
                self.camera.start()
                time.sleep(0.2)
                print("Picamera2 started successfully")
            except Exception as e:
                print(f"Picamera2 error: {e}, falling back to USB camera")
                self.use_picamera = False
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("USB camera started")
        else:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print("USB camera started")

        self.update_camera()

    def update_camera(self):
        if self.camera_running and self.camera:
            try:
                if self.use_picamera:
                    frame = self.camera.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    ret = True
                    self.latest_frame = frame.copy()
                else:
                    ret, frame = self.camera.read()
                    if ret:
                        self.latest_frame = frame.copy()

                if ret and self.preview_active:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (690, 400))

                    img = Image.fromarray(frame_resized)
                    imgtk = ImageTk.PhotoImage(image=img)

                    if self.video_label:
                        self.video_label.imgtk = imgtk
                        self.video_label.configure(image=imgtk, text="")
            except Exception as e:
                print(f"Camera error: {e}")

            if self.camera_running:
                self.root.after(30, self.update_camera)

    def stop_camera(self):
        self.camera_running = False
        if self.camera:
            try:
                if self.use_picamera:
                    self.camera.stop()
                else:
                    self.camera.release()
            except Exception:
                pass
            self.camera = None

    def on_closing(self):
        self.log_event("SYSTEM", "Application closing")
        self.stop_door_alarm()
        self.close_alarm_popup()
        self.stop_camera()
        self.hardware.stop_all_servos()
        self.payment_reader.close()
        self.root.destroy()

    def print_receipt_async(self, medicine, qty=1):
        unit_price = MEDICINE_PRICES.get(medicine, 0.00)

        def worker():
            printed = self.printer.print_receipt(
                medicine_name=medicine,
                price=unit_price,
                qty=qty
            )
            if printed:
                self.log_event("TRANSACTION", f"Receipt printed: {medicine} | Qty: {qty}")
            else:
                self.log_event("SYSTEM", f"Receipt printing failed: {medicine} | Qty: {qty}")

        threading.Thread(target=worker, daemon=True).start()

    def show_quantity_popup(self, medicine):
        if medicine not in MED_TO_SLOT:
            return

        slot = MED_TO_SLOT[medicine]
        unit_price = MEDICINE_PRICES.get(medicine, 0.00)
        med_info = self.get_medicine_info(medicine)
        is_prescription = medicine in PRESCRIPTION_MEDS

        popup = tk.Toplevel(self.root)
        popup.title("Confirm Dispensing")
        self.make_fullscreen_popup(popup, bg="#16213e")
        popup.resizable(False, False)

        # Responsive sizing based on the actual touchscreen/window size.
        popup.update_idletasks()
        screen_w = max(800, popup.winfo_screenwidth())
        screen_h = max(480, popup.winfo_screenheight())
        scale = min(screen_w / 1366.0, screen_h / 768.0)
        scale = max(0.68, min(1.0, scale))

        def fs(size):
            return max(8, int(size * scale))

        outer_pad_x = max(10, int(22 * scale))
        outer_pad_y = max(6, int(12 * scale))
        gap = max(8, int(16 * scale))
        wrap_left = max(260, int(screen_w * 0.28))
        wrap_right = max(280, int(screen_w * 0.32))

        container = tk.Frame(popup, bg="#16213e")
        container.pack(fill=tk.BOTH, expand=True, padx=outer_pad_x, pady=outer_pad_y)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        title_label = tk.Label(
            container,
            text="Confirm Dispensing",
            font=('Segoe UI', fs(28), 'bold'),
            bg="#16213e",
            fg="#e94560"
        )
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, max(6, int(10 * scale))))

        content = tk.Frame(container, bg="#16213e")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1, uniform="panel")
        content.grid_columnconfigure(1, weight=1, uniform="panel")
        content.grid_rowconfigure(0, weight=1)

        left_panel = tk.Frame(content, bg="#0f3460", relief=tk.FLAT, bd=0)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, gap // 2))
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(2, weight=1)

        right_panel = tk.Frame(content, bg="#0f3460", relief=tk.FLAT, bd=0)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(gap // 2, 0))
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(6, weight=1)

        tk.Label(
            left_panel,
            text=medicine,
            font=('Segoe UI', fs(23), 'bold'),
            bg="#0f3460",
            fg="white",
            wraplength=wrap_left,
            justify="center"
        ).grid(row=0, column=0, sticky="ew", padx=max(10, int(16 * scale)), pady=(max(12, int(22 * scale)), max(3, int(6 * scale))))

        tk.Label(
            left_panel,
            text=med_info["brand"],
            font=('Segoe UI', fs(15), 'bold'),
            bg="#0f3460",
            fg="#2ecc71"
        ).grid(row=1, column=0, sticky="ew", padx=max(10, int(16 * scale)), pady=(0, max(6, int(12 * scale))))

        info_card = tk.Frame(left_panel, bg="#163b66")
        info_card.grid(row=2, column=0, sticky="nsew", padx=max(10, int(18 * scale)), pady=(0, max(10, int(16 * scale))))
        info_card.grid_columnconfigure(0, weight=1)

        tk.Label(
            info_card,
            text="Medicine Information",
            font=('Segoe UI', fs(15), 'bold'),
            bg="#163b66",
            fg="#f1f1f1"
        ).pack(anchor="w", padx=max(10, int(16 * scale)), pady=(max(10, int(14 * scale)), max(6, int(10 * scale))))

        info_rows = [
            ("Type", med_info["type"]),
            ("Form", med_info["form"]),
            ("Unit Price", f"PHP {unit_price:,.2f}")
        ]

        for label_text, value_text in info_rows:
            row = tk.Frame(info_card, bg="#163b66")
            row.pack(fill=tk.X, padx=max(10, int(16 * scale)), pady=max(1, int(3 * scale)))

            tk.Label(
                row,
                text=f"{label_text}:",
                font=('Segoe UI', fs(12), 'bold'),
                bg="#163b66",
                fg="#bdc3c7",
                width=11,
                anchor="w"
            ).pack(side=tk.LEFT)

            tk.Label(
                row,
                text=value_text,
                font=('Segoe UI', fs(12)),
                bg="#163b66",
                fg="white",
                anchor="w",
                wraplength=wrap_left
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            info_card,
            text="Description",
            font=('Segoe UI', fs(12), 'bold'),
            bg="#163b66",
            fg="#bdc3c7"
        ).pack(anchor="w", padx=max(10, int(16 * scale)), pady=(max(10, int(14 * scale)), max(4, int(6 * scale))))

        tk.Label(
            info_card,
            text=med_info["summary"],
            font=('Segoe UI', fs(12)),
            bg="#163b66",
            fg="white",
            wraplength=wrap_left,
            justify="left"
        ).pack(anchor="w", padx=max(10, int(16 * scale)), pady=(0, max(8, int(14 * scale))))

        tk.Label(
            right_panel,
            text="Order Details",
            font=('Segoe UI', fs(18), 'bold'),
            bg="#0f3460",
            fg="white"
        ).grid(row=0, column=0, sticky="ew", pady=(max(10, int(16 * scale)), max(5, int(8 * scale))))

        warning_box = tk.Frame(right_panel, bg="#7f0000")
        warning_box.grid(row=1, column=0, sticky="ew", padx=max(12, int(24 * scale)), pady=(0, max(7, int(10 * scale))))

        tk.Label(
            warning_box,
            text="IMPORTANT PAYMENT WARNING",
            font=('Segoe UI', fs(11), 'bold'),
            bg="#7f0000",
            fg="white"
        ).pack(pady=(max(4, int(6 * scale)), 1))

        tk.Label(
            warning_box,
            text="Inserted payment is permanent. No change will be given.",
            font=('Segoe UI', fs(10), 'bold'),
            bg="#7f0000",
            fg="white",
            wraplength=wrap_right,
            justify="center"
        ).pack(pady=(0, max(4, int(6 * scale))))

        qty_var = tk.IntVar(value=1)
        total_var = tk.StringVar(value=f"PHP {unit_price:,.2f}")

        qty_area = tk.Frame(right_panel, bg="#0f3460")
        qty_area.grid(row=2, column=0, sticky="ew", pady=(max(4, int(8 * scale)), max(2, int(4 * scale))))

        qty_box = tk.Frame(qty_area, bg="#0f3460")
        qty_box.pack(anchor="center")

        minus_btn = ttk.Button(qty_box, text="-", style='Qty.TButton', width=4)
        minus_btn.pack(side=tk.LEFT, padx=max(5, int(10 * scale)))

        qty_label = tk.Label(
            qty_box,
            textvariable=qty_var,
            font=('Segoe UI', fs(24), 'bold'),
            width=5,
            bg="#163b66",
            fg="white",
            relief=tk.FLAT,
            pady=max(5, int(9 * scale))
        )
        qty_label.pack(side=tk.LEFT, padx=max(5, int(10 * scale)))

        plus_btn = ttk.Button(qty_box, text="+", style='Qty.TButton', width=4)
        plus_btn.pack(side=tk.LEFT, padx=max(5, int(10 * scale)))

        tk.Label(
            right_panel,
            text="Quantity",
            font=('Segoe UI', fs(15)),
            bg="#0f3460",
            fg="#bdc3c7"
        ).grid(row=3, column=0, sticky="ew", pady=(0, max(3, int(5 * scale))))

        qty_note = "Prescription medicines are limited to 1 quantity only." if is_prescription else "Maximum quantity: 5"
        qty_note_fg = "#f1c40f" if is_prescription else "#bdc3c7"
        tk.Label(
            right_panel,
            text=qty_note,
            font=('Segoe UI', fs(11), 'bold' if is_prescription else 'normal'),
            bg="#0f3460",
            fg=qty_note_fg,
            wraplength=wrap_right,
            justify="center"
        ).grid(row=4, column=0, sticky="ew", padx=max(12, int(24 * scale)), pady=(0, max(6, int(10 * scale))))

        price_box = tk.Frame(right_panel, bg="#163b66")
        price_box.grid(row=5, column=0, sticky="ew", padx=max(12, int(24 * scale)), pady=(max(3, int(6 * scale)), max(7, int(12 * scale))))

        tk.Label(
            price_box,
            text="Total Price",
            font=('Segoe UI', fs(16)),
            bg="#163b66",
            fg="#bdc3c7"
        ).pack(pady=(max(8, int(14 * scale)), max(3, int(6 * scale))))

        tk.Label(
            price_box,
            textvariable=total_var,
            font=('Segoe UI', fs(28), 'bold'),
            bg="#163b66",
            fg="#2ecc71"
        ).pack(pady=(0, max(8, int(14 * scale))))

        note_box = tk.Frame(right_panel, bg="#0f3460")
        note_box.grid(row=6, column=0, sticky="nsew", padx=max(12, int(24 * scale)), pady=(0, max(5, int(8 * scale))))

        tk.Label(
            note_box,
            text="Please review the medicine information before proceeding to payment.",
            font=('Segoe UI', fs(11)),
            bg="#0f3460",
            fg="#bdc3c7",
            wraplength=wrap_right,
            justify="center"
        ).pack(anchor="center", pady=max(2, int(4 * scale)))

        # Button row is outside the content panel so it is always visible.
        btn_row = tk.Frame(container, bg="#16213e")
        btn_row.grid(row=2, column=0, sticky="ew", pady=(max(6, int(10 * scale)), 0))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=0)
        btn_row.grid_columnconfigure(2, weight=0)
        btn_row.grid_columnconfigure(3, weight=1)

        def refresh_total():
            total = unit_price * qty_var.get()
            total_var.set(f"PHP {total:,.2f}")

        def update_qty_buttons():
            current = qty_var.get()

            if is_prescription:
                qty_var.set(1)
                minus_btn.state(['disabled'])
                plus_btn.state(['disabled'])
                refresh_total()
                return

            if current <= 1:
                minus_btn.state(['disabled'])
            else:
                minus_btn.state(['!disabled'])

            if current >= 5:
                plus_btn.state(['disabled'])
            else:
                plus_btn.state(['!disabled'])

        def decrease_qty():
            if is_prescription:
                qty_var.set(1)
                update_qty_buttons()
                return
            if qty_var.get() > 1:
                qty_var.set(qty_var.get() - 1)
                refresh_total()
                update_qty_buttons()

        def increase_qty():
            if is_prescription:
                qty_var.set(1)
                update_qty_buttons()
                return
            if qty_var.get() < 5:
                qty_var.set(qty_var.get() + 1)
                refresh_total()
                update_qty_buttons()

        def confirm_dispense():
            selected_qty = 1 if is_prescription else qty_var.get()
            self.log_event("TRANSACTION", f"Proceed to payment: {medicine} | Qty selected: {selected_qty}")
            self.close_active_popup()
            self.show_payment_popup(medicine, selected_qty)

        minus_btn.configure(command=decrease_qty)
        plus_btn.configure(command=increase_qty)
        update_qty_buttons()

        cancel_button = tk.Button(
            btn_row,
            text="Cancel",
            command=self.close_active_popup,
            font=('Segoe UI', fs(14), 'bold'),
            width=max(12, int(16 * scale)),
            height=2,
            bg="#2c5f8d",
            fg="white",
            activebackground="#3a7dbf",
            activeforeground="white",
            relief=tk.FLAT
        )
        cancel_button.grid(row=0, column=1, padx=max(6, int(12 * scale)))

        proceed_button = tk.Button(
            btn_row,
            text="Proceed to Payment",
            command=confirm_dispense,
            font=('Segoe UI', fs(14), 'bold'),
            width=max(16, int(22 * scale)),
            height=2,
            bg="#e94560",
            fg="white",
            activebackground="#ff5577",
            activeforeground="white",
            relief=tk.FLAT
        )
        proceed_button.grid(row=0, column=2, padx=max(6, int(12 * scale)))

        popup.update_idletasks()
        try:
            popup.lift()
            popup.focus_force()
        except Exception:
            pass

    def show_payment_popup(self, medicine, qty):
        if medicine in PRESCRIPTION_MEDS:
            qty = 1

        unit_price = MEDICINE_PRICES.get(medicine, 0.00)
        total_price = unit_price * qty

        popup = tk.Toplevel(self.root)
        popup.title("Payment")
        self.make_fullscreen_popup(popup, bg="#16213e")
        popup.resizable(False, False)

        container = tk.Frame(popup, bg="#16213e")
        container.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        tk.Label(container,
                 text="Payment",
                 font=('Segoe UI', 22, 'bold'),
                 bg="#16213e", fg="#e94560").pack(pady=(0, 8))

        tk.Label(container,
                 text=medicine,
                 font=('Segoe UI', 19, 'bold'),
                 bg="#16213e", fg="white",
                 wraplength=520,
                 justify="center").pack(pady=(0, 8))

        tk.Label(container,
                 text=f"Quantity: {qty}",
                 font=('Segoe UI', 14),
                 bg="#16213e", fg="#bdc3c7").pack()

        tk.Label(container,
                 text=f"Price per item: PHP {unit_price:,.2f}",
                 font=('Segoe UI', 14),
                 bg="#16213e", fg="#bdc3c7").pack(pady=(3, 0))

        tk.Label(container,
                 text=f"Required Amount: PHP {total_price:,.2f}",
                 font=('Segoe UI', 17, 'bold'),
                 bg="#16213e", fg="#f1c40f").pack(pady=(14, 4))

        tk.Label(container,
                 text="Payment must be at least the required amount",
                 font=('Segoe UI', 13, 'bold'),
                 bg="#16213e", fg="#e74c3c").pack(pady=(0, 4))

        tk.Label(container,
                 text="IMPORTANT: Inserted payment is permanent. No change will be given.",
                 font=('Segoe UI', 12, 'bold'),
                 bg="#16213e", fg="#ff6b6b",
                 wraplength=620,
                 justify="center").pack(pady=(0, 10))

        inserted_var = tk.StringVar(value="PHP 0.00")
        status_var = tk.StringVar(value="Please insert coins or bills")
        last_inserted_var = tk.StringVar(value="Last inserted: PHP 0.00")
        drop_count_var = tk.StringVar(value="Dropped Items: 0")

        amount_box = tk.Frame(container, bg="#0f3460", relief=tk.FLAT, bd=0)
        amount_box.pack(fill=tk.X, pady=(12, 16), padx=30)

        tk.Label(amount_box,
                 text="Inserted Amount",
                 font=('Segoe UI', 16),
                 bg="#0f3460", fg="#bdc3c7").pack(pady=(14, 5))

        tk.Label(amount_box,
                 textvariable=inserted_var,
                 font=('Segoe UI', 28, 'bold'),
                 bg="#0f3460", fg="#2ecc71").pack(pady=(0, 6))

        tk.Label(amount_box,
                 textvariable=last_inserted_var,
                 font=('Segoe UI', 13),
                 bg="#0f3460", fg="#bdc3c7").pack(pady=(0, 10))

        tk.Label(amount_box,
                 textvariable=drop_count_var,
                 font=('Segoe UI', 13, 'bold'),
                 bg="#0f3460", fg="#2ecc71").pack(pady=(0, 14))

        tk.Label(container,
                 textvariable=status_var,
                 font=('Segoe UI', 13),
                 bg="#16213e", fg="white",
                 wraplength=520,
                 justify="center").pack(pady=(4, 16))

        btn_row = tk.Frame(container, bg="#16213e")
        btn_row.pack(pady=(8, 0))

        dispense_btn = ttk.Button(btn_row,
                                  text="Confirm Dispense",
                                  style='PopupPrimary.TButton',
                                  state='disabled')
        dispense_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = ttk.Button(btn_row,
                                text="Cancel",
                                style='PopupSecondary.TButton',
                                command=self.close_active_popup)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        if not self.payment_connected:
            status_var.set("Arduino payment reader not connected.")
            last_inserted_var.set("Last inserted: N/A")
            self.log_event("SYSTEM", "Arduino payment reader not connected during payment popup")
            messagebox.showwarning(
                "Arduino Not Connected",
                "Payment reader was not connected.\n"
                "Please check USB connection and restart the app."
            )
            return

        self.payment_reader.reset_total()
        self.payment_reader.reset_drop_count()
        self.current_drop_count = 0
        current_total = {"value": 0}
        cancel_removed = {"value": False}

        self.log_event("TRANSACTION", f"Payment window opened: {medicine} | Qty: {qty} | Required: PHP {total_price:,.2f}")

        def process_payment_queue():
            try:
                while True:
                    msg = self.payment_reader.payment_queue.get_nowait()

                    if msg[0] == "PAY":
                        _, inserted, total = msg
                        self.log_event("TRANSACTION", f"Payment inserted: PHP {inserted:.2f} | Running total: PHP {total:.2f}")
                        current_total["value"] = total
                        inserted_var.set(f"PHP {total:,.2f}")
                        last_inserted_var.set(f"Last inserted: PHP {inserted:,.2f}")

                        if total >= total_price:
                            excess = total - total_price

                            if excess > 0:
                                status_var.set(
                                    f"Payment complete. Overpayment received: PHP {excess:,.2f}. You may now confirm dispensing."
                                )
                                self.log_event("TRANSACTION", f"Payment complete with overpayment: PHP {excess:.2f}")
                            else:
                                status_var.set(
                                    "Payment complete. Enough amount received. You may now confirm dispensing."
                                )
                                self.log_event("TRANSACTION", "Payment complete with exact or sufficient amount")

                            dispense_btn.config(state='normal')

                            if not cancel_removed["value"]:
                                try:
                                    cancel_btn.destroy()
                                except Exception:
                                    pass
                                cancel_removed["value"] = True
                        else:
                            remaining = total_price - total
                            status_var.set(f"Remaining balance: PHP {remaining:,.2f}")
                            dispense_btn.config(state='disabled')

                    elif msg[0] == "RESET":
                        current_total["value"] = 0
                        inserted_var.set("PHP 0.00")
                        last_inserted_var.set("Last inserted: PHP 0.00")
                        status_var.set("Please insert coins or bills")
                        dispense_btn.config(state='disabled')
                        self.log_event("TRANSACTION", "Payment total reset")

                    elif msg[0] == "READY":
                        status_var.set("Arduino ready. Please insert coins or bills")
                        self.log_event("SYSTEM", "Arduino ready during payment")

            except queue.Empty:
                pass

            if popup.winfo_exists():
                popup.after(30, process_payment_queue)

        def process_drop_queue():
            try:
                while True:
                    msg = self.payment_reader.drop_queue.get_nowait()

                    if msg[0] == "DROP":
                        count = msg[1]
                        self.current_drop_count = count
                        self.log_event("DROP", f"Detected dropped item count: {count}")
                        drop_count_var.set(f"Dropped Items: {count}")

            except queue.Empty:
                pass

            if popup.winfo_exists():
                popup.after(30, process_drop_queue)

        def confirm_paid_dispense():
            if current_total["value"] >= total_price:
                self.log_event("TRANSACTION", f"Confirm dispense pressed: {medicine} | Qty: {qty}")
                self.close_active_popup()
                self.dispense_medicine(medicine, qty)
            else:
                self.log_event("TRANSACTION", f"Confirm dispense blocked: insufficient payment for {medicine}")
                messagebox.showwarning("Payment Incomplete",
                                       "Required amount has not been reached yet.")

        dispense_btn.config(command=confirm_paid_dispense)
        process_payment_queue()
        process_drop_queue()

    def show_success_popup(self, medicine, qty, total_price):
        popup = tk.Toplevel(self.root)
        popup.title("Success")
        self.make_fullscreen_popup(popup, bg="#16213e")
        popup.resizable(False, False)

        container = tk.Frame(popup, bg="#16213e")
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=28)

        tk.Label(container,
                 text="DOGPAL",
                 font=('Segoe UI', 24, 'bold'),
                 bg="#16213e", fg="#e94560").pack(pady=(0, 8))

        tk.Label(container,
                 text="Dispensed Successfully",
                 font=('Segoe UI', 20, 'bold'),
                 bg="#16213e", fg="white").pack(pady=(0, 14))

        info_box = tk.Frame(container, bg="#0f3460")
        info_box.pack(fill=tk.X, padx=20, pady=8)

        tk.Label(info_box,
                 text=f"Medicine: {medicine}",
                 font=('Segoe UI', 14, 'bold'),
                 bg="#0f3460", fg="white",
                 anchor="w", wraplength=500, justify="left").pack(fill=tk.X, padx=16, pady=(14, 6))

        tk.Label(info_box,
                 text=f"Quantity: {qty}",
                 font=('Segoe UI', 14),
                 bg="#0f3460", fg="#bdc3c7",
                 anchor="w").pack(fill=tk.X, padx=16, pady=3)

        tk.Label(info_box,
                 text=f"Total: PHP {total_price:,.2f}",
                 font=('Segoe UI', 16, 'bold'),
                 bg="#0f3460", fg="#2ecc71",
                 anchor="w").pack(fill=tk.X, padx=16, pady=(3, 14))

        tk.Label(container,
                 text="Receipt is being printed.",
                 font=('Segoe UI', 14),
                 bg="#16213e", fg="#bdc3c7").pack(pady=(14, 12))

        ttk.Button(container, text="OK", style='PopupPrimary.TButton',
                   command=self.close_active_popup).pack(pady=(6, 0))

    def wait_for_new_drop(self, previous_count, timeout=2.8, progress_callback=None):
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                msg = self.payment_reader.drop_queue.get_nowait()
                if msg[0] == "DROP":
                    self.current_drop_count = msg[1]
                    if progress_callback:
                        progress_callback(self.current_drop_count)
                    if self.current_drop_count > previous_count:
                        return True
            except queue.Empty:
                pass

            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.02)

        return False

    def dispense_medicine(self, medicine, qty=1):
        if medicine in PRESCRIPTION_MEDS:
            qty = 1

        if medicine not in MED_TO_SLOT:
            messagebox.showerror("Error",
                                 f"{medicine} is not configured in the system.\n\n"
                                 "Please contact administrator.")
            return

        slot = MED_TO_SLOT[medicine]
        channel = SLOT_TO_CH[slot]
        unit_price = MEDICINE_PRICES.get(medicine, 0.00)
        total_price = unit_price * qty

        self.expected_drop_count = qty
        self.current_drop_count = 0
        self.payment_reader.reset_drop_count()
        self.log_event("TRANSACTION", f"Dispense requested: {medicine} | Qty: {qty} | Slot: {slot}")

        dispensing_window = tk.Toplevel(self.root)
        dispensing_window.title("Dispensing...")
        self.make_fullscreen_popup(dispensing_window, bg="#16213e")
        dispensing_window.resizable(False, False)

        dispensing_panel = tk.Frame(dispensing_window, bg="#16213e")
        dispensing_panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(dispensing_panel,
                 text="Dispensing",
                 font=('Segoe UI', 16, 'bold'),
                 bg="#16213e", fg="#e94560",
                 pady=10).pack()

        tk.Label(dispensing_panel,
                 text=f"{medicine}\nQuantity: {qty}",
                 font=('Segoe UI', 13, 'bold'),
                 bg="#16213e", fg="white",
                 pady=6).pack()

        drop_label_var = tk.StringVar(value=f"Dropped: 0 / {qty}")
        status_label_var = tk.StringVar(value="Preparing motor...")

        tk.Label(dispensing_panel,
                 textvariable=drop_label_var,
                 font=('Segoe UI', 14, 'bold'),
                 bg="#16213e", fg="#2ecc71").pack(pady=(8, 4))

        tk.Label(dispensing_panel,
                 textvariable=status_label_var,
                 font=('Segoe UI', 11),
                 bg="#16213e", fg="#bdc3c7").pack(pady=(0, 10))

        progress = ttk.Progressbar(dispensing_panel,
                                   mode='indeterminate',
                                   length=300)
        progress.pack(pady=12)
        progress.start(10)

        dispensing_window.update()
        self.play_medicine_sound(medicine)

        def update_drop_progress(count):
            drop_label_var.set(f"Dropped: {count} / {qty}")
            dispensing_window.update_idletasks()

        success = True
        max_attempts = max(qty * 8, 8)
        attempts = 0

        while self.current_drop_count < self.expected_drop_count and attempts < max_attempts:
            attempts += 1
            before_count = self.current_drop_count

            status_label_var.set(
                f"Spinning motor... Attempt {attempts} | Count {self.current_drop_count}/{self.expected_drop_count}"
            )
            dispensing_window.update_idletasks()
            self.log_event("DROP", f"Motor spin attempt {attempts} for {medicine} | Current count: {self.current_drop_count}/{self.expected_drop_count}")

            result = self.hardware.servo_run(channel)
            if not result:
                success = False
                self.log_event("SYSTEM", f"Servo error while dispensing {medicine}")
                break

            status_label_var.set(
                f"Waiting for packet sensor... Count {self.current_drop_count}/{self.expected_drop_count}"
            )
            dispensing_window.update_idletasks()

            time.sleep(0.20)

            detected = self.wait_for_new_drop(
                previous_count=before_count,
                timeout=2.8,
                progress_callback=update_drop_progress
            )

            if detected:
                status_label_var.set(
                    f"Item detected. Current count: {self.current_drop_count}/{self.expected_drop_count}"
                )
                self.log_event("DROP", f"Item detected after attempt {attempts} | Count: {self.current_drop_count}/{self.expected_drop_count}")
            else:
                status_label_var.set(
                    f"No item detected. Retrying... Current count: {self.current_drop_count}/{self.expected_drop_count}"
                )
                self.log_event("DROP", f"No item detected after attempt {attempts} | Count: {self.current_drop_count}/{self.expected_drop_count}")

            dispensing_window.update_idletasks()
            time.sleep(0.25)

        progress.stop()
        try:
            dispensing_window.destroy()
        except Exception:
            pass
        if self.active_popup is dispensing_window:
            self.active_popup = None

        if success and self.current_drop_count >= self.expected_drop_count:
            self.log_event("TRANSACTION", f"Dispense success: {medicine} | Qty: {qty} | Total: PHP {total_price:,.2f}")
            self.log_event("DROP", f"Dispense confirmed by sensor: {self.current_drop_count}/{self.expected_drop_count}")
            self.payment_reader.reset_total()
            self.print_receipt_async(medicine, qty=qty)
            self.show_success_popup(medicine, qty, total_price)
        else:
            self.log_event(
                "DROP",
                f"Dispense failed or incomplete: {medicine} | Expected: {qty} | Detected: {self.current_drop_count}"
            )
            messagebox.showerror(
                "Dispense Error",
                f"Dispensing could not confirm the full quantity.\n\n"
                f"Expected: {qty}\n"
                f"Detected: {self.current_drop_count}\n\n"
                f"Please check the machine, medicine path, or IR sensor alignment."
            )


def main():
    root = tk.Tk()
    app = MedicineDispenserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
