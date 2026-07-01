// We don't have Jest or Vitest installed yet, so this serves as the structural foundation 
// for how the tests will be written once the testing framework is added.

import { MockUniversityProvider } from "../__mocks__/mock.provider";
import { UniversityProviderFactory } from "../provider-factory";
import { ProviderRegistry } from "../provider-registry";

describe("UniversityProviderFactory", () => {
  beforeAll(() => {
    // Manually register a mock provider for testing
    const registry = ProviderRegistry.getInstance();
    registry.register(new MockUniversityProvider("TEST_UNIV"));
  });

  it("should resolve the correct provider", () => {
    const provider = UniversityProviderFactory.getProvider("TEST_UNIV");
    expect(provider).toBeDefined();
    expect(provider.getProviderId()).toBe("TEST_UNIV");
  });

  it("should throw error for unregistered provider", () => {
    expect(() => {
      UniversityProviderFactory.getProvider("UNKNOWN_UNIV");
    }).toThrow("University Provider not found");
  });
});
