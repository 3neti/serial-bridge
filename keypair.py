from nacl.signing import SigningKey

signing_key = SigningKey.generate()
verify_key = signing_key.verify_key

print("PRIVATE (base64):", signing_key.encode().hex())
print("PUBLIC  (base64):", verify_key.encode().hex())