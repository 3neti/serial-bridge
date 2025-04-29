import json
import base64
import serial
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

SERIAL_PORT = "/dev/ttys010"  # Paired with the listener
BAUD_RATE = 115200

ANDROID_PRIVATE_KEY = "f58e5fd0bf4dd506d9cefa35a37dc557b2376abdd0e7b72a9904513d7310424f"
DEVICE_PUBLIC_KEY = "d21f8aaa37aa3b399843196ea62f48490092cb0a7a3a0f49ac17fdefbe311a0d"

signing_key = SigningKey(bytes.fromhex(ANDROID_PRIVATE_KEY))
verify_key = VerifyKey(bytes.fromhex(DEVICE_PUBLIC_KEY))

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)

# Build signed ActivateCashModule message
# payload = {
#     "transactionId": "txn_537",
#     "function": "ActivateCashModule",
#     "requestTime": "20250423125900"
# }

# payload = {
#   "transactionId": "RetrieveDeviceID_NON_20250423125900_00112233",
#   "function": "RetrieveDeviceID",
#   "requestTime": "20250423125900"
# }

# payload = {
#   "transactionId": "InitializeDevice_999_20250423125900_99887766",
#   "function": "InitializeDevice",
#   "requestTime": "20250423125900",
#   "params": {
#     "appMac": "00:1A:2B:3C:4D:5E",
#     "deviceMac": "00:1A:2B:3C:4D:5E",
#     "businessProcessId": "999"
#   }
# }

# payload = {
#   "transactionId": "PrepareCards_123_20250423120059_33445566",
#   "function": "PrepareCards",
#   "requestTime": "20250423120059",
#   "params": {
#     "businessProcessId": "123",
#     "quantity": 5,
#     "autoRecycleTime": 300
#   }
# }

# payload = {
#   "transactionId": "CheckCardQuantity_456_20250423120059_11223344",
#   "function": "CheckCardQuantity",
#   "requestTime": "20250423120059",
#   "params": {
#     "businessProcessId": "456"
#   }
# }

payload = {
  "transactionId": "GetMoneyAmount_999_20250423120059_22334455",
  "function": "GetMoneyAmount",
  "requestTime": "20250423120059",
  "params": {
    "businessProcessId": "999"
  }
}

message = json.dumps(payload, separators=(",", ":")).encode()
b64_message = base64.b64encode(message).decode()
signature = signing_key.sign(message).signature
b64_signature = base64.b64encode(signature).decode()

signed_message = f"{b64_message}.{b64_signature}\n"
print("📤 Sending signed request to listener:")
print(signed_message)
ser.write(signed_message.encode())

print("\n⏳ Listening for signed responses from device...\n")

try:
    while True:
        line = ser.readline().decode().strip()
        if line:
            try:
                print(f"\n📥 Received: {line}")
                msg_b64, sig_b64 = line.split(".")
                decoded_msg = base64.b64decode(msg_b64)
                decoded_sig = base64.b64decode(sig_b64)

                verify_key.verify(decoded_msg, decoded_sig)
                parsed_response = json.loads(decoded_msg)
                print("✅ Verified response:")
                print(json.dumps(parsed_response, indent=2))
            except (ValueError, BadSignatureError) as e:
                print(f"❌ Signature verification failed: {e}")
except KeyboardInterrupt:
    print("\n🛑 Stopped listening.")

ser.close()