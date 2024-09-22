import json
import logging
import os

from eth_utils.abi import event_abi_to_log_topic
from pywaves import pw
from web3 import Web3

from chain_contract import ChainContract


class NetworkSettings:
    def __init__(
        self,
        name: str,
        chain_id_str: str,
        cl_node_api_url: str,
        el_node_api_url: str,
        chain_contract_address: str,
    ):
        self.name = name
        self.chain_id_str = chain_id_str
        self.chain_id = ord(chain_id_str)
        self.cl_node_api_url = cl_node_api_url
        self.el_node_api_url = el_node_api_url
        self.chain_contract_address = chain_contract_address


# Creating instances for each network
stage_net = NetworkSettings(
    name="StageNet",
    chain_id_str="S",
    cl_node_api_url="https://nodes-stagenet.wavesnodes.com",
    el_node_api_url="https://rpc-stagenet.unit0.dev",
    chain_contract_address="3Mew9817x6rePmCUKNAiRxuzNEP8F2XK1Kd",
)

test_net = NetworkSettings(
    name="TestNet",
    chain_id_str="T",
    cl_node_api_url="https://nodes-testnet.wavesnodes.com",
    el_node_api_url="https://rpc-testnet.unit0.dev",
    chain_contract_address="3Msx4Aq69zWUKy4d1wyKnQ4ofzEDAfv5Ngf",
)

networks = {n.chain_id_str: n for n in [stage_net, test_net]}


def get_network_settings(chain_id_str: str) -> NetworkSettings:
    r = networks.get(chain_id_str)
    if not r:
        raise ValueError(f"Unknown network {chain_id_str}")

    return r


class Network:
    def __init__(self, settings: NetworkSettings):
        self.settings = settings
        self.cl_chain_contract = ChainContract(
            oracleAddress=settings.chain_contract_address
        )
        self.w3 = Web3(Web3.HTTPProvider(settings.el_node_api_url))

        with open("bridge-abi.json") as f:
            el_bridge_abi = json.load(f)

        self.el_bridge_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(
                self.cl_chain_contract.getElBridgeAddress()
            ),
            abi=el_bridge_abi,
        )
        self.el_send_native_topic = event_abi_to_log_topic(
            self.el_bridge_contract.events.SentNative().abi
        ).hex()


def select_network(chain_id_str: str) -> Network:
    s = get_network_settings(chain_id_str)
    log = logging.getLogger(os.path.basename(__file__))
    log.info(f"Selected {s.name}")
    pw.setNode(s.cl_node_api_url, s.chain_id_str)
    return Network(s)
