from eth_account.signers.base import BaseAccount
from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.types import Nonce, Wei


class BaseContract:
    def __init__(self, w3: Web3, contract_address: ChecksumAddress, abi):
        self.w3 = w3
        self.abi = abi
        self.contract_address = contract_address
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=self.abi
        )

    def send_transaction(
        self,
        function_name: str,
        args,
        sender_account: BaseAccount,
        el_amount: Wei = Wei(0),
        gas_price: Wei = Wei(-1),
        nonce: Nonce = Nonce(-1),
    ) -> HexStr:
        gas_price = self.w3.eth.gas_price if gas_price < 0 else gas_price
        nonce = (
            self.w3.eth.get_transaction_count(sender_account.address, "pending")
            if (nonce < 0)
            else nonce
        )

        attrs = {
            "chainId": self.w3.eth.chain_id,
            "from": sender_account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
        }
        if el_amount:
            attrs["value"] = el_amount

        tx = getattr(self.contract.functions, function_name)(*args).build_transaction(
            attrs
        )
        signed_tx = sender_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return self.w3.to_hex(tx_hash)
