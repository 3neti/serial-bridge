import json
import base64
from datetime import datetime
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

ANDROID_PUBLIC_KEY = "d21f8aaa37aa3b399843196ea62f48490092cb0a7a3a0f49ac17fdefbe311a0d"
DEVICE_PRIVATE_KEY = "f58e5fd0bf4dd506d9cefa35a37dc557b2376abdd0e7b72a9904513d7310424f"

total_coin = 0

verify_key = VerifyKey(bytes.fromhex(ANDROID_PUBLIC_KEY))
signing_key = SigningKey(bytes.fromhex(DEVICE_PRIVATE_KEY))

def load_config(path="config.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)

def pad_b64(s: str) -> str:
    return s + "=" * ((4 - len(s) % 4) % 4)

def get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def verify_and_parse(message: str):
    try:
        if "." not in message:
            raise ValueError("Missing delimiter between payload and signature.")
        
        b64_payload, b64_signature = message.strip().split(".")
        payload_bytes = base64.b64decode(pad_b64(b64_payload))
        signature_bytes = base64.b64decode(pad_b64(b64_signature))
        verify_key.verify(payload_bytes, signature_bytes)
        print("✅ Signature verified from Android.")

        return json.loads(message)
    except (ValueError, BadSignatureError, base64.binascii.Error) as e:
        print(f"❌ Signature verification failed: {e}")
        return None

def sign_and_send_to_android(payload: dict, android):
    message = json.dumps(payload, separators=(",", ":")).encode()
    b64_message = base64.b64encode(message).decode()
    signature = signing_key.sign(message).signature
    b64_signature = base64.b64encode(signature).decode()
    combined = f"{b64_message}.{b64_signature}\n"
    android.write(combined.encode())
    print("📤 Sent encrypted response to Android.")

def handle_verified_android_command(payload: dict, coin, card, android, context: dict):
    global total_coin
    context["last_transaction_id"] = payload.get("transactionId")
    function = payload.get("function")
    params = payload.get("params", {})

    if function == "RetrieveDeviceID":
        print("🔎 Android requested: RetrieveDeviceID")
        response = {
            "transactionId": context["last_transaction_id"],
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Device identity retrieved.",
            "data": {
                "retrieveDeviceId": "DEVICE_SerialBridge_001",
                "phoneNumber": "+639171234567",
                "ipAddress": "192.168.100.5",
                "deviceMac": "00:1A:2B:3C:4D:5E"
            }
        }
        sign_and_send_to_android(response, android)

    elif function == "InitializeDevice":
        print("🧰 Android requested: InitializeDevice")
        response = {
            "transactionId": context["last_transaction_id"],
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Initialization successful.",
            "data": {
                "businessProcessId": params.get("businessProcessId", "unknown"),
                "deviceInitBusinessId": f"DEVICE_{params.get('businessProcessId', '000')}",
                "data": {
                    "cashBoxInfo": {
                        "businessProcessId": params.get("businessProcessId", "unknown"),
                        "chargeTotalAmount": "0.00",
                        "receivedAmount": "0.00"
                    },
                    "cardBoxInfo": {
                        "businessProcessId": params.get("businessProcessId", "unknown"),
                        "deviceBusinessId": f"DEVICE_{params.get('businessProcessId', '000')}",
                        "quantity": 50
                    }
                }
            }
        }
        sign_and_send_to_android(response, android)

    elif function == "PrepareCards":
        print("📦 Android requested: PrepareCards")
        quantity = params.get("quantity", 1)
        auto_recycle = params.get("autoRecycleTime", 300)
        card.write(f"PREPARE_CARDS={quantity},{auto_recycle}\n".encode())

        response = {
            "transactionId": context["last_transaction_id"],
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Cards prepared",
            "data": {
                "businessProcessId": params.get("businessProcessId", "unknown"),
                "deviceBusinessId": f"DEVICE_{params.get('businessProcessId', '000')}"
            }
        }
        sign_and_send_to_android(response, android)

    elif function == "CheckCardQuantity":
        print("📦 Android requested: CheckCardQuantity")
        is_alarm = "Y"
        quantity = 5 if is_alarm == "Y" else None
        response = {
            "transactionId": context["last_transaction_id"],
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Card quantity checked",
            "data": {
                "isAlarm": is_alarm,
                **({"quantity": quantity} if quantity else {})
            }
        }
        sign_and_send_to_android(response, android)

    elif function == "GetMoneyAmount":
        print("💰 Android requested: GetMoneyAmount")
        response = {
            "transactionId": context["last_transaction_id"],
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Amount retrieved",
            "data": {
                "businessProcessId": params.get("businessProcessId", "unknown"),
                "receivedAmount": "100.00"
            }
        }
        sign_and_send_to_android(response, android)

    elif function == "RetrieveDeviceID":
        print("💰 Android requested: RetrieveDeviceID")
        response = {"transactionId":context["last_transaction_id"],"resultCode":"200","resultMessage":"Success","responseTime":"20250410100113","data":{"retrieveDeviceId":"DEVICE_Simulated_001","phoneNumber":"+1234567890","ipAddress":"192.168.1.100","deviceMac":"00:1A:2B:3C:4D:5E"}}
        sign_and_send_to_android(response, android)

    elif function == "ActivateCashModule":
        total_coin = 0
        print("💰 Android requested: Start coin acceptor")
        coin.write(b"COIN_ACCEPT=1\n")
        response = {"transactionId":context["last_transaction_id"],"responseTime":"20250410100115","resultCode":"200","data":{"transactionId":"ActivateCashModule_374a315b_20250410100114_62196579","businessProcessId":"374a315b","deviceBusinessId":"CASH_001"}}
        sign_and_send_to_android(response, android)

    elif function == "DeactivateCashModule":
        total_coin = 0
        print("🛑 Android requested: Stop coin acceptor")
        coin.write(b"COIN_ACCEPT=0\n")

    elif function == "DispenseCard":
        print("📤 Android requested: Dispense SIM card")
        card.write(b"c\n")

    elif function == "EjectCard":
        print("📤 Android requested: Eject SIM card")
        card.write(b"d\n")

    else:
        print(f"❓ Unknown Android command: {function}")



def handle_coin_feedback(line: str, android, context: dict):
    global total_coin
    txn_id = context.get("last_transaction_id", "mock_txn")
    if line.startswith("COIN_VALUE"):
        par = line.split("=")
        amount = par[1].replace('COIN_VALUE', '')
        total_coin += int(amount)
        payload = {
            "deviceTransactionId": "Coin update",
            "responseTime": get_timestamp(),
            "requestTime": "20250423131000", # TODO: Get from request
            "resultCode": "200",
            "resultMessage": "Coin inserted",
            'retrieveDeviceId': 'DEVICE_001',
            'function': 'UpdateCashReceived',
            "params": {
                "businessProcessId": "mock_process_001",
                'chargeTotalAmount': '99.0',
                "receivedTotalAmount": str(total_coin),
                "currentReceivedAmount": amount + '.0',
                'isClosed': 'N'
            }
        }
        print(payload)
        sign_and_send_to_android(payload, android)

    elif line.startswith("CASH_BOX_REMOVED"):
        total_amount = line.split("=")[1]
        payload = {
            "deviceTransactionId": "cashbox_takeaway_001",
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Cash box opened manually",
            "data": {
                "totalAmount": total_amount
            }
        }
        sign_and_send_to_android(payload, android)

    elif line.startswith("REFUND_TRIGGERED"):
        amount = line.split("=")[1]
        payload = {
            "deviceTransactionId": "refund_triggered_001",
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Refund initiated",
            "data": {
                "businessProcessId": "mock_process_001",
                "deviceBusinessProcessId": "DEVICE_mock_process_001",
                "refundAmount": amount
            }
        }
        sign_and_send_to_android(payload, android)

    else:
        print(f"🔕 Unrecognized coin feedback: {line}")



def handle_card_feedback(line: str, android, context: dict):

    txn_id = context.get("last_transaction_id", "mock_txn")
    print("card handler",line)
    if line.startswith("DISPENSED"):
        print("card handler/dispensed",line)
        parts = line.split("=")
        print("card handler/dispensed/parts",parts)
        params = parts[1].split(',')
        print("card handler/dispensed/parts",params)
        count = int(params[0])
        ccid = str(params[1])
        payload = {
            "deviceTransactionId": "card_dispense_notice_001",
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Card dispensed",
            "data": {
                "businessProcessId": "mock_process_001",
                "iccid": ccid,
                "totalDispensedAmount": count
            }
        }
        sign_and_send_to_android(payload, android)

    elif line.startswith("LOW_STOCK"):
        quantity = line.split("=")[1]
        payload = {
            "deviceTransactionId": "low_stock_alert_001",
            "responseTime": get_timestamp(),
            "resultCode": "200",
            "resultMessage": "Low stock detected",
            "data": {
                "simQuantity": int(quantity)
            }
        }
        sign_and_send_to_android(payload, android)

    else:
        print(f"🔕 Unrecognized coin feedback: {line}")