import json
from core import (
    verify_and_parse,
    sign_and_send_to_android,
    handle_verified_android_command,
    handle_controller_feedback
)
from unittest.mock import MagicMock

def test_signature_roundtrip():
    from nacl.signing import SigningKey
    import base64

    message = {"function": "ActivateCashModule", "transactionId": "test123"}
    payload = json.dumps(message, separators=(",", ":")).encode()
    sk = SigningKey.generate()
    vk = sk.verify_key
    sig = sk.sign(payload).signature
    b64_payload = base64.b64encode(payload).decode()
    b64_sig = base64.b64encode(sig).decode()
    signed = f"{b64_payload}.{b64_sig}"
    decoded = vk.verify(base64.b64decode(b64_payload), base64.b64decode(b64_sig))
    assert json.loads(decoded.decode()) == message

def test_handle_android_command_dispatch():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn123",
        "function": "ActivateCashModule",
        "params": {}
    }

    handle_verified_android_command(payload, controller, android, context)
    controller.write.assert_called_with(b"COIN_ACCEPT=1\n")

def test_prepare_cards_dispatch():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn789",
        "function": "PrepareCards",
        "params": {
            "businessProcessId": "X",
            "quantity": 3,
            "autoRecycleTime": 180
        }
    }

    handle_verified_android_command(payload, controller, android, context)
    controller.write.assert_called_with(b"PREPARE_CARDS=3,180\n")

def test_handle_controller_feedback_coin_value():
    android = MagicMock()
    context = {"last_transaction_id": "mock_txn_001"}
    handle_controller_feedback("COIN_VALUE=50.00", android, context)
    assert android.write.call_count == 1

def test_handle_controller_feedback_low_stock():
    android = MagicMock()
    context = {"last_transaction_id": "mock_txn_002"}
    handle_controller_feedback("LOW_STOCK=2", android, context)
    assert android.write.call_count == 1

def test_initialize_device_response():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn_init_001",
        "function": "InitializeDevice",
        "params": {
            "businessProcessId": "biz001"
        }
    }

    handle_verified_android_command(payload, controller, android, context)
    assert android.write.call_count == 1
    assert context["last_transaction_id"] == "txn_init_001"

def test_check_card_quantity_response():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn_check_qty",
        "function": "CheckCardQuantity",
        "params": {
            "businessProcessId": "qty001"
        }
    }

    handle_verified_android_command(payload, controller, android, context)
    assert android.write.call_count == 1

def test_get_money_amount_response():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn_get_cash",
        "function": "GetMoneyAmount",
        "params": {
            "businessProcessId": "cash001"
        }
    }

    handle_verified_android_command(payload, controller, android, context)
    assert android.write.call_count == 1

def test_retrieve_device_id_response():
    controller = MagicMock()
    android = MagicMock()
    context = {}

    payload = {
        "transactionId": "txn_device_id",
        "function": "RetrieveDeviceID"
    }

    handle_verified_android_command(payload, controller, android, context)
    assert android.write.call_count == 1

import base64
import json

def extract_payload(decoded_msg):
    """Extract and decode base64 payload from signed message."""
    raw = decoded_msg.split(".")[0]
    padded = raw + "=" * ((4 - len(raw) % 4) % 4)
    return json.loads(base64.b64decode(padded).decode())

def test_handle_controller_feedback_cash_box_removed():
    android = MagicMock()
    context = {"last_transaction_id": "mock_txn_cashbox"}
    handle_controller_feedback("CASH_BOX_REMOVED=1234.56", android, context)

    assert android.write.call_count == 1
    encoded = android.write.call_args[0][0].decode()
    payload = extract_payload(encoded)
    assert payload["deviceTransactionId"] == "cashbox_takeaway_001"
    assert payload["data"]["totalAmount"] == "1234.56"

def test_handle_controller_feedback_refund_triggered():
    android = MagicMock()
    context = {"last_transaction_id": "mock_txn_refund"}
    handle_controller_feedback("REFUND_TRIGGERED=200.00", android, context)

    assert android.write.call_count == 1
    encoded = android.write.call_args[0][0].decode()
    payload = extract_payload(encoded)
    assert payload["deviceTransactionId"] == "refund_triggered_001"
    assert payload["data"]["refundAmount"] == "200.00"