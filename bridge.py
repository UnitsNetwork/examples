import json
import logging
from typing import List, TypedDict

from eth_account.signers.base import BaseAccount
from eth_account.types import TransactionDictType
from eth_typing import HexStr
from eth_utils.abi import event_abi_to_log_topic
from hexbytes import HexBytes
from web3 import Web3
from web3.types import FilterParams, Nonce, TxParams, Wei

from merkle import get_merkle_proofs


class E2CTransferParams(TypedDict):
    block_with_transfer_hash: HexBytes
    merkle_proofs: List[str]
    transfer_index_in_block: int


class Bridge(object):
    def __init__(self, w3: Web3, el_bridge_address: str):
        self.log = logging.getLogger(__class__.__name__)
        self.w3 = w3
        self.address = Web3.to_checksum_address(el_bridge_address)

        with open("bridge-abi.json") as f:
            el_bridge_abi = json.load(f)

        self.contract = self.w3.eth.contract(
            address=self.address,
            abi=el_bridge_abi,
        )

        self.topic = HexStr(
            event_abi_to_log_topic(self.contract.events.SentNative().abi).hex()
        )

    def sendNative(
        self,
        from_eth_account: BaseAccount,
        to_waves_pk_hash: bytes,
        amount: Wei,
        gas_price: Wei = Wei(-1),
        nonce: Nonce = Nonce(-1),
    ) -> HexBytes:
        gas_price = self.w3.eth.gas_price if gas_price < 0 else gas_price
        nonce = (
            self.w3.eth.get_transaction_count(from_eth_account.address)
            if (nonce < 0)
            else nonce
        )
        txn: TxParams = {
            "from": from_eth_account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "value": amount,
        }
        send_native_call = self.contract.functions.sendNative(to_waves_pk_hash)
        gas = send_native_call.estimate_gas(txn)
        txn.update(
            {
                "to": self.contract.address,
                "gas": gas,
                "data": send_native_call._encode_transaction_data(),
            }
        )
        signed_tx = from_eth_account.sign_transaction(txn)
        self.log.debug(f"Signed sendNative transaction: {Web3.to_json(signed_tx)}")
        return self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    def getTransferProofs(
        self, block_hash: HexBytes, transfer_txn_hash: HexBytes
    ) -> E2CTransferParams:
        block_hash_hex = block_hash.hex()
        block_logs = self.w3.eth.get_logs(
            FilterParams(
                blockHash=block_hash,
                address=self.address,
                topics=[self.topic],
            )
        )

        self.log.debug(
            f"Bridge logs in block 0x{block_hash_hex} by topic '0x{self.topic}': {Web3.to_json(block_logs)}"  # type: ignore
        )

        merkle_leaves = []
        transfer_index_in_block = -1
        for i, x in enumerate(block_logs):
            merkle_leaves.append(x["data"].hex())
            if x["transactionHash"] == transfer_txn_hash:
                transfer_index_in_block = i

        return {
            "block_with_transfer_hash": block_hash,
            "merkle_proofs": get_merkle_proofs(merkle_leaves, transfer_index_in_block),
            "transfer_index_in_block": transfer_index_in_block,
        }
