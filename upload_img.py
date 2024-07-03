from flask import Flask, request
import base64
import os
import logging
from logging.handlers import WatchedFileHandler
from datetime import datetime
import requests
import threading
import socket

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
print(f"Now local computer IP is : {local_ip}")

# Configure logging
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
handler = WatchedFileHandler(log_file)  # Use WatchedFileHandler instead of TimedRotatingFileHandler
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)
start_time = datetime.now()
logger.info(f"{start_time}，開始記錄")

# 使用 input() 从命令行获取 IP 地址
camera_ip = input("Please enter the camera IP address (default 192.168.50.197): ") or '192.168.50.197'
cloud_detection_ip = input("Please enter the cloud detection IP address (default 192.168.50.200): ") or '192.168.50.200'


def capture_image(sequence, upload_dir):
    try:
        url = f'http://{camera_ip}/webcapture.jpg?command=snap&channel=1'
        response = requests.get(url)
        if response.status_code == 200:
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{current_time}_captured_{sequence}.jpg'
            image_path = os.path.join(upload_dir, filename)
            with open(image_path, 'wb') as f:
                f.write(response.content)
            # upload_captured_image(image_path)
            logger.info(f'Captured image {sequence} saved to {image_path}')
        else:
            logger.error(f'Failed to capture image {sequence}. Status code: {response.status_code}')
    except Exception as e:
        logger.error(f'Error capturing image {sequence}: {str(e)}')
        print(e)

def schedule_image_captures(upload_dir):
    intervals = [0, 1, 2]  # Immediately, 1 second later, 2 seconds later
    for i, interval in enumerate(intervals):
        timer = threading.Timer(interval, capture_image, args=(i + 1, upload_dir))
        timer.start()

def upload_captured_image(image_path):
    '''上傳雲端辨識系統'''
    try:
        url = f"http://{cloud_detection_ip}/lpr/single/image"
        with open(image_path, "rb") as image_file:
            files = {
                "image": (image_path, image_file, "image/jpeg")
            }
            headers = {
                "accept": "application/json"
            }
            response = requests.post(url, headers=headers, files=files)
            if response.status_code == 200:
                logger.info(f'Successfully uploaded {image_path} to {url}')                
                logger.info(response.json())
            else:
                logger.error(f'Failed to upload {image_path}. Status code: {response.status_code}')
    except Exception as e:
        logger.error(f'Error uploading image {image_path}: {str(e)}')
        pass

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
        upload_captured_image(image_path)

        schedule_image_captures(upload_dir)
        # 獲得snapshot三次
        return {"message": "Uploaded successfully.", "image_path": image_path}, 200
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6000)