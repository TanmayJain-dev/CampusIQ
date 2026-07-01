import { AuthenticationError } from "@/core/errors/provider.error";
import { ProviderCredentials } from "@/core/interfaces/university-provider.interface";
import { IPortalClient } from "@/infrastructure/sync-engine/portal-client.interface";
import { ISessionManager, SessionState } from "@/infrastructure/sync-engine/session-manager.interface";
import { logger } from "@/shared/lib/logger";

export interface IPUSessionContext {
  token: string;
  state: SessionState;
  createdAt: number;
}

export class IPUSessionManager implements ISessionManager<ProviderCredentials, IPUSessionContext> {
  constructor(private readonly portalClient: IPortalClient) {}

  async createSession(credentials: ProviderCredentials): Promise<IPUSessionContext> {
    logger.debug("IPUSessionManager: Creating session");
    
    const response = await this.portalClient.post("/api/login", {
      enrollmentNo: credentials.enrollmentNo,
      password: credentials.password
    });

    if (response.includes("Invalid")) {
      throw new AuthenticationError("IPU", "Invalid credentials provided");
    }

    // Mock token extraction
    const token = "mock-jwt-token-123";
    this.portalClient.setHeaders({ 'Authorization': `Bearer ${token}` });

    return {
      token,
      state: SessionState.ACTIVE,
      createdAt: Date.now()
    };
  }

  async refreshSession(context: IPUSessionContext): Promise<IPUSessionContext> {
    logger.debug("IPUSessionManager: Refreshing session");
    return { ...context, createdAt: Date.now() };
  }

  expireSession(context: IPUSessionContext): void {
    logger.debug("IPUSessionManager: Expiring session");
    context.state = SessionState.EXPIRED;
  }

  async destroySession(context: IPUSessionContext): Promise<void> {
    logger.debug("IPUSessionManager: Destroying session");
    await this.portalClient.post("/api/logout");
    context.state = SessionState.INVALID;
  }

  async validateSession(context: IPUSessionContext): Promise<boolean> {
    if (context.state !== SessionState.ACTIVE) return false;
    
    // Simulate check
    const age = Date.now() - context.createdAt;
    return age < 3600000; // 1 hour valid
  }

  async recoverSession(credentials: ProviderCredentials, context: IPUSessionContext): Promise<IPUSessionContext> {
    logger.warn("IPUSessionManager: Recovering session");
    return this.createSession(credentials);
  }
}
