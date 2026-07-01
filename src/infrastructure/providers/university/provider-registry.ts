import { IUniversityProvider } from "@/core/interfaces/university-provider.interface";
import { logger } from "@/shared/lib/logger";

/**
 * A central registry for all university providers.
 * Adheres to the Singleton pattern to ensure a single source of truth across the application.
 */
export class ProviderRegistry {
  private static instance: ProviderRegistry;
  private providers: Map<string, IUniversityProvider> = new Map();

  private constructor() {}

  public static getInstance(): ProviderRegistry {
    if (!ProviderRegistry.instance) {
      ProviderRegistry.instance = new ProviderRegistry();
    }
    return ProviderRegistry.instance;
  }

  public register(provider: IUniversityProvider): void {
    const id = provider.getProviderId();
    if (this.providers.has(id)) {
      logger.warn({ providerId: id }, "Provider is being overwritten in registry");
    }
    this.providers.set(id, provider);
    logger.info({ providerId: id }, "Provider registered successfully");
  }

  public get(providerId: string): IUniversityProvider | undefined {
    return this.providers.get(providerId);
  }

  public getAllRegisteredIds(): string[] {
    return Array.from(this.providers.keys());
  }
}
