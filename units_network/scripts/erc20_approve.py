#!/usr/bin/env python
import sys
from decimal import Decimal

import pywaves as pw
from web3 import Web3
from web3.types import TxReceipt, Wei

from units_network import common_utils, networks, units


def main():
    log = common_utils.configure_cli_logger(__file__)

    el_account_private_key = common_utils.get_argument_value("--eth-private-key")
    chain_id_str = common_utils.get_argument_value("--chain-id") or "S"
    chain_settings_file = common_utils.get_argument_value("--chain-settings")
    asset_id = common_utils.get_argument_value("--asset-id")
    user_amount = Decimal(common_utils.get_argument_value("--amount") or "0.01")

    if not (
        el_account_private_key and el_account_private_key.startswith("0x") and asset_id
    ):
        print(
            """Approves token movements from Execution Layer (Ethereum) to Consensus Layer (Waves).
Usage:
  erc20_approve.py --eth-private-key <Ethereum private key in HEX with 0x> --asset-id <Waves asset id in Base58>
Required arguments:
  --asset-id <Waves asset id in Base58>: the matching ERC20 address will be found in the chain contract registry
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet. W - MainNet
  --chain-settings <path/to/chain/settings.json> (default: empty):
     if specified - use network settings from the file instead of based on --chain-id
  --amount N (default: 0.01): amount of transferred Unit0 tokens""",
            file=sys.stderr,
        )
        exit(1)

    network_settings = (
        networks.read_network_settings(chain_settings_file)
        if chain_settings_file
        else networks.get_network_settings(chain_id_str)
    )
    network = networks.create_manual(network_settings)

    asset = pw.Asset(asset_id)
    registered_asset = network.cl_chain_contract.getRegisteredAssetSettings(asset)
    if not registered_asset:
        raise Exception(f"{asset_id} is not a registered in the chain contract")

    erc20 = network.get_erc20(registered_asset.el_erc20_address)
    el_atomic_amount = Wei(units.user_to_atomic(user_amount, erc20.decimals))
    log.info(
        f"Approving a transfer of {user_amount} (in atomic units: {el_atomic_amount}) assets '{erc20.name}' at {registered_asset.el_erc20_address}"
    )

    el_account = network.w3.eth.account.from_key(el_account_private_key)
    approve_txn_hash = erc20.approve(
        network.bridges.standard_bridge.contract_address, el_atomic_amount, el_account
    )
    approve_receipt: TxReceipt = network.w3.eth.wait_for_transaction_receipt(
        approve_txn_hash,
    )
    log.info(f"ERC20.approve receipt: {Web3.to_json(approve_receipt)}")  # type: ignore
    log.info("Done")


if __name__ == "__main__":
    main()
