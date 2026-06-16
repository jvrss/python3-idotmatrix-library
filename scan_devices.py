"""
Script de diagnóstico: mostra TODOS os dispositivos BLE visíveis.
Execute este script para descobrir o nome e endereço do teu dispositivo 64x64.

Uso:
    python scan_devices.py
"""
import asyncio
import logging
from idotmatrix import ConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)


async def main():
    conn = ConnectionManager()
    print("\n=== A procurar TODOS os dispositivos BLE ===\n")
    all_devices = await conn.scanAll()

    if not all_devices:
        print("Nenhum dispositivo BLE encontrado. Verifica se o Bluetooth está ativo.")
    else:
        print(f"\nEncontrados {len(all_devices)} dispositivo(s):\n")
        for d in all_devices:
            print(f"  Endereço : {d['address']}")
            print(f"  Nome     : {d['name']}")
            print()

        print("Para ligar diretamente ao teu dispositivo, usa:")
        print("    await conn.connectByAddress('XX:XX:XX:XX:XX:XX')")
        print("\nSe o nome do dispositivo não começa com 'IDM-',")
        print("adiciona o prefixo correto à lista BLUETOOTH_DEVICE_NAME em idotmatrix/const.py")


if __name__ == "__main__":
    asyncio.run(main())

