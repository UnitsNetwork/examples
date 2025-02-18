import logging
from time import sleep
from typing import List, Optional

import pywaves as pw
from eth_typing import HexAddress, HexStr
from pywaves.address import TxSigner
from pywaves.txGenerator import TxGenerator
from web3 import Web3
from web3.types import Wei

import units_network.exceptions
from units_network import common_utils
from units_network.extended_address import ExtendedAddress
from units_network.extended_oracle import ExtendedOracle


class ContractBlock(object):
    def __init__(self, hash, meta):
        self.hash = hash
        self.chain_height = meta["_1"]["value"]
        self.epoch_number = meta["_2"]["value"]

    def __repr__(self) -> str:
        return (
            f"ContractBlock({self.hash}, h={self.chain_height}, e={self.epoch_number})"
        )


class ChainContract(ExtendedOracle):
    def __init__(self, oracleAddress=None, seed=None, nonce=0, pywaves=pw):
        # super().__init__(oracleAddress, seed, pywaves)  # Doesn't propagate nonce
        self.pw = pywaves
        if seed is None:
            self.oracleAddress = oracleAddress
        else:
            self.oracleAcc = ExtendedAddress(seed=seed, nonce=nonce)
            self.oracleAddress = self.oracleAcc.address
        self.log = logging.getLogger(self.__class__.__name__)

    def isContractSetup(self) -> bool:
        r = self.evaluate("isContractSetup()")
        return r and r["result"] and r["result"]["value"]

    def getToken(self) -> pw.Asset:
        r: str = self.getData("tokenId")
        return pw.Asset(r)  # type: ignore

    def getElBridgeAddress(self) -> str:
        return self.getData("elBridgeAddress")

    def getElStandardBridgeAddress(self) -> str:
        return self.getData("elStandardBridgeAddress")

    def waitForFinalized(
        self, block: ContractBlock, timeout: float = 30, poll_latency: float = 2
    ):
        last_finalized_block: List[Optional[ContractBlock]] = [None]

        rest_timeout = timeout
        while True:
            curr_finalized_block = self.getFinalizedBlock()
            message = f"Wait for {block.chain_height - curr_finalized_block.chain_height} blocks to finalize"
            if not (
                last_finalized_block[0]
                and last_finalized_block[0].hash == curr_finalized_block.hash
            ):
                last_finalized_block[0] = curr_finalized_block
                message = f"Current finalized block is {curr_finalized_block}"
            self.log.debug(message)
            if curr_finalized_block.chain_height >= block.chain_height:
                return

            rest_timeout -= poll_latency
            if rest_timeout <= 0:
                break

            sleep(poll_latency)
        raise units_network.exceptions.TimeExhausted(
            f"Block {block.hash} not finalized on contract in {timeout} seconds"
        )

    def waitForBlock(
        self, block_hash: str, timeout: float = 30, poll_latency: float = 2
    ) -> ContractBlock:
        self.log.debug(f"Wait for {block_hash} on chain contract")
        rest_timeout = timeout
        while True:
            try:
                return self.getBlockMeta(block_hash)
            except units_network.exceptions.BlockNotFound:
                pass

            rest_timeout -= poll_latency
            if rest_timeout <= 0:
                break

            sleep(poll_latency)
        raise units_network.exceptions.TimeExhausted(
            f"Block {block_hash} not found on contract in {timeout} seconds"
        )

    def getFinalizedBlock(self) -> ContractBlock:
        hash = self.getData("finalizedBlock")
        return self.getBlockMeta(hash)

    def getBlockMeta(self, hash: str) -> ContractBlock:
        if hash.startswith("0x"):
            hash = hash[2:]

        r = self.evaluate(f'blockMeta("{hash}")')
        try:
            meta = r["result"]["value"]
            return ContractBlock(hash, meta)
        except Exception:
            raise units_network.exceptions.BlockNotFound(hash)

    def setScript(self, script: str, txFee: int = 3_500_000):
        return self.oracleAcc.setScript(script, txFee)

    def setup(
        self,
        elGenesisBlockHash: HexStr,
        minerRewardInTokens: float = 1.8,
        txFee: int = 100_500_000,
        daoAddress: str = "",
        daoRewardInTokens: float = 0.2,
    ):
        minerRewardInWei = int(minerRewardInTokens * 10**18)
        minerRewardInGwei = Web3.from_wei(minerRewardInWei, "gwei")
        return self.oracleAcc.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="setup",
            params=[
                {
                    "type": "string",
                    "value": common_utils.clean_hex_prefix(elGenesisBlockHash),
                },
                {
                    "type": "integer",
                    "value": int(minerRewardInGwei),
                },
                {"type": "string", "value": daoAddress},
                {"type": "integer", "value": int(daoRewardInTokens * 10**8)},
            ],
            txFee=txFee,
        )

    def join(
        self,
        miner: pw.Address,
        elRewardAddress: HexStr,
        txFee: int = 500_000,
    ):
        return miner.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="join",
            params=[
                {
                    "type": "binary",
                    "value": f"base64:{common_utils.hex_to_base64(common_utils.clean_hex_prefix(elRewardAddress))}",
                },
            ],
            txFee=txFee,
        )

    def join_v2(
        self,
        miner: pw.Address,
        elRewardAddress: HexStr,
        txFee: int = 500_000,
    ):
        # Reward address in string
        return miner.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="join",
            params=[
                {
                    "type": "string",
                    "value": elRewardAddress,
                },
            ],
            txFee=txFee,
        )

    def registerAsset(
        self,
        asset: pw.Asset,
        erc20Address: HexStr,
        elDecimals: int,
        txFee: int = 500_000,
    ):
        return self.oracleAcc.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="registerAsset",
            params=[
                {
                    "type": "string",
                    "value": asset.assetId,
                },
                {
                    "type": "string",
                    "value": common_utils.clean_hex_prefix(erc20Address).lower(),
                },
                {"type": "integer", "value": elDecimals},
            ],
            txFee=txFee,
        )

    def createAndRegisterAsset(
        self,
        erc20Address: HexStr,
        elDecimals: int,
        name: str,
        description: str,
        clDecimals: int,
        txFee: int = 500_000,
    ):
        return self.oracleAcc.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="createAndRegisterAsset",
            params=[
                {
                    "type": "string",
                    "value": common_utils.clean_hex_prefix(erc20Address).lower(),
                },
                {"type": "integer", "value": elDecimals},
                {
                    "type": "string",
                    "value": name,
                },
                {
                    "type": "string",
                    "value": description,
                },
                {"type": "integer", "value": clDecimals},
            ],
            txFee=txFee,
        )

    def transfer(
        self,
        fromWavesAccount: pw.Address,
        toEthAddress: HexAddress,
        token: pw.Asset,
        atomicAmount: int,
        txFee: int = 500_000,
    ):
        return fromWavesAccount.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="transfer",
            params=[
                {
                    "type": "string",
                    "value": common_utils.clean_hex_prefix(toEthAddress).lower(),
                }
            ],
            payments=[{"amount": atomicAmount, "assetId": token.assetId}],
            txFee=txFee,
        )

    def withdraw(
        self,
        sender: pw.Address,
        blockHashWithTransfer: str,
        merkleProofs: List[str],
        transferIndexInBlock: int,
        amount: Wei,
        txFee: int = 500_000,
    ):
        txn = self.prepareWithdraw(
            sender,
            blockHashWithTransfer,
            merkleProofs,
            transferIndexInBlock,
            amount,
            txFee,
        )
        return sender.broadcastTx(txn)

    def prepareWithdraw(
        self,
        sender: pw.Address,
        blockHashWithTransfer: str,
        merkleProofs: List[str],
        transferIndexInBlock: int,
        amount: Wei,
        txFee: int = 500_000,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore

        proofs = [
            {"type": "binary", "value": f"base64:{common_utils.hex_to_base64(p)}"}
            for p in merkleProofs
        ]
        withdraw_amount = amount // (10**10)
        params = [
            {"type": "string", "value": blockHashWithTransfer},
            {"type": "list", "value": proofs},
            {"type": "integer", "value": transferIndexInBlock},
            {"type": "integer", "value": withdraw_amount},
        ]
        txn = generator.generateInvokeScript(
            publicKey=sender.publicKey,
            dappAddress=self.oracleAddress,
            functionName="withdraw",
            params=params,
            txFee=txFee,
        )
        signer.signTx(txn, privateKey=sender.privateKey)
        return txn

    def withdrawAsset(
        self,
        sender: pw.Address,
        blockHashWithTransfer: str,
        merkleProofs: List[str],
        transferIndexInBlock: int,
        atomicAmount: int,
        asset: pw.Asset,
        txFee: int = 500_000,
    ):
        txn = self.prepareWithdrawAsset(
            sender,
            blockHashWithTransfer,
            merkleProofs,
            transferIndexInBlock,
            atomicAmount,
            asset,
            txFee,
        )
        return sender.broadcastTx(txn)

    def prepareWithdrawAsset(
        self,
        sender: pw.Address,
        blockHashWithTransfer: str,
        merkleProofs: List[str],
        transferIndexInBlock: int,
        atomicAmount: int,
        asset: pw.Asset,
        txFee: int = 500_000,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore

        proofs = [
            {"type": "binary", "value": f"base64:{common_utils.hex_to_base64(p)}"}
            for p in merkleProofs
        ]
        params = [
            {"type": "string", "value": blockHashWithTransfer},
            {"type": "list", "value": proofs},
            {"type": "integer", "value": transferIndexInBlock},
            {"type": "integer", "value": atomicAmount},
            {"type": "string", "value": asset.assetId},
        ]
        txn = generator.generateInvokeScript(
            publicKey=sender.publicKey,
            dappAddress=self.oracleAddress,
            functionName="withdrawAsset",
            params=params,
            txFee=txFee,
        )
        signer.signTx(txn, privateKey=sender.privateKey)
        return txn
