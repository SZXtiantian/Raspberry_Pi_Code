import os
import time
from picamera2 import Picamera2, MappedArray, Preview
import cv2
import datetime


def get_unix_timestamp():
    return int(time.time() * 1000)


# 视频叠加的时间戳配置
colour = (0, 0, 255)
origin = (10, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

# 初始化相机
picam2 = Picamera2()
picam2.set_controls({
    "ExposureTime": 300000,
    "AnalogueGain": 4.0,
    "AwbEnable": False,
    "ColourGains": [3.0, 1.8],
    "NoiseReductionMode": "HighQuality"
})


# picam2.start_preview(Preview.QTGL)

# 添加时间戳的回调函数
def apply_timestamp(request):
    timestamp = str(int(time.time() * 1000))
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)


picam2.pre_callback = apply_timestamp

# 设置视频保存时长为10分钟（600秒）
video_duration = 600  # 10分钟
target_folder = "/media/wugu1"
output_folder_base = "/media/wugu1/videos"

if os.path.exists(target_folder):
    # 如果文件夹不存在，则创建
    if not os.path.exists(output_folder_base):
        os.makedirs(output_folder_base)

    # 查找现有的视频文件夹，并递增命名
    i = 1
    while os.path.exists(f"{output_folder_base}/video_{i}"):
        i += 1
    output_folder = f"{output_folder_base}/video_{i}"
else:
    output_folder = "videos"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

try:
    while True:
        # 生成带时间戳的文件名
        timestamp = str(int(time.time() * 1000))
        video_filename = os.path.join(output_folder, f"video_{timestamp}.mp4")

        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S") + f".{current_time.microsecond // 1000:03d}"

        print(f"[{formatted_time}]: 开始录制视频  {video_filename}")
        # 录制视频
        picam2.start_and_record_video(video_filename, duration=video_duration)
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S") + f".{current_time.microsecond // 1000:03d}"

        print(f"[{formatted_time}]: 录制完成: {video_filename}\n")


except KeyboardInterrupt:
    print("\n手动中断录制\n")

finally:
    picam2.stop()
