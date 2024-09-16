import * as waves from '@waves/node-api-js';

export interface WavesNetwork {
  name: string;
  clNodeApiUrl: string;
  elNodeApiUrl: string;
  chainContractAddress: string;
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
