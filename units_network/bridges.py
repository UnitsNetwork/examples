import logging
from dataclasses import dataclass
from typing import List, Optional, Union

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.types import FilterParams, LogReceipt

from units_network.merkle import get_merkle_proofs
from units_network.native_bridge import NativeBridge, SentNative
from units_network.standard_bridge import ERC20BridgeInitiatedEvent, StandardBridge


@dataclass()
class E2CTransferParams:
    block_with_transfer_hash: HexBytes
    merkle_proofs: List[HexBytes]
    transfer_index_in_block: int


class Bridges(object):
    def __init__(
        self,
        w3: Web3,
        el_native_bridge_address: ChecksumAddress,
        el_standard_bridge_address: ChecksumAddress,
    ):
        self.log = logging.getLogger(__class__.__name__)
        self.w3 = w3

        self.native_bridge = NativeBridge(w3, el_native_bridge_address)
        self.standard_bridge = StandardBridge(w3, el_standard_bridge_address)

        self.e2c_topics = [
            self.native_bridge.sent_native_topic,
            self.standard_bridge.erc20_bridge_initiated_topic,
        ]
        str_topics = ", ".join(self.e2c_topics)
        self.log.debug(f"Topics: {str_topics}")

    def get_e2c_transfer_params(
        self, block_hash: HexBytes, transfer_txn_hash: HexBytes
    ) -> E2CTransferParams:
        block_logs = self.get_e2c_block_logs(block_hash)
        self.log.debug(
            f"Bridge logs in block {block_hash.to_0x_hex()}: {Web3.to_json(block_logs)}"  # type: ignore
        )

        merkle_leaves = self.get_e2c_merkle_leaves(block_logs)
        transfer_index_in_block = -1
        for i, log in enumerate(block_logs):
            if log["transactionHash"] == transfer_txn_hash:
                self.log.debug(f"Found transfer transaction at #{i}")
                transfer_index_in_block = i

        return E2CTransferParams(
            block_with_transfer_hash=block_hash,
            merkle_proofs=get_merkle_proofs(merkle_leaves, transfer_index_in_block),
            transfer_index_in_block=transfer_index_in_block,
        )

    def get_e2c_block_logs(self, block_hash: HexBytes) -> List[LogReceipt]:
        return self.w3.eth.get_logs(
            FilterParams(
                blockHash=block_hash,
                address=[
                    self.native_bridge.contract_address,
                    self.standard_bridge.contract_address,
                ],
            )
        )

    def get_e2c_merkle_leaves(self, block_logs: List[LogReceipt]) -> List[HexBytes]:
        merkle_leaves: List[HexBytes] = []
        for i, log in enumerate(block_logs):
            evt = self.parse_e2c_event(log)
            if not evt:
                continue
            self.log.debug(f"Parsed event at #{i}: {evt}")
            merkle_leaves.append(evt.to_merkle_leaf())
        return merkle_leaves

    def parse_e2c_event(
        self, log: LogReceipt
    ) -> Optional[Union[SentNative, ERC20BridgeInitiatedEvent]]:
        topics = log["topics"]
        if len(topics) == 0:
            return None

        topic = HexStr(topics[0].to_0x_hex())
        if topic == self.native_bridge.sent_native_topic:
            return self.native_bridge.parse_sent_native(log)
        elif topic == self.standard_bridge.erc20_bridge_initiated_topic:
            return self.standard_bridge.parse_erc20_bridge_initiated(log)

        return None
