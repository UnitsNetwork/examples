import sys
from logging import Logger
from time import sleep
from typing_extensions import deprecated

from pywaves import pw


def force_success(log: Logger, r, error_text: str, wait=True, pw=pw):
    if not r or r == "ERROR" or "error" in r:
        log.error(f"{error_text}: {r}")
        sys.exit(1)

    if wait:
        id = r["id"]
        wait_for_approval(log, id, pw)
        log.info(f"{id} confirmed")


@deprecated("Use wait_for_approval instead")
def wait_for(id, pw=pw, log=None):
    if id == "ERROR":
        if log:
            log.error("Transaction failed, can't continue")
        else:
            print("Transaction failed, can't continue")
        sys.exit(1)

    while True:
        tx = pw.tx(id)
        if "id" in tx:
            return tx
        sleep(2)


def wait_for_approval(log: Logger, id, pw=pw):
    if id == "ERROR":
        log.error("Transaction failed, can't continue")
        sys.exit(1)

    while True:
        tx = pw.tx(id)
        if "id" in tx:
            return tx
        sleep(2)
