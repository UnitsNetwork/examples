import base64
import logging
import logging.config
import os
from typing import Optional

from base58 import b58decode
from ens.ens import HexAddress
from hexbytes import HexBytes
from pywaves import pw
from importlib.resources import files


def hex_to_base64(x: HexBytes) -> str:
    return base64.b64encode(x).decode("utf-8")


def waves_public_key_hash_bytes(acc: pw.Address) -> HexAddress:
    return b58decode(acc.address)[2:22]  # type: ignore


def configure_cli_logger(
    file: str, config_path: Optional[str] = None
) -> logging.Logger:
    if config_path is None:
        config_path = os.getenv(
            "LOGGING_CONFIG", os.path.join(os.getcwd(), "logging.conf")
        )
    if not os.path.exists(config_path):
        config_path = files("units_network").joinpath("logging.conf")

    log_dir = os.getenv("LOGGING_DIR", os.getcwd())
    logging.config.fileConfig(config_path, defaults={"LOGGING_DIR": log_dir})
    return logging.getLogger(os.path.basename(file))
