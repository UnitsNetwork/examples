#!/usr/bin/env python
import sys
from decimal import Decimal

import pywaves as pw
from web3.types import Wei

from units_network import common_utils, networks, units


def main():
    log = common_utils.configure_cli_logger(__file__)

    cl_account_private_key = common_utils.get_argument_value("--waves-private-key")
    el_account_private_key = common_utils.get_argument_value("--eth-private-key")
    chain_id_str = common_utils.get_argument_value("--chain-id") or "S"
    chain_settings_file = common_utils.get_argument_value("--chain-settings")
    asset_id = common_utils.get_argument_value("--asset-id")
    user_amount = Decimal(common_utils.get_argument_value("--amount") or "0.01")

    if not (
        cl_account_private_key
        and el_account_private_key
        and el_account_private_key.startswith("0x")
        and user_amount > 0
    ):
        print(
            """Transfer assets from Consensus Layer (Waves) to Execution Layer (Ethereum).
Usage:
  transfer-c2e.py --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet, W - MainNet 
  --chain-settings <path/to/chain/settings.json> (default: empty):
     if specified - use network settings from the file instead of based on --chain-id
  --asset-id <Waves asset id in Base58> (default: Unit0 of selected network)
  --amount N (default: 0.01): amount of transferred assets""",
            file=sys.stderr,
        )
        sys.exit(1)

    network_settings = (
        networks.read_network_settings(chain_settings_file)
        if chain_settings_file
        else networks.get_network_settings(chain_id_str)
    )
    network = networks.create_manual(network_settings)

    cl_account = pw.Address(privateKey=cl_account_private_key)
    el_account = network.w3.eth.account.from_key(el_account_private_key)

    native_token = network.cl_chain_contract.getNativeToken()
    registered_asset = None
    if asset_id == native_token.assetId or not asset_id:
        asset = native_token
    else:
        asset = pw.Asset(asset_id)
        registered_asset = network.cl_chain_contract.getRegisteredAssetSettings(asset)
        if not registered_asset:
            raise Exception(
                f"{asset_id} is neither a native token {native_token.assetId}, nor a registered asset"
            )

    log.info(
        f"[C] Selected asset '{asset.name}' with id {asset.assetId} and {asset.decimals} decimals"
    )

    if registered_asset:
        el_decimals = network.bridges.standard_bridge.token_ratio(
            registered_asset.el_erc20_address
        )
        log.info(
            f"[C] Registered asset ERC20 address: {registered_asset.el_erc20_address}, decimals: {el_decimals}"
        )
    else:
        el_decimals = units.UNIT0_EL_DECIMALS

    cl_atomic_amount = units.user_to_atomic(user_amount, asset.decimals)
    el_atomic_amount = Wei(units.user_to_atomic(user_amount, el_decimals))
    log.info(
        f"Sending {user_amount} assets from {cl_account.address} (C) to {el_account.address} (E)"
    )
    log.debug(f"C atomic units: {cl_atomic_amount}, E atomic units: {el_atomic_amount}")

    transfer_result = network.cl_chain_contract.transfer(
        cl_account, el_account.address, asset, cl_atomic_amount
    )

    log.info(f"[C] ChainContract.transfer result: {transfer_result}")
    log.info("Done")


if __name__ == "__main__":
    main()
