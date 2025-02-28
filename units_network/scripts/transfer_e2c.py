#!/usr/bin/env python
import sys

import pywaves as pw
from web3 import Web3
from web3.types import TxReceipt, Wei

from units_network import common_utils, networks, units
from units_network.args import Args


def main():
    log = common_utils.configure_cli_logger(__file__)

    args = Args()
    if not (args.waves_private_key and args.eth_private_key and args.amount > 0):
        print(
            """Transfer native tokens from Execution Layer (Ethereum) to Consensus Layer (Waves).
Usage:
  transfer-e2c.py --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> 
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet. W - MainNet
  --asset-id <Waves asset id in Base58> (default: Unit0 of selected network)
  --amount N (default: 0.01): amount of transferred Unit0 tokens
  --args <path/to/args.json>: take default argument values from this file""",
            file=sys.stderr,
        )
        exit(1)

    network = networks.create_manual(args.network_settings)

    cl_account = pw.Address(privateKey=args.waves_private_key)
    el_account = network.w3.eth.account.from_key(args.eth_private_key)

    native_token = network.cl_chain_contract.getNativeToken()
    registered_asset = None
    if args.asset_id == native_token.assetId or not args.asset_id:
        asset = native_token
    else:
        asset = pw.Asset(args.asset_id)
        registered_asset = network.cl_chain_contract.getRegisteredAssetSettings(asset)
        if not registered_asset:
            raise Exception(
                f"{args.asset_id} is neither a native token {native_token.assetId}, nor a registered asset"
            )

    log.info(
        f"[C] Selected asset '{asset.name}' with id {asset.assetId} and {asset.decimals} decimals"
    )

    if registered_asset:
        erc20 = network.get_erc20(registered_asset.el_erc20_address)
        el_decimals = erc20.decimals
        log.info(
            f"[C] Registered asset ERC20 address: {registered_asset.el_erc20_address}, decimals: {el_decimals}"
        )
    else:
        el_decimals = units.UNIT0_EL_DECIMALS

    cl_atomic_amount = units.user_to_atomic(args.amount, asset.decimals)
    el_atomic_amount = Wei(units.user_to_atomic(args.amount, el_decimals))
    sending_str = f"Sending {args.amount} assets from {el_account.address} (E) to {cl_account.address} using "
    atomic_units_str = (
        f"in C atomic units: {cl_atomic_amount}, in E atomic units: {el_atomic_amount}"
    )

    if registered_asset:
        log.info(f"[E] {sending_str} StandardBridge.bridgeERC20. {atomic_units_str}")
        send_txn_hash = network.bridges.standard_bridge.bridge_erc20(
            token=registered_asset.el_erc20_address,
            cl_to=common_utils.waves_public_key_hash_bytes(cl_account),
            el_amount=el_atomic_amount,
            sender_account=el_account,
        )
    else:
        log.info(f"[E] {sending_str} NativeBridge. {atomic_units_str}")
        send_txn_hash = network.bridges.native_bridge.send_native(
            cl_to=cl_account,
            el_amount=el_atomic_amount,
            sender_account=el_account,
        )
    log.info(f"[E] Transaction hash: {send_txn_hash}")

    send_receipt: TxReceipt = network.w3.eth.wait_for_transaction_receipt(
        send_txn_hash,
    )
    log.info(f"[E] NativeBridge.sendNative receipt: {Web3.to_json(send_receipt)}")  # type: ignore

    transfer_params = network.bridges.get_e2c_transfer_params(
        send_receipt["blockHash"], send_receipt["transactionHash"]
    )
    log.info(f"[C] E2C transfer params: {transfer_params}")

    withdraw_contract_block = network.cl_chain_contract.waitForBlock(
        transfer_params.block_with_transfer_hash
    )
    log.info(
        f"[C] Found a block with transfer on chain contract: {withdraw_contract_block}"
    )

    network.cl_chain_contract.waitForFinalized(withdraw_contract_block)

    withdraw_result = network.cl_chain_contract.withdrawAsset(
        sender=cl_account,
        blockHashWithTransfer=transfer_params.block_with_transfer_hash,
        merkleProofs=transfer_params.merkle_proofs,
        transferIndexInBlock=transfer_params.transfer_index_in_block,
        atomicAmount=cl_atomic_amount,
        asset=asset,
    )
    log.info(f"[C] ChainContract.withdraw result: {withdraw_result}")
    log.info("Done")


if __name__ == "__main__":
    main()
