# IPU Provider

The `IPUProvider` implements the `IUniversityProvider` interface specifically for Indraprastha University (IPU). It is responsible for simulating interactions with the IPU student portal, fetching profiles, and mapping academic results into normalized domain entities.

## Architecture & Lifecycle

1. **`IPUProvider`**: The main entry point that adheres to the `IUniversityProvider` contract.
2. **`IPURequestService`**: The internal request abstraction. It encapsulates HTTP request logic, rate limiting, and raw response parsing (currently simulated).
3. **`IPUMapper`**: Responsible for transforming the raw responses defined in `ipu.types.ts` into strongly typed domain models (`StudentProfile`, `SemesterResult`).
4. **State Machine**: The provider tracks lifecycle states: `UNINITIALIZED`, `READY`, `AUTHENTICATED`, `SYNCING`, `FAILED`, `LOCKED`.

## How Mocked Responses Will Be Replaced

Currently, `IPURequestService` relies on simulated delays and static JSON payloads, controlled by the `useMockData` feature flag in `IPUProviderConfig`.

To replace mocks with actual scraping in the future:
1. **No changes to `IPUProvider` or `IPUMapper` are required.**
2. Only modify `IPURequestService`. Replace the `simulateNetworkDelay()` and static return statements with an HTTP client (like Axios or Fetch) targeting the actual IPU portal.
3. If the IPU HTML changes, update the raw extraction logic in `IPURequestService`.
4. Ensure the actual scraping logic emits the same `IPURawStudentProfile` and `IPURawSemesterResult` interfaces. 

By isolating the HTTP request layer and adhering to dependency inversion, the provider logic, state management, and error handling remain untouched when real network calls are introduced.
