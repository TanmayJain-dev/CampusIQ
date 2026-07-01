export enum SessionState {
  ACTIVE = 'ACTIVE',
  EXPIRED = 'EXPIRED',
  INVALID = 'INVALID',
  UNAUTHENTICATED = 'UNAUTHENTICATED'
}

export interface ISessionManager<TCredentials, TSessionContext> {
  createSession(credentials: TCredentials): Promise<TSessionContext>;
  refreshSession(context: TSessionContext): Promise<TSessionContext>;
  expireSession(context: TSessionContext): void;
  destroySession(context: TSessionContext): Promise<void>;
  validateSession(context: TSessionContext): Promise<boolean>;
  recoverSession(credentials: TCredentials, context: TSessionContext): Promise<TSessionContext>;
}
