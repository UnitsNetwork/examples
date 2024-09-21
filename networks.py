class WavesNetwork:
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
stage_net = WavesNetwork(
    name="StageNet",
    chain_id_str="S",
    cl_node_api_url="https://nodes-stagenet.wavesnodes.com",
    el_node_api_url="https://rpc-stagenet.unit0.dev",
    chain_contract_address="3Mew9817x6rePmCUKNAiRxuzNEP8F2XK1Kd",
)

test_net = WavesNetwork(
    name="TestNet",
    chain_id_str="T",
    cl_node_api_url="https://nodes-testnet.wavesnodes.com",
    el_node_api_url="https://rpc-testnet.unit0.dev",
    chain_contract_address="3Msx4Aq69zWUKy4d1wyKnQ4ofzEDAfv5Ngf",
)

networks = {n.chain_id_str: n for n in [stage_net, test_net]}


def get_network(chain_id_str: str) -> WavesNetwork:
    network = networks.get(chain_id_str)
    if not network:
        raise ValueError(f"Unknown network {chain_id_str}")
    return network
