import { WavesNetwork } from './types';

const StageNet: WavesNetwork = {
  name: 'StageNet',
  clNodeApiUrl: "https://nodes-stagenet.wavesnodes.com",
  elNodeApiUrl: "https://rpc-stagenet.unit0.dev",
  chainContractAddress: "3Mew9817x6rePmCUKNAiRxuzNEP8F2XK1Kd",
};

const TestNet: WavesNetwork = {
  name: 'TestNet',
  clNodeApiUrl: "https://nodes-testnet.wavesnodes.com",
  elNodeApiUrl: "https://rpc-testnet.unit0.dev",
  chainContractAddress: "3MsqKJ6o1ABE37676cHHBxJRs6huYTt72ch",
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
