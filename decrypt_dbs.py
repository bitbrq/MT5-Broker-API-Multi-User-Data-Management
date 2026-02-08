from cryptography.fernet import Fernet
import os
import shutil


# Decrypt Database Files for testing purposed only
def decrypt_dbs():
    try:
        aes_key = "Mmymzl2VBsgMlThKGgkHmJNk6wry0_an1e21C_Fj8Ig="
        
        fernet = Fernet(aes_key.encode())
        source_dir = "dbs"
        target_dir = "decrypted_dbs"

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        for file in os.listdir(source_dir):
            db_file = os.path.join(source_dir, file)
            if os.path.isfile(db_file):
                shutil.copy(db_file, target_dir)
                target_file = os.path.join(target_dir, file)
                with open(target_file, "rb") as file:
                    data = file.read()
                decrypted = fernet.decrypt(data)
                with open(target_file, "wb") as file:
                    file.write(decrypted)

        print("Decryption completed successfully")
    except Exception as e:
        print(f"Error: {e}")

decrypt_dbs()