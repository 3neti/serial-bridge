import base64
import json
from nacl.signing import SigningKey, VerifyKey

def test_signature_verification():
    message = {"function": "ActivateCashModule", "transactionId": "test_txn"}
    encoded = json.dumps(message, separators=(",", ":")).encode()

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    signature = signing_key.sign(encoded).signature

    # Simulate what your bridge does
    try:
        verify_key.verify(encoded, signature)
        assert True
    except:
        assert False, "Signature should be valid"