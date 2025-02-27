import logging
from dataclasses import dataclass
from time import sleep
from typing import List, Optional
from urllib.parse import quote

import pywaves as pw
from eth_typing import BlockNumber, ChecksumAddress
from hexbytes import HexBytes
from pywaves.address import TxSigner
from pywaves.txGenerator import TxGenerator
from web3 import Web3

import units_network.exceptions
from units_network import common_utils
from units_network.extended_address import ExtendedAddress
from units_network.extended_oracle import ExtendedOracle

SEP = ","


@dataclass
class ContractBlock:
    hash: HexBytes
    chain_height: BlockNumber
    epoch_number: int

    def __repr__(self) -> str:
        return f"ContractBlock({self.hash.to_0x_hex()}, h={self.chain_height}, e={self.epoch_number})"

    @classmethod
    def from_meta(cls, hash: HexBytes, meta: dict) -> "ContractBlock":
        return cls(
            hash=hash,
            chain_height=BlockNumber(meta["_1"]["value"]),
            epoch_number=meta["_2"]["value"],
        )


@dataclass
class RegisteredAsset:
    index: int
    cl_asset: pw.Asset
    el_erc20_address: ChecksumAddress
    ratio_exponent: int


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

    def getNativeToken(self) -> pw.Asset:
        r: str = self.getData("tokenId")
        return pw.Asset(r)  # type: ignore

    def getElNativeBridgeAddress(self) -> ChecksumAddress:
        return Web3.to_checksum_address(self.getData("elBridgeAddress"))

    def getElStandardBridgeAddress(self) -> ChecksumAddress:
        return Web3.to_checksum_address(self.getData("elStandardBridgeAddress"))

    def getRegisteredAssets(self) -> List[pw.Asset]:
        xs = self.getData(regex=quote("^assetRegistryIndex_.+$"))
        return [pw.Asset(x["value"]) for x in xs]

    def getRegisteredAssetSettings(self, asset: pw.Asset) -> Optional[RegisteredAsset]:
        xs = self.getData(regex=quote(f"^assetRegistry_{asset.assetId}$"))
        n = len(xs)
        if n == 0:
            return None
        elif n != 1:
            raise Exception(f"Found multiple asset entries for {asset.assetId}")

        x = xs[0]
        parts = x.split(SEP)
        if len(parts) < 3:
            raise Exception(f"Invalid data format in registry for {asset.assetId}: {x}")

        return RegisteredAsset(
            index=int(parts[0]),
            cl_asset=asset,
            el_erc20_address=Web3.to_checksum_address(parts[1]),
            ratio_exponent=int(parts[2]),
        )

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
        self, block_hash: HexBytes, timeout: float = 30, poll_latency: float = 2
    ) -> ContractBlock:
        self.log.debug(f"Wait for {block_hash.to_0x_hex()} on chain contract")
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
        hash = HexBytes(Web3.to_bytes(hexstr=self.getData("finalizedBlock")))
        return self.getBlockMeta(hash)

    def getBlockMeta(self, block_hash: HexBytes) -> ContractBlock:
        r = self.evaluate(f'blockMeta("{block_hash.hex()}")')
        try:
            meta = r["result"]["value"]
            return ContractBlock.from_meta(block_hash, meta)
        except Exception:
            raise units_network.exceptions.BlockNotFound(block_hash)

    def setScript(self, script: str, txFee: int = 5_000_000):
        return self.oracleAcc.setScript(script, txFee)

    def setup(
        self,
        elGenesisBlockHash: HexBytes,
        minerRewardInTokens: float = 1.8,
        daoAddress: str = "",
        daoRewardInTokens: float = 0.2,
        txFee: int = 100_500_000,
    ):
        minerRewardInWei = int(minerRewardInTokens * 10**18)
        minerRewardInGwei = Web3.from_wei(minerRewardInWei, "gwei")
        return self.oracleAcc.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="setup",
            params=[
                {
                    "type": "string",
                    "value": elGenesisBlockHash.hex(),
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
        elRewardAddress: ChecksumAddress,
        txFee: int = 500_000,
    ):
        return miner.invokeScript(
            dappAddress=self.oracleAddress,
            functionName="join",
            params=[
                {
                    "type": "string",
                    "value": elRewardAddress.lower(),
                },
            ],
            txFee=txFee,
        )

    def registerAsset(
        self,
        sender: pw.Address,
        asset: pw.Asset,
        erc20Address: ChecksumAddress,
        elDecimals: int,
        txFee: int = 500_000,
    ):
        return self.registerAssets(
            sender, [asset], [erc20Address], [elDecimals], txFee=txFee
        )

    def registerAssets(
        self,
        sender: pw.Address,
        assets: List[pw.Asset],
        erc20Addresses: List[ChecksumAddress],
        elDecimals: List[int],
        txFee: int = 500_000,
    ):
        txn = self.prepareRegisterAssets(
            sender, assets, erc20Addresses, elDecimals, txFee
        )
        return sender.broadcastTx(txn)

    def prepareRegisterAssets(
        self,
        sender: pw.Address,
        assets: List[pw.Asset],
        erc20Addresses: List[ChecksumAddress],
        elDecimals: List[int],
        txFee: int = 500_000,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore
        params = [
            {
                "type": "list",
                "value": [
                    {"type": "string", "value": asset.assetId} for asset in assets
                ],
            },
            {
                "type": "list",
                "value": [
                    {
                        "type": "string",
                        "value": erc20Address.lower(),
                    }
                    for erc20Address in erc20Addresses
                ],
            },
            {
                "type": "list",
                "value": [{"type": "integer", "value": x} for x in elDecimals],
            },
        ]
        txn = generator.generateInvokeScript(
            publicKey=sender.publicKey,
            dappAddress=self.oracleAddress,
            functionName="registerAssets",
            params=params,
            txFee=txFee,
        )
        signer.signTx(txn, privateKey=sender.privateKey)
        return txn

    def issueAndRegister(
        self,
        sender: pw.Address,
        erc20Address: ChecksumAddress,
        elDecimals: int,
        name: str,
        description: str,
        clDecimals: int,
        txFee: int = 100_500_000,
    ):
        txn = self.prepareIssueAndRegister(
            sender, erc20Address, elDecimals, name, description, clDecimals, txFee
        )
        return sender.broadcastTx(txn)

    def prepareIssueAndRegister(
        self,
        sender: pw.Address,
        erc20Address: ChecksumAddress,
        elDecimals: int,
        name: str,
        description: str,
        clDecimals: int,
        txFee: int = 100_500_000,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore
        params = [
            {
                "type": "string",
                "value": erc20Address.lower(),
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
        ]
        txn = generator.generateInvokeScript(
            publicKey=sender.publicKey,
            dappAddress=self.oracleAddress,
            functionName="issueAndRegister",
            params=params,
            txFee=txFee,
        )
        signer.signTx(txn, privateKey=sender.privateKey)
        return txn

    def transfer(
        self,
        fromWavesAccount: pw.Address,
        toEthAddress: ChecksumAddress,
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
                    "value": toEthAddress.lower(),
                }
            ],
            payments=[{"amount": atomicAmount, "assetId": token.assetId}],
            txFee=txFee,
        )

    def withdraw(
        self,
        sender: pw.Address,
        blockHashWithTransfer: HexBytes,
        merkleProofs: List[HexBytes],
        transferIndexInBlock: int,
        clAmount: int,
        txFee: int = 500_000,
    ):
        txn = self.prepareWithdraw(
            sender,
            blockHashWithTransfer,
            merkleProofs,
            transferIndexInBlock,
            clAmount,
            txFee,
        )
        return sender.broadcastTx(txn)

    def prepareWithdraw(
        self,
        sender: pw.Address,
        blockHashWithTransfer: HexBytes,
        merkleProofs: List[HexBytes],
        transferIndexInBlock: int,
        clAmount: int,
        txFee: int = 500_000,
    ):
        generator = TxGenerator(self.pw)  # type: ignore
        signer = TxSigner(self.pw)  # type: ignore

        proofs = [
            {"type": "binary", "value": f"base64:{common_utils.hex_to_base64(p)}"}
            for p in merkleProofs
        ]
        withdraw_amount = clAmount // (10**10)
        params = [
            {"type": "string", "value": blockHashWithTransfer.hex()},
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
        blockHashWithTransfer: HexBytes,
        merkleProofs: List[HexBytes],
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
        blockHashWithTransfer: HexBytes,
        merkleProofs: List[HexBytes],
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
            {"type": "string", "value": blockHashWithTransfer.hex()},
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
