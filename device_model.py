#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/11/2 20:47
# @Author  : 钟昊天2021280300
# @FileName: device_model.py
# @Software: PyCharm
# coding:UTF-8
import asyncio
import csv
import os
import threading
import time
import logging
import bleak


# 设备实例 Device instance
class DeviceModel:
    # region 属性 attribute
    # 设备名称 deviceName
    deviceName = "我的设备"

    # 设备数据字典 Device Data Dictionary
    deviceData = {}

    # 设备是否开启
    isOpen = False

    # 临时数组 Temporary array
    TempBytes = []

    # endregion

    def __init__(self, deviceName, BLEDevice, path, callback_method):
        logging.info("Initialize device model")
        # 设备名称（自定义） Device Name
        self.deviceName = deviceName
        self.BLEDevice = BLEDevice
        self.client = None
        self.writer_characteristic = None
        self.isOpen = False
        self.callback_method = callback_method
        self.deviceData = {}
        sanitized_address = self.BLEDevice.address.replace(":", "_")
        # 生成文件名，包含MAC地址和起始时间戳
        self.start_timestamp = 0
        mac_folder_path = f"{path}/{sanitized_address}"
        if not os.path.exists(mac_folder_path):
            os.makedirs(mac_folder_path)
        self.mac_folder_path = mac_folder_path
        self.filename = ""
        # self.filename = f"{mac_folder_path}/{start_timestamp}.csv"
        self.deviceDataBuffer = []  # 数据缓冲区
        self.buffer_lock = threading.Lock()  # 锁，确保线程安全
        self.isWriting = True  # 控制写入线程的运行
        # 启动写入线程
        threading.Thread(target=self.writeDataToCSVPeriodically, args=(self.filename,), daemon=True).start()

    # region 获取设备数据 Obtain device data
    # 设置设备数据 Set device data
    def set(self, key, value):
        # 将设备数据存到键值 Saving device data to key values
        self.deviceData[key] = value

    # 获得设备数据 Obtain device data
    def get(self, key):
        # 从键值中获取数据，没有则返回None Obtaining data from key values
        if key in self.deviceData:
            return self.deviceData[key]
        else:
            return None

    # 删除设备数据 Delete device data
    def remove(self, key):
        # 删除设备键值
        del self.deviceData[key]

    # endregion

    # 打开设备 open Device
    async def openDevice(self):
        logging.info("Opening device......")
        # 获取设备的服务和特征 Obtain the services and characteristic of the device
        async with bleak.BleakClient(self.BLEDevice, timeout=15) as client:
            self.client = client
            self.isOpen = True
            # 设备UUID常量 Device UUID constant
            target_service_uuid = "0000ffe5-0000-1000-8000-00805f9a34fb"
            target_characteristic_uuid_read = "0000ffe4-0000-1000-8000-00805f9a34fb"
            target_characteristic_uuid_write = "0000ffe9-0000-1000-8000-00805f9a34fb"
            notify_characteristic = None

            logging.info("Matching services......")
            for service in client.services:
                if service.uuid == target_service_uuid:
                    logging.info("Service: {service}")
                    logging.info("Matching characteristic......")
                    for characteristic in service.characteristics:
                        if characteristic.uuid == target_characteristic_uuid_read:
                            notify_characteristic = characteristic
                        if characteristic.uuid == target_characteristic_uuid_write:
                            self.writer_characteristic = characteristic
                    if notify_characteristic:
                        break

            # 切换0x96寄存器值为2的输出模式
            await self.setOutputModeTo(0x02)
            # 设置回传速率（假设速率值为0x0A对应100Hz）
            await self.setTransmissionRate(0x0B)

            if notify_characteristic:
                # 设置通知以接收数据 Set up notifications to receive data
                await client.start_notify(notify_characteristic.uuid, self.onDataReceived)

                # 保持连接打开 Keep connected and open
                try:
                    while self.isOpen:
                        if not self.client.is_connected:
                            logging.info("Device disconnected unexpectedly.")
                            self.closeDevice()
                            break
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    logging.info("error!")
                finally:
                    # 在退出时停止通知 Stop notification on exit
                    await client.stop_notify(notify_characteristic.uuid)
            else:
                logging.info("No matching services or characteristic found")

    # 关闭设备  close Device
    def closeDevice(self):
        self.isOpen = False
        self.isOpen = False
        if self.client and self.client.is_connected:
            asyncio.run(self.client.disconnect())  # 断开 BLE 连接
        self.stopWriting()  # 停止写入线程
        logging.info("Device disconnected and stopped.")
        logging.info("The device is turned off")

    # region 数据解析 data analysis
    # 串口数据处理  Serial port data processing
    def onDataReceived(self, sender, data):
        tempdata = bytes.fromhex(data.hex())
        for var in tempdata:
            self.TempBytes.append(var)
            if len(self.TempBytes) == 1 and self.TempBytes[0] != 0x55:
                del self.TempBytes[0]
                continue
            if len(self.TempBytes) == 2 and (self.TempBytes[1] != 0x61 and self.TempBytes[1] != 0x71):
                del self.TempBytes[0]
                continue
            if len(self.TempBytes) == 20:
                self.processData(self.TempBytes)
                self.TempBytes.clear()

    # 数据解析 data analysis
    def processData(self, Bytes):
        # timestamp = time.time()  # 获取当前时间戳
        # parsed_data = [timestamp]  # 初始化数据列表，包含时间戳
        if Bytes[1] == 0x61:
            if self.filename == "":
                start_timestamp = int(time.time() * 1000)
                self.filename = f"{self.mac_folder_path}/{start_timestamp}.csv"
                self.start_timestamp = start_timestamp
                self.deviceDataBuffer.clear()
            Ax = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768 * 16
            Ay = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768 * 16
            Az = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768 * 16
            Gx = self.getSignInt16(Bytes[9] << 8 | Bytes[8]) / 32768 * 2000
            Gy = self.getSignInt16(Bytes[11] << 8 | Bytes[10]) / 32768 * 2000
            Gz = self.getSignInt16(Bytes[13] << 8 | Bytes[12]) / 32768 * 2000
            '''加速度 角速度 时间戳 数据包(切换0x96寄存器值为2时输出）'''
            # print("timeStamp: ", end='')
            # print(Bytes[17], end=' ')
            # print(Bytes[16], end=' ')
            # print(Bytes[15], end=' ')
            # print(Bytes[14], end=' ')

            MS = self.getSignInt16(Bytes[17] << 24 | Bytes[16] << 16 | Bytes[15] << 8 | Bytes[14])
            parsed_data = [MS]
            parsed_data.extend([
                round(Ax, 10), round(Ay, 10), round(Az, 10),
                round(Gx, 10), round(Gy, 10), round(Gz, 10),
                # round(AngX, 3), round(AngY, 3), round(AngZ, 3)
            ])
            # self.set("Time", round(MS, 16))
            # self.set("AccX", round(Ax, 3))
            # self.set("AccY", round(Ay, 3))
            # self.set("AccZ", round(Az, 3))
            # self.set("AsX", round(Gx, 3))
            # self.set("AsY", round(Gy, 3))
            # self.set("AsZ", round(Gz, 3))

            # 添加数据到 parsed_data
            if parsed_data:
                self.addToBuffer(parsed_data)
        # self.callback_method(self)

    # 获得int16有符号数 Obtain int16 signed number
    @staticmethod
    def getSignInt16(num):
        if num >= pow(2, 15):
            num -= pow(2, 16)
        return num

    # endregion

    # 发送串口数据 Sending serial port data
    async def sendData(self, data):
        try:
            if self.client.is_connected and self.writer_characteristic is not None:
                await self.client.write_gatt_char(self.writer_characteristic.uuid, bytes(data))
        except Exception as ex:
            logging.info(ex)

    # 读取寄存器 read register
    async def readReg(self, regAddr):
        # 封装读取指令并向串口发送数据 Encapsulate read instructions and send data to the serial port
        await self.sendData(self.get_readBytes(regAddr))

    async def setOutputModeTo(self, value):
        """
        切换 0x96 寄存器值为 2 的输出模式
        """
        regAddr = 0x96

        await self.writeReg(regAddr, value)
        logging.info("Switched 0x96 register to output mode 2")

    async def setTransmissionRate(self, rate_value):
        """
        设置设备的回传速率
        :param rate_value: 回传速率的值（0x0A 为100Hz，需根据设备文档确认）
        """
        # 假设回传速率的寄存器地址为 0x03
        regAddr = 0x03
        await self.writeReg(regAddr, rate_value)
        logging.info(f"Set transmission rate to {rate_value}")

    # 写入寄存器 Write Register
    async def writeReg(self, regAddr, sValue):
        # 解锁 unlock
        await self.unlock()
        # 延迟100ms Delay 100ms
        time.sleep(0.1)
        # 封装写入指令并向串口发送数据
        await self.sendData(self.get_writeBytes(regAddr, sValue))
        # 延迟100ms Delay 100ms
        time.sleep(0.1)
        # 保存 save
        await self.save()

    # 读取指令封装 Read instruction encapsulation
    @staticmethod
    def get_readBytes(regAddr):
        # 初始化
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = 0x27
        tempBytes[3] = regAddr
        tempBytes[4] = 0
        return tempBytes

    # 写入指令封装 Write instruction encapsulation
    @staticmethod
    def get_writeBytes(regAddr, rValue):
        # 初始化
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = regAddr
        tempBytes[3] = rValue & 0xff
        tempBytes[4] = rValue >> 8
        return tempBytes

    # 解锁 unlock
    async def unlock(self):
        cmd = self.get_writeBytes(0x69, 0xb588)
        await self.sendData(cmd)  # 添加 await 关键字

    # 保存 save
    async def save(self):
        cmd = self.get_writeBytes(0x00, 0x0000)
        await self.sendData(cmd)  # 添加 await 关键字

        # 将数据添加到缓冲区

    def addToBuffer(self, data):
        with self.buffer_lock:
            self.deviceDataBuffer.append(data)

        # 定时批量写入缓冲区数据到 CSV 文件

    def writeDataToCSVPeriodically(self, filename, max_ms=600):
        while self.isWriting:
            time.sleep(6)
            if self.filename == "":
                continue
            with self.buffer_lock:
                if self.deviceDataBuffer:
                    with open(self.filename, mode='a', newline='') as file:
                        writer = csv.writer(file, delimiter=' ')
                        writer.writerows(self.deviceDataBuffer)
                        logging.info(f"Wrote {len(self.deviceDataBuffer)} records to {self.filename}")
                        self.deviceDataBuffer.clear()
                    end_timestamp = int(time.time())
                    if end_timestamp - self.start_timestamp // 1000 >= max_ms:
                        self.filename = ""

    # 停止写入线程
    def stopWriting(self):
        self.isWriting = False
