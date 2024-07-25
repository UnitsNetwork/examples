import { WavesNetwork } from './types';

const StageNet: WavesNetwork = {
  clNodeApiUrl: "https://nodes-stagenet.wavesnodes.com",
  elNodeApiUrl: "https://rpc-stagenet.unit0.dev",
  chainContractAddress: "3Mew9817x6rePmCUKNAiRxuzNEP8F2XK1Kd",
  elBridgeAddress: "0xadc0526e55b2234e62e3cc2ac13191552bed542f"
};

const TestNet: WavesNetwork = {
  clNodeApiUrl: "https://nodes-testnet.wavesnodes.com",
  elNodeApiUrl: "https://rpc-testnet.unit0.dev",
  chainContractAddress: "3MsqKJ6o1ABE37676cHHBxJRs6huYTt72ch",
  elBridgeAddress: "0x33ce7f46EbC22D01B50e2eEb8DcD26C31a0e027C"
};

const networks = {
  'S': StageNet,
  'T': TestNet
}

export function getNetwork(chainIdStr: string): WavesNetwork {
  const r = networks[chainIdStr];
  if (!r) throw new Error(`Unknown network ${chainIdStr}`);
  return r;
}
