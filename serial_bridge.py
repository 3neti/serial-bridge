from core import (
    verify_and_parse,
    sign_and_send_to_android,
    handle_verified_android_command,
    handle_coin_feedback,
    handle_card_feedback,
    load_config
)

import serial
import threading

config = load_config()


ANDROID_PORT = config["android_port"]
COIN_PORT = config["coin_port"]
CARD_PORT = config["card_port"]
BAUD_RATE = config["baud_rate"]
# ANDROID_PORT = "/dev/ttys009"
# CONTROLLER_PORT = "/dev/ttys012"
# BAUD_RATE = 115200

android = serial.Serial(ANDROID_PORT, BAUD_RATE, timeout=1)
coin = serial.Serial(COIN_PORT, BAUD_RATE, timeout=1)
card = serial.Serial(CARD_PORT, BAUD_RATE, timeout=1)

print(f"🟢 Serial Bridge active: Android@{ANDROID_PORT} ⇄ Coin@{COIN_PORT} ⇄ Card@{CARD_PORT}")

context = {"last_transaction_id": None}

def listen_to_coin():
    while True:
        try:
            line = coin.readline().decode().strip()
            if line:
                print(f"🎯 Coin says: {line}")
                handle_coin_feedback(line, android, context)
        except Exception as e:
            print(f"⚠️ Coin read error: {e}")


def listen_to_card():
    while True:
        try:
            line = card.readline().decode().strip()
            if line:
                print(f"🎯 Card says: {line}")
                handle_card_feedback(line, android, context)
        except Exception as e:
            print(f"⚠️ Card read error: {e}")

def main():
    threading.Thread(target=listen_to_coin, daemon=True).start()
    threading.Thread(target=listen_to_card, daemon=True).start()

    try:
        while True:
            line = android.readline().decode().strip()
            if not line:
                continue

            print(f"\n📥 Encrypted message from Android: {line}")
            verified = verify_and_parse(line)
            if verified:
                handle_verified_android_command(verified, coin, card, android, context)

                response = {
                    "transactionId": verified.get("transactionId"),
                    "resultCode": "200",
                    "resultMessage": "Acknowledged",
                    "responseTime": "20250423130000"
                }
                sign_and_send_to_android(response, android)

    except KeyboardInterrupt:
        print("\n🛑 Serial Bridge stopped.")

if __name__ == "__main__":
    main()