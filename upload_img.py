from flask import Flask, request
import base64
import os
import logging
from logging.handlers import WatchedFileHandler
from datetime import datetime
import requests
import threading
import socket
import torch
from PIL import Image
import sys
import multiprocessing

app = Flask(__name__)

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

start_time = datetime.now()
logger.info(f"{start_time}，開始記錄")

def capture_image(sequence, upload_dir):
    try:
        url = f'http://{camera_ip}/webcapture.jpg?command=snap&channel=1'
        res = requests.Session()
        response = res.get(url)
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
        pass

def schedule_image_captures(upload_dir):
    try:
        intervals = [0, 1, 2]  # Immediately, 1 second later, 2 seconds later
        for i, interval in enumerate(intervals):
            timer = threading.Timer(interval, capture_image, args=(i + 1, upload_dir))
            timer.start()
    except Exception as e:
        logger.error(f'Error capturing image {sequence}: {str(e)}')
        print(e)
        pass

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
    upload_dir = r"./uploads/"
    # camera_ip = input("Please enter the camera IP address (default 192.168.50.197): ") or '192.168.50.197'
    #cloud_detection_ip = input("Please enter the cloud detection IP address (default 192.168.50.200): ") or '192.168.50.200'
    camera_ip = '192.168.50.197'  # 默认值
    cloud_detection_ip = '192.168.50.200'  # 默认值
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    try:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        base64_image = request.json["image"]
        image_data = base64.b64decode(base64_image)
        filename = f"{current_time}.png"
        image_path = os.path.join(upload_dir, filename)
        with open(image_path, "wb") as f:
            f.write(image_data)
        logger.info(f"完成主動回傳的檔案 {image_path} 寫入")
        # upload_captured_image(image_path)
        digit_prediction(image_path)
        schedule_image_captures(upload_dir)
        # 獲得snapshot三次
        return {"message": "Uploaded successfully.", "image_path": image_path}, 200
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return {"error": str(e)}, 500
        pass

def digit_prediction(image_path):
    try:
        # 讀取圖片
        # image_path = '/Users/jimmy_kuo/Documents/camera-test-tool/103600398.jpg'
        image = Image.open(image_path)
        results = plate_detection_model(image)
        detected_boxes = results.pandas().xyxy[0]  # 0 代表第一张图像（如果一次处理多张则可能不同）

        for index, row in detected_boxes.iterrows():
            x1, y1, x2, y2 = row['xmin'], row['ymin'], row['xmax'], row['ymax']

        # 裁剪车牌图像
        plate_image = image.crop((x1, y1, x2, y2))
        plate_image.show()  # 显示裁剪的车牌图像


        # 辨識車牌上的文字
        recognized_text = plate_recognition_model(plate_image).pandas().xyxy[0] 

        # 根据xmin排序，从左至右
        sorted_text = recognized_text.sort_values(by='xmin')

        print("辨識結果：",  ''.join(sorted_text.name.tolist()))
    except Exception as e:
        logger.error(f'Error predicting image : {str(e)}')
        print(e)
        pass

def get_resource_path(relative_path):
    """ 獲取資源文件的絕對路徑 """
    try:
        # 運行打包後的可執行文件時，PyInstaller 設置了 sys._MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # 在開發環境中，沒有 sys._MEIPASS 這個屬性，加上這段就不需改動程式碼
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

yolo_path = get_resource_path('yolov5')


if __name__ == "__main__":
    multiprocessing.freeze_support()
    plate_detection_model =  torch.hub.load(yolo_path, 'custom', path=f'{yolo_path}/20230821-plate-640-s-640.pt',source='local')
    plate_recognition_model =  torch.hub.load(yolo_path, 'custom', path=f'{yolo_path}/20240102-digit-640-s.pt',source='local')

    camera_ip = input("Please enter the camera IP address (default 192.168.50.197): ") or camera_ip
    cloud_detection_ip = input("Please enter the cloud detection IP address (default 192.168.50.200): ") 
    # 使用 input() 从命令行获取 IP 地址

    app.run(host="0.0.0.0", port=6000, load_dotenv=False, processes=1 , threaded=True
            , use_reloader=False)

    