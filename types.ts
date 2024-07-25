import * as waves from '@waves/node-api-js';

export interface WavesNetwork {
  clNodeApiUrl: string;
  elNodeApiUrl: string;
  chainContractAddress: string;
  elBridgeAddress: string;
}

export interface ElToClTransfer {
  recipient: string,
  amount: string
}

export interface EcBlockContractInfo {
  chainHeight: number,
  epochNumber: number
}

export type WavesApi = ReturnType<typeof waves.create>;
