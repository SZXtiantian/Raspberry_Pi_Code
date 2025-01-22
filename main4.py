import asyncio
import os

from bleak import BleakClient, BleakScanner
import device_model
import logging
import random

# 设置日志格式
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 蓝牙设备的MAC地址列","
# MAC_ADDRESSES = [":::::",":::::",":::::"]
# MAC_ADDRESSES = ["F3:67:22:F9:1E:B9","DE:A3:7E:6A:C5:BC","D2:56:A0:22:B2:1B"]
# MAC_ADDRESSES = ["EE:01:EF:5E:79:BA", "CE:2E:98:7E:BC:4D", "E3:C5:0E:D7:C7:26"]
MAC_ADDRESSES = ["DC:A8:A0:E8:F2:D9", "DE:A3:7E:6A:C5:BC"]


# 数据更新回调函数
def updateData(DeviceModel):
    logging.info(f"Updated data: {DeviceModel.deviceData}")


# 异步连接设备
async def connect_device(mac_address, path):
    while True:
        logging.info(f"Attempting to connect to {mac_address}...")
        try:
            # 扫描设备
            device = await BleakScanner.find_device_by_address(mac_address, timeout=10)
            if device:
                logging.info(f"Device found: {mac_address}")
                ble_device = device_model.DeviceModel("MyBle5.0", device, path, updateData)

                # 打开设备并建立连接
                await ble_device.openDevice()
                logging.info(f"Connected to {mac_address}")

                # 创建一个事件，用于处理断连后退出阻塞
                disconnect_event = asyncio.Event()

                # 创建BleakClient并设置断连回调
                async with BleakClient(device) as client:
                    client.set_disconnected_callback(
                        lambda _: disconnect_event.set()
                    )
                    try:
                        # 等待断连事件触发
                        await disconnect_event.wait()
                        logging.warning(f"Device {mac_address} disconnected.")
                    except asyncio.CancelledError:
                        logging.info(f"Connection to {mac_address} cancelled.")
            else:
                logging.warning(f"Device {mac_address} not found, retrying...")
        except Exception as ex:
            logging.warning(f"Failed to connect to {mac_address}: {ex}")
        finally:
            # 确保扫描间隔，避免蓝牙资源过度使用
            random_value = random.randint(0, 7)
            await asyncio.sleep(random_value)


# 主函数
async def main():
    # 检查IMU文件夹是否存在，不存在则创建
    folder_path = "F:/Raspberry_Pi_Code/IMU"

    # 树莓派则去掉下面的注释，并注释上一句
    # folder_path = "/media/wugu1/IMU"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # 创建以MAC地址命名的文件夹
    # 查找现有的视频文件夹，并递增命名
    i = 1
    while os.path.exists(f"{folder_path}/IMU_{i}"):
        i += 1
    path = f"{folder_path}/IMU_{i}"
    tasks = [asyncio.create_task(connect_device(mac, path)) for mac in MAC_ADDRESSES]
    await asyncio.gather(*tasks)


if __name__ == "__main__":

    asyncio.run(main())
