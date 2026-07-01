export interface IPortalClient {
  get(path: string, options?: Record<string, any>): Promise<string>;
  post(path: string, data?: Record<string, any>, options?: Record<string, any>): Promise<string>;
  setHeaders(headers: Record<string, string>): void;
}
