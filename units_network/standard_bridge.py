import json
from dataclasses import dataclass
from functools import cached_property
from importlib.resources import files

from eth_typing import ChecksumAddress, HexAddress, HexStr
from eth_utils.abi import event_abi_to_log_topic
from web3 import Web3
from web3.types import LogReceipt, Wei

from units_network.base_contract import BaseContract


class StandardBridge(BaseContract):
    def __init__(self, w3: Web3, contract_address: ChecksumAddress):
        json_abi = (
            files("units_network").joinpath("abi/StandardBridge.json").read_text()
        )
        abi = json.loads(json_abi)
        super().__init__(w3, contract_address, abi)

    def bridge_erc20(self, token, cl_to, el_amount: Wei, sender_account) -> HexStr:
        return self.send_transaction(
            "bridgeERC20",
            [Web3.to_checksum_address(token), cl_to, el_amount],
            sender_account,
        )

    def token_ratio(self, address):
        return self.contract.functions.tokenRatios(address).call()

    @cached_property
    def erc20_bridge_initiated_topic(self) -> HexStr:
        return HexStr(
            "0x"
            + event_abi_to_log_topic(
                self.contract.events.ERC20BridgeInitiated().abi
            ).hex()
        )

    def parse_erc20_bridge_initiated(self, log: LogReceipt):
        args = self.contract.events.ERC20BridgeInitiated().process_log(log)["args"]
        return ERC20BridgeInitiatedEvent(
            local_token=HexAddress(args["localToken"]),
            from_address=HexAddress(args["from"]),
            cl_to=HexAddress(args["clTo"]),
            cl_amount=args["clAmount"],
        )


@dataclass
class ERC20BridgeInitiatedEvent:
    local_token: HexAddress
    from_address: HexAddress
    cl_to: HexAddress
    cl_amount: int

    def to_merkle_leaf(self) -> bytes:
        local_token_bytes = bytes.fromhex(self.local_token[2:]).rjust(32, b"\x00")
        cl_to_bytes = bytes.fromhex(self.cl_to[2:]).rjust(32, b"\x00")
        cl_amount_bytes = self.cl_amount.to_bytes(
            8, byteorder="big", signed=False
        ).rjust(32, b"\x00")
        return local_token_bytes + cl_to_bytes + cl_amount_bytes

    def __repr__(self) -> str:
        return (
            f"ERC20BridgeInitiatedEvent(local_token={self.local_token}, "
            f"from_address={self.from_address}, cl_to={self.cl_to}, cl_amount={self.cl_amount})"
        )
