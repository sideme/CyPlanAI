export type StreamMessage = {
  id?: string;
  type: string;
  content?: unknown;
  clientOptimistic?: boolean;
  [key: string]: unknown;
};

export type StreamCheckpoint = {
  checkpoint_id?: string;
  [key: string]: unknown;
};
