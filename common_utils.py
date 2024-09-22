import logging
import sys
import time
import base64


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


def configure_script_logger(name: str) -> logging.Logger:
    # Remove a handler from PyWaves
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )

    return logging.getLogger(name)
