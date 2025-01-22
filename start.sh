#!/bin/bash

sudo systemctl stop bluetooth

devices=$(bluetoothctl devices | awk '{print $2}')
for device in $devices; do
    echo "Removing device: $device"
    echo "remove $device" | bluetoothctl
done
echo "All devices have been removed."

sudo rm -rf /var/lib/bluetooth/*
sudo systemctl start bluetooth
nohup python3 /home/wugu1/code/main4.py >/home/wugu1/code/output_ble.log 2>&1 &
nohup python3 /home/wugu1/code/main.py >/home/wugu1/code/output_video.log 2>&1 &
echo "Scripts are running in the background. Logs are being written to output_ble.log and output_video.log."
