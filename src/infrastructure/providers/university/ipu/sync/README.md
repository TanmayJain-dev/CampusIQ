# Academic Synchronization Engine

This module represents the independent synchronization subsystem for IPU. It securely retrieves data from the university portal and returns normalized domain models.

## Responsibilities
- **IPUSyncEngine**: Orchestrates the sync flow (Auth -> Fetch Profile -> Fetch Results -> Cleanup), utilizing retry strategies and returning a normalized `SyncResult`.
- **IPUPortalClient**: An HTTP client abstraction. Currently returns mocked responses based on configuration, but can be replaced by Axios or Playwright without altering sync logic.
- **IPUSessionManager**: Handles login, session creation, and expiration securely.
- **IPUParsers**: Pure functions that extract data from raw HTML. Completely independent of networking.
- **Detectors**: `IPUCaptchaDetector` and `IPUVersionDetector` catch portal anomalies early and throw typed errors.

## Connecting to the Dashboard and Database
The synchronization engine operates completely independently from the Dashboard, Database, and Notification systems. 

**Integration Architecture:**
1. The **Background Sync Worker** (part of the Academic Service) retrieves credentials from the `CredentialVault`.
2. The worker instantiates `IPUSyncEngine` (via `UniversityProviderFactory`) and calls `executeSync(credentials)`.
3. The engine performs the HTTP operations and returns a strongly-typed `SyncResult<AcademicSyncData>`.
4. If `success: true`, the worker takes the normalized data and uses Prisma ORM to upsert the records into the database.
5. If the worker detects newly inserted data (e.g., a new semester result), it dispatches an event to the **Notification Service**.
6. The **Dashboard** exclusively queries the local database. It never interacts with the synchronization engine directly.

By keeping this subsystem isolated, we ensure that changes to IPU's HTML layout only require updating the `IPUParsers`, with zero impact on the UI, database, or analytics.
