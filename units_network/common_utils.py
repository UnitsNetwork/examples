import base64
import logging
import logging.config
import os
import sys
from typing import Optional

from base58 import b58decode


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


def configure_cli_logger(
    file: str, config_path: Optional[str] = None
) -> logging.Logger:
    if config_path is None:
        config_path = os.getenv(
            "LOGGING_CONFIG", os.path.join(os.getcwd(), "logging.conf")
        )

    log_dir = os.getenv("LOGGING_DIR", os.getcwd())
    logging.config.fileConfig(config_path, defaults={"LOGGING_DIR": log_dir})
    return logging.getLogger(os.path.basename(file))
