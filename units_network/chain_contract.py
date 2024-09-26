import logging
from typing import List, Optional

import pywaves as pw
import requests
from eth_typing import HexAddress
from pywaves.address import TxSigner
from pywaves.txGenerator import TxGenerator
from web3.types import Wei

from units_network import common_utils


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

    def isContractSetup(self) -> bool:
        r = self.evaluate("isContractSetup()")
        return r and r["result"] and r["result"]["value"]

    def getToken(self) -> pw.Asset:
        r: str = self.getData("tokenId")
        return pw.Asset(r)  # type: ignore

    def getElBridgeAddress(self) -> str:
        return self.getData("elBridgeAddress")

    def waitForFinalized(self, block: ContractBlock):
        last_finalized_block: List[Optional[ContractBlock]] = [None]

        def is_finalized():
            curr_finalized_block = self.getFinalizedBlock()
            message = f"Waiting for {block.chain_height - curr_finalized_block.chain_height} blocks to finalize"
            if not (
                last_finalized_block[0]
                and last_finalized_block[0].hash == curr_finalized_block.hash
            ):
                last_finalized_block[0] = curr_finalized_block
                message = f"{curr_finalized_block} finalized"
            self.log.info(message)
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

    def transfer(
        self,
        from_waves_account: pw.Address,
        to_eth_address: HexAddress,
        token: pw.Asset,
        atomic_amount: int,
    ):
        return from_waves_account.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="transfer",
            params=[
                {
                    "type": "string",
                    "value": to_eth_address.lower()[2:],  # Remove '0x' prefix
                }
            ],
            payments=[{"amount": atomic_amount, "assetId": token.assetId}],
            txFee=500_000,
        )

    def withdraw(
        self,
        sender: pw.Address,
        block_hash_with_transfer: str,
        merkle_proofs: List[str],
        transfer_index_in_block: int,
        amount: Wei,
    ):
        txn = self.prepareWithdraw(
            sender,
            block_hash_with_transfer,
            merkle_proofs,
            transfer_index_in_block,
            amount,
        )
        return sender.broadcastTx(txn)

    def prepareWithdraw(
        self,
        sender: pw.Address,
        block_hash_with_transfer: str,
        merkle_proofs: List[str],
        transfer_index_in_block: int,
        amount: Wei,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore

        proofs = [
            {"type": "binary", "value": f"base64:{common_utils.hex_to_base64(p)}"}
            for p in merkle_proofs
        ]
        withdraw_amount = amount // (10**10)
        params = [
            {"type": "string", "value": block_hash_with_transfer},
            {"type": "list", "value": proofs},
            {"type": "integer", "value": transfer_index_in_block},
            {"type": "integer", "value": withdraw_amount},
        ]
        txn = generator.generateInvokeScript(
            publicKey=sender.publicKey,
            dappAddress=self.oracleAddress,
            functionName="withdraw",
            params=params,
            txFee=500_000,
        )
        signer.signTx(txn, privateKey=sender.privateKey)
        return txn
