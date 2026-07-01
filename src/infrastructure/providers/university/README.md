# University Provider System

This module implements a scalable, pluggable architecture for university result scraping and data retrieval. It strictly follows the Dependency Inversion Principle, meaning the application core depends on abstractions (`IUniversityProvider`), not concrete scrapers.

## Architecture

1. **`IUniversityProvider`**: The contract every university integration must fulfill.
2. **`ProviderRegistry`**: A singleton registry holding active provider instances.
3. **`UniversityProviderFactory`**: The entry point for the application to resolve the correct provider by University ID.

## How to add a new University Provider

Adding a new university (e.g., Delhi University - DU) takes less than an hour if the scraping logic is known. You do not need to modify any existing UI, Database, or API logic.

### 1. Create the Provider Class
Create a new folder: `src/infrastructure/providers/university/du/`.
Create `du.provider.ts`:

```typescript
import { IUniversityProvider } from "@/core/interfaces/university-provider.interface";
import { logger } from "@/shared/lib/logger";

export class DUProvider implements IUniversityProvider {
  getProviderId() { return 'DU'; }
  // ... implement interface methods
}
```

### 2. Throw Standard Errors
Inside your scraping logic, map university-specific errors (like HTML changes or timeouts) to our domain errors located in `src/core/errors/provider.error.ts`.
- `throw new AuthenticationError('DU', 'Wrong DOB')`
- `throw new PortalChangedError('DU')`

### 3. Register the Provider
Open `src/infrastructure/providers/university/provider-factory.ts` and add it to the bootstrap method:

```typescript
static initializeDefaultProviders(): void {
  const registry = ProviderRegistry.getInstance();
  
  // ... existing IPU registration
  
  registry.register(new DUProvider({ baseUrl: "..." }));
}
```

### 4. Done.
The application's background workers and API routes will now automatically support the new university ID.
