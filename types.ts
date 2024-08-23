import * as waves from '@waves/node-api-js';

export interface WavesNetwork {
  clNodeApiUrl: string;
  elNodeApiUrl: string;
  chainContractAddress: string;
  elBridgeAddress: string;
}

export interface E2CTransfer {
  recipientAddressB58: string,
  amount: string
}

export interface C2ETransfer {
  elRecipientAddress: string,
  amount: string
}

export interface EcBlockContractInfo {
  chainHeight: number,
  epochNumber: number
}

export type WavesApi = ReturnType<typeof waves.create>;
