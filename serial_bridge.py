from core import (
    verify_and_parse,
    sign_and_send_to_android,
    handle_verified_android_command,
    handle_controller_feedback,
    load_config
)

import serial
import threading

config = load_config()


ANDROID_PORT = config["android_port"]
CONTROLLER_PORT = config["controller_port"]
BAUD_RATE = config["baud_rate"]
# ANDROID_PORT = "/dev/ttys009"
# CONTROLLER_PORT = "/dev/ttys012"
# BAUD_RATE = 115200

android = serial.Serial(ANDROID_PORT, BAUD_RATE, timeout=1)
controller = serial.Serial(CONTROLLER_PORT, BAUD_RATE, timeout=1)

print(f"🟢 Serial Bridge active: Android@{ANDROID_PORT} ⇄ Controller@{CONTROLLER_PORT}")

context = {"last_transaction_id": None}

def listen_to_controller():
    while True:
        try:
            line = controller.readline().decode().strip()
            if line:
                print(f"🎯 Controller says: {line}")
                handle_controller_feedback(line, android, context)
        except Exception as e:
            print(f"⚠️ Controller read error: {e}")

def main():
    threading.Thread(target=listen_to_controller, daemon=True).start()

    try:
        while True:
            line = android.readline().decode().strip()
            if not line:
                continue

            print(f"\n📥 Encrypted message from Android: {line}")
            verified = verify_and_parse(line)
            if verified:
                handle_verified_android_command(verified, controller, android, context)

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