import sys
import os
import subprocess
import socket
import logging
from logging.handlers import WatchedFileHandler
from datetime import datetime
import requests
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from flask import Flask, request
import base64

# Get local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Local IP address
local_ip = get_local_ip()
print(f"Now ip is: {local_ip}")

# Configure logging
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
handler = WatchedFileHandler(log_file)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)
start_time = datetime.now()
logger.info(f"{start_time}，開始記錄")

camera_ip = '192.168.50.197'
cloud_detection_ip = '192.168.50.200'

@app.route("/upload_image", methods=["POST"])
def upload_image():
    try:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        base64_image = request.json["image"]
        image_data = base64.b64decode(base64_image)
        upload_dir = r"./uploads/"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        filename = f"{current_time}.png"
        image_path = os.path.join(upload_dir, filename)
        with open(image_path, "wb") as f:
            f.write(image_data)
        logger.info(f"完成主動回傳的檔案 {image_path} 寫入")

        # 獲得snapshot三次
        return {"message": "Uploaded successfully.", "image_path": image_path}, 200
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return {"error": str(e)}, 500

# Define the Flask app and tkinter GUI integration
def create_gui(app):
    root = tk.Tk()
    root.title("Flask 應用控制台")

    # Text area for logs
    log_area = scrolledtext.ScrolledText(root, width=80, height=20, state='disabled')
    log_area.grid(column=0, row=0, sticky='ew', padx=10, pady=10)

    class TextHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            log_area.config(state='normal')
            log_area.insert(tk.END, msg + '\n')
            log_area.config(state='disabled')
            log_area.yview(tk.END)

    logger.addHandler(TextHandler())

    def on_close():
        if messagebox.askokcancel("退出", "確定要退出程序嗎？"):
            os._exit(0)

    close_button = tk.Button(root, text="關閉程式", command=on_close)
    close_button.grid(column=0, row=1, padx=10, pady=10)

    def run_flask():
        app.run(debug=True, host='0.0.0.0', port=6000)

    threading.Thread(target=run_flask, daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    create_gui(app)