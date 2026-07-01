export class ProviderError extends Error {
  constructor(message: string, public readonly code: string, public readonly providerId: string) {
    super(message);
    this.name = "ProviderError";
  }
}

export class AuthenticationError extends ProviderError {
  constructor(providerId: string, message = "Invalid credentials provided.") {
    super(message, "AUTHENTICATION_ERROR", providerId);
    this.name = "AuthenticationError";
  }
}

export class ProviderUnavailableError extends ProviderError {
  constructor(providerId: string, message = "University portal is currently unavailable.") {
    super(message, "PROVIDER_UNAVAILABLE", providerId);
    this.name = "ProviderUnavailableError";
  }
}

export class PortalChangedError extends ProviderError {
  constructor(providerId: string, message = "University portal structure has changed.") {
    super(message, "PORTAL_CHANGED", providerId);
    this.name = "PortalChangedError";
  }
}

export class RateLimitError extends ProviderError {
  constructor(providerId: string, message = "Rate limit exceeded for university portal.") {
    super(message, "RATE_LIMIT_EXCEEDED", providerId);
    this.name = "RateLimitError";
  }
}

export class CaptchaRequiredError extends ProviderError {
  constructor(providerId: string, message = "Captcha required for authentication.") {
    super(message, "CAPTCHA_REQUIRED", providerId);
    this.name = "CaptchaRequiredError";
  }
}

export class InvalidCredentialsError extends ProviderError {
  constructor(providerId: string, message = "The credentials provided are in an invalid format.") {
    super(message, "INVALID_CREDENTIALS", providerId);
    this.name = "InvalidCredentialsError";
  }
}

export class ParsingError extends ProviderError {
  constructor(providerId: string, message = "Failed to parse data from university portal.") {
    super(message, "PARSING_ERROR", providerId);
    this.name = "ParsingError";
  }
}

export class NetworkError extends ProviderError {
  constructor(providerId: string, message = "Network error while communicating with university portal.") {
    super(message, "NETWORK_ERROR", providerId);
    this.name = "NetworkError";
  }
}
