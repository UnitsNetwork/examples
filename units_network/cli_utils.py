from dataclasses import dataclass
from typing import Optional

from pywaves import pw

from units_network import units
from units_network.erc20 import Erc20
from units_network.networks import Network


@dataclass()
class FoundAsset:
    waves_asset: pw.Asset
    el_decimals: int
    erc20: Optional[Erc20] = None

    def __post_init__(self):
        self.waves_asset_name = self.waves_asset.name.decode("ascii")


def find_asset(
    network: Network,
    waves_asset_id: Optional[str] = None,
    waves_asset_name: Optional[str] = None,
) -> FoundAsset:
    if not (waves_asset_id or waves_asset_name):
        raise Exception(
            "Either waves_asset_id or waves_asset_name required to find an asset"
        )

    native_token = network.cl_chain_contract.getNativeToken()
    if (
        waves_asset_id == native_token.assetId
        or waves_asset_name.lower() == native_token.name.decode("ascii").lower()
    ):
        return FoundAsset(native_token, units.UNIT0_EL_DECIMALS)

    if waves_asset_id:
        asset = pw.Asset(waves_asset_id)
    elif waves_asset_name:
        asset = network.cl_chain_contract.findRegisteredAsset(waves_asset_name)
    else:
        asset = None

    if not asset:
        raise Exception(
            f"{waves_asset_id}/{waves_asset_name} is not a registered in the chain contract"
        )

    registered_asset = network.cl_chain_contract.getRegisteredAssetSettings(asset)
    if not registered_asset:
        raise Exception(
            f"{waves_asset_id} is neither a native token {native_token.assetId}, nor a registered asset"
        )
    erc20 = network.get_erc20(registered_asset.el_erc20_address)
    return FoundAsset(asset, erc20.decimals, erc20)
