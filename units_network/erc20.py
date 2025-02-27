import json
from functools import cached_property
from importlib.resources import files

from eth_account.signers.base import BaseAccount
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.types import Wei

from units_network.base_contract import BaseContract


class Erc20(BaseContract):
    def __init__(self, w3: Web3, contract_address: ChecksumAddress):
        json_abi = files("units_network").joinpath("abi/Erc20.json").read_text()
        abi = json.loads(json_abi)
        super().__init__(w3, contract_address, abi)

    @cached_property
    def name(self) -> int:
        return self.contract.functions.name().call()

    @cached_property
    def decimals(self) -> int:
        return self.contract.functions.decimals().call()

    def get_balance(self, address: ChecksumAddress) -> Wei:
        return self.contract.functions.balanceOf(address).call(
            block_identifier="pending"
        )

    def approve(
        self, spender_address: ChecksumAddress, amount: Wei, sender_account: BaseAccount
    ):
        return self.send_transaction(
            "approve",
            [spender_address, amount],
            sender_account,
        )

    def transfer(
        self, to_address: ChecksumAddress, amount: Wei, sender_account: BaseAccount
    ):
        return self.send_transaction("transfer", [to_address, amount], sender_account)
