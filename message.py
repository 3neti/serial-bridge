import base64, json
from nacl.signing import SigningKey

signing_key = SigningKey.generate()  # Simulate Android's key
verify_key = signing_key.verify_key

print("ANDROID_PUBLIC_KEY:", verify_key.encode().hex())

payload = {
    "transactionId": "txn_001",
    "function": "ActivateCashModule",
    "requestTime": "20250423125900"
}
message = json.dumps(payload, separators=(",", ":")).encode()
b64_message = base64.b64encode(message).decode()
signature = signing_key.sign(message).signature
b64_signature = base64.b64encode(signature).decode()

print("SEND THIS TO DEVICE:")
print(f"{b64_message}.{b64_signature}")