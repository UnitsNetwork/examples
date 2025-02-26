import json
from dataclasses import dataclass
from functools import cached_property
from importlib.resources import files

import pywaves as pw
from eth_account.signers.base import BaseAccount
from eth_typing import ChecksumAddress, HexStr
from eth_utils.abi import event_abi_to_log_topic
from hexbytes import HexBytes
from web3 import Web3
from web3.types import LogReceipt, Nonce, Wei

from units_network import common_utils
from units_network.base_contract import BaseContract


class NativeBridge(BaseContract):
    def __init__(self, w3: Web3, contract_address: ChecksumAddress):
        json_abi = files("units_network").joinpath("abi/NativeBridge.json").read_text()
        abi = json.loads(json_abi)
        super().__init__(w3, contract_address, abi)

    def send_native(
        self,
        cl_to: pw.Address,
        el_amount: Wei,
        sender_account: BaseAccount,
        gas_price: Wei = Wei(-1),
        nonce: Nonce = Nonce(-1),
    ) -> HexStr:
        return self.send_transaction(
            "sendNative",
            [common_utils.waves_public_key_hash_bytes(cl_to.address)],
            sender_account,
            el_amount,
            gas_price,
            nonce,
        )

    @cached_property
    def sent_native_topic(self) -> HexStr:
        return HexStr(
            "0x" + event_abi_to_log_topic(self.contract.events.SentNative().abi).hex()
        )

    def parse_sent_native(self, log: LogReceipt):
        args = self.contract.events.SentNative().process_log(log)["args"]
        return SentNative(
            waves_recipient=args["wavesRecipient"],
            amount=args["amount"],
            data=log["data"],
        )


@dataclass
class SentNative:
    waves_recipient: HexBytes
    amount: int
    data: HexBytes

    def to_merkle_leaf(self) -> bytes:
        return self.data
