from cryptography.fernet import Fernet

# Generate a key using Fernet
key = Fernet.generate_key()

# Print the key in base64 encoding format
print("Generated AES_KEY:", key.decode())
