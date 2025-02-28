import logging
import os
from dataclasses import dataclass
from functools import cached_property

from ens.ens import ChecksumAddress
from pywaves import pw
from web3 import Web3

from units_network.bridges import Bridges
from units_network.chain_contract import ChainContract
from units_network.erc20 import Erc20


@dataclass
class NetworkSettings:
    name: str
    cl_chain_id_str: str
    cl_node_api_url: str
    el_node_api_url: str
    chain_contract_address: str

    def __post_init__(self):
        self.chain_id = ord(self.cl_chain_id_str)


# Creating instances for each network
stage_net = NetworkSettings(
    name="StageNet",
    cl_chain_id_str="S",
    cl_node_api_url="https://nodes-stagenet.wavesnodes.com",
    el_node_api_url="https://rpc-stagenet.unit0.dev",
    chain_contract_address="3MSYQZgB25kRqg9pAAbtgBmvNkx1B1AzdY1",
)

test_net = NetworkSettings(
    name="TestNet",
    cl_chain_id_str="T",
    cl_node_api_url="https://nodes-testnet.wavesnodes.com",
    el_node_api_url="https://rpc-testnet.unit0.dev",
    chain_contract_address="3Msx4Aq69zWUKy4d1wyKnQ4ofzEDAfv5Ngf",
)

main_net = NetworkSettings(
    name="MainNet",
    cl_chain_id_str="W",
    cl_node_api_url="https://nodes.wavesnodes.com",
    el_node_api_url="https://rpc.unit0.dev",
    chain_contract_address="3PKgN8rfmvF7hK7RWJbpvkh59e1pQkUzero",
)

networks = {n.cl_chain_id_str: n for n in [stage_net, test_net, main_net]}


def get_predefined_network_settings(chain_id_str: str) -> NetworkSettings:
    r = networks.get(chain_id_str)
    if not r:
        raise ValueError(f"Unknown network {chain_id_str}")

    return r


class Network:
    def __init__(self, settings: NetworkSettings):
        self.settings = settings

    @cached_property
    def w3(self) -> Web3:
        return Web3(Web3.HTTPProvider(self.settings.el_node_api_url))

    @cached_property
    def cl_chain_contract(self) -> ChainContract:
        return ChainContract(oracleAddress=self.settings.chain_contract_address)

    @cached_property
    def bridges(self) -> Bridges:
        return Bridges(
            self.w3,
            self.cl_chain_contract.getElNativeBridgeAddress(),
            self.cl_chain_contract.getElStandardBridgeAddress(),
        )

    def get_erc20(self, address: ChecksumAddress) -> Erc20:
        return Erc20(self.w3, address)


def create_manual(settings: NetworkSettings) -> Network:
    prepare(settings)
    return Network(settings)


def prepare(settings: NetworkSettings):
    log = logging.getLogger(os.path.basename(__file__))
    log.info(f"Selected {settings.name} ({settings.cl_chain_id_str})")
    pw.setNode(settings.cl_node_api_url, settings.name, settings.cl_chain_id_str)
