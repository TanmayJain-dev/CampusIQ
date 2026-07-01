import { IUniversityProvider } from "@/core/interfaces/university-provider.interface";
import { IPUProvider } from "./ipu/ipu.provider";
import { ProviderRegistry } from "./provider-registry";

/**
 * Factory responsible for initializing and resolving University Providers.
 * This abstracts away the provider instantiation from the rest of the application.
 */
export class UniversityProviderFactory {
  private static initialized = false;

  /**
   * Bootstraps the registry with default providers.
   * In a real application, configuration would be injected via environment variables.
   */
  static initializeDefaultProviders(): void {
    if (this.initialized) return;

    const registry = ProviderRegistry.getInstance();
    
    // Instantiate IPU Provider with configuration
    const ipuConfig = {
      baseUrl: "https://mock.ipu.ac.in",
      timeoutMs: 10000,
      retryPolicy: { maxRetries: 3, backoffMs: 1000 },
      userAgent: "CampusIQ-Bot",
      rateLimitSettings: { requestsPerMinute: 30 },
      featureFlags: { enableHtmlParsing: false, useMockData: true }
    };
    registry.register(new IPUProvider(ipuConfig));
    
    // Future providers (DU, AKTU, etc.) can be instantiated and registered here.
    
    this.initialized = true;
  }

  /**
   * Resolves the correct provider for a given university ID.
   * Throws an error if the provider is not registered, preventing runtime failures down the line.
   */
  static getProvider(universityId: string): IUniversityProvider {
    // Ensure initialized
    this.initializeDefaultProviders();

    const registry = ProviderRegistry.getInstance();
    const provider = registry.get(universityId);
    
    if (!provider) {
      throw new Error(`University Provider not found for ID: ${universityId}. Ensure it is registered in UniversityProviderFactory.`);
    }
    
    return provider;
  }
}
