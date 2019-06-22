from simplecrypt import encrypt, decrypt
import random
import base64

CHAR_LITERALS = "abcdefghijklmopqrstuvwxyz1234567890"


def random_password_generator():
    password = ''
    for k in range(32):
        password += random.choice(CHAR_LITERALS)
    return password


def generate_secret_data(password, sms_sid):
    cipher_text = encrypt(password, sms_sid)
    b64encoded_cipher = base64.b64encode(cipher_text)
    return b64encoded_cipher


def generate_plaint_text_from_secret_data(cipher_text, password):
    b64encoded_cipher = base64.b64decode(cipher_text)
    try:
        sms_sid = decrypt(b64encoded_cipher, password)
    except Exception:
        return ""
    else:
        return sms_sid


