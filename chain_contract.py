from typing import List, Optional
import pywaves as pw
import requests
import common_utils
import logging


class ContractBlock(object):
    def __init__(self, hash, meta):
        self.hash = hash
        self.chain_height = meta["_1"]["value"]
        self.epoch_number = meta["_2"]["value"]

    def __repr__(self) -> str:
        return (
            f"ContractBlock({self.hash}, h={self.chain_height}, e={self.epoch_number})"
        )


class ExtendedOracle(pw.Oracle):
    def evaluate(self, query):
        url = f"{self.pw.NODE}/utils/script/evaluate/{self.oracleAddress}"
        headers = {"Content-Type": "application/json"}
        data = {"expr": query}

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error: {response.status_code}, {response.text}")


class ChainContract(ExtendedOracle):
    def __init__(self, oracleAddress=None, seed=None, pywaves=pw):
        super().__init__(oracleAddress, seed, pywaves)  # type: ignore
        self.log = logging.getLogger(self.__class__.__name__)

    def getToken(self) -> pw.Asset:
        r: str = self.getData("tokenId")
        return pw.Asset(r)  # type: ignore

    def getElBridgeAddress(self) -> str:
        return self.getData("elBridgeAddress")

    def waitForFinalized(self, block: ContractBlock):
        last_finalized_block: List[Optional[ContractBlock]] = [None]

        def is_finalized():
            finalized_block_str = "Same"
            curr_finalized_block = self.getFinalizedBlock()
            if not (
                last_finalized_block[0]
                and last_finalized_block[0].hash == curr_finalized_block.hash
            ):
                last_finalized_block[0] = curr_finalized_block
                finalized_block_str = f"{curr_finalized_block}"
            self.log.info(f"Current finalized block: {finalized_block_str}")
            return curr_finalized_block.chain_height >= block.chain_height

        common_utils.repeat(is_finalized, 5000)

    def waitForBlock(self, block_hash: str) -> ContractBlock:
        if block_hash.startswith("0x"):
            block_hash = block_hash[2:]

        def get_block_data():
            try:
                r = self.getBlockMeta(block_hash)
                return r
            except Exception:
                return None

        return common_utils.repeat(get_block_data, 2000)

    def getFinalizedBlock(self) -> ContractBlock:
        hash = self.getData("finalizedBlock")
        return self.getBlockMeta(hash)

    def getBlockMeta(self, hash: str) -> ContractBlock:
        r = self.evaluate(f'blockMeta("{hash}")')
        meta = r["result"]["value"]
        return ContractBlock(hash, meta)
