export interface MarketData {
  last_price?: number;
  high_24h?: number;
  low_24h?: number;
  volume_24h?: number;
}

export interface Analysis {
  reasoning?: string;
  analysis?: string;
  confidence?: number;
  recommendation?: 'buy' | 'sell' | 'hold';
}

export interface PositionInfo {
  盈亏信息?: {
    当前持仓?: number;
    持仓均价?: number;
    持仓市值?: number;
    未实现盈亏?: number;
    总盈亏?: number;
    总手续费?: number;
  };
  资金信息?: {
    总资金?: number;
    已用资金?: number;
    可用资金?: number;
  };
}

export interface StrategyState {
  status: 'running' | 'stopped' | 'paused';
  position_info?: PositionInfo;
}

export type Period = '1m' | '5m' | '15m' | '1H' | '4H' | '1D'; 