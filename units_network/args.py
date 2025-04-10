import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import Optional

from units_network import networks
from units_network.networks import NetworkSettings


@dataclass
class ArgsData:
    waves_private_key: Optional[str] = None
    eth_private_key: Optional[str] = None
    chain_id: Optional[str] = None
    network_settings: Optional[NetworkSettings] = None
    asset_id: Optional[str] = None
    asset_name: Optional[str] = None
    amount: Optional[Decimal] = None
    timeout: Optional[int] = None  # In seconds
    txn_hash: Optional[str] = None

    @staticmethod
    def from_json_file(file_path: str) -> "ArgsData":
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "network_settings" in data and isinstance(data["network_settings"], dict):
            data["network_settings"] = NetworkSettings(**data["network_settings"])

        if "amount" in data and data["amount"] is not None:
            data["amount"] = Decimal(data["amount"])

        return ArgsData(**data)


def get_argument_value(arg_name: str) -> Optional[str]:
    try:
        index = sys.argv.index(arg_name)
        if index != -1 and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    except ValueError:
        pass
    return None


class Args:
    def __init__(self):
        default_args_path = get_argument_value("--args")
        self.default = (
            ArgsData.from_json_file(default_args_path)
            if default_args_path
            else ArgsData()
        )

    @cached_property
    def waves_private_key(self) -> Optional[str]:
        return (
            get_argument_value("--waves-private-key") or self.default.waves_private_key
        )

    @cached_property
    def eth_private_key(self) -> Optional[str]:
        return get_argument_value("--eth-private-key") or self.default.eth_private_key

    @cached_property
    def chain_id(self) -> Optional[str]:
        return get_argument_value("--chain-id") or self.default.chain_id

    @cached_property
    def network_settings(self) -> NetworkSettings:
        r = (
            networks.get_predefined_network_settings(self.chain_id)
            if self.chain_id
            else self.default.network_settings
        )
        return r if r else networks.get_predefined_network_settings("S")

    @cached_property
    def asset_id(self) -> Optional[str]:
        return get_argument_value("--asset-id") or self.default.asset_id

    @cached_property
    def asset_name(self) -> Optional[str]:
        return get_argument_value("--asset-name") or self.default.asset_name

    @cached_property
    def amount(self) -> Decimal:
        from_args = get_argument_value("--amount")
        if from_args:
            from_args = Decimal(from_args)
        return from_args or self.default.amount or Decimal("0.01")

    # In seconds
    @cached_property
    def timeout(self) -> int:
        return int(get_argument_value("--timeout") or self.default.timeout or "180")

    @cached_property
    def txn_hash(self) -> Optional[str]:
        return get_argument_value("--txn-hash") or self.default.txn_hash
