import logging
import sys
import time
import base64
from typing import Optional

from base58 import b58decode


def repeat(func, interval_ms=3000.0):
    while True:
        result = func()
        if result:
            return result
        time.sleep(interval_ms / 1000)


def get_argument_value(arg_name):
    try:
        index = sys.argv.index(arg_name)
        if index != -1 and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    except ValueError:
        pass
    return None


def hex_to_base64(hex_string: str) -> str:
    bytes_data = bytes.fromhex(hex_string)
    base64_data = base64.b64encode(bytes_data)
    return base64_data.decode("utf-8")


def waves_public_key_hash_bytes(waves_address: str):
    return b58decode(waves_address)[2:22]


def clean_hex_prefix(hex: str) -> str:
    return hex[2:] if hex.startswith("0x") else hex


def configure_script_logger(name: str, to_file: Optional[str] = None) -> logging.Logger:
    # Remove a handler from PyWaves
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    handlers = [logging.StreamHandler(sys.stdout)]
    if to_file:
        handlers.append(logging.FileHandler(to_file, mode="a"))

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        handlers=handlers,
    )

    return logging.getLogger(name)
