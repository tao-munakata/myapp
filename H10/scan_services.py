"""Polar H10 BLE サービス・キャラクタリスティック列挙スクリプト"""
import asyncio
from bleak import BleakClient

POLAR_H10_ADDR = "24:AC:AC:1F:BD:C9"

async def scan():
    print(f"接続中: {POLAR_H10_ADDR}")
    async with BleakClient(POLAR_H10_ADDR, timeout=20.0) as client:
        print(f"接続成功: {client.is_connected}")
        print()
        for service in client.services:
            print(f"[Service] {service.uuid}  ({service.description})")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  [Char]  {char.uuid}  [{props}]  ({char.description})")
                for desc in char.descriptors:
                    print(f"    [Desc] {desc.uuid}  ({desc.description})")
        print()

asyncio.run(scan())
