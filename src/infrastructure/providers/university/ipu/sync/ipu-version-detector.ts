import { PortalChangedError } from "@/core/errors/provider.error";
import { logger } from "@/shared/lib/logger";

export class IPUVersionDetector {
  private static readonly EXPECTED_SIGNATURES = [
    "Dashboard Logged In v1.0",
    "Profile: ",
    "Results Table Data"
  ];

  static detect(html: string): string {
    // In a real scenario, this extracts a meta tag or specific DOM structure hash.
    // If the expected DOM elements are completely missing, it implies a major UI overhaul.
    
    const isValid = this.EXPECTED_SIGNATURES.some(sig => html.includes(sig)) || html.includes("<html>");
    
    if (!isValid) {
      logger.error("IPUVersionDetector: Portal layout changed significantly.");
      throw new PortalChangedError("IPU", "The IPU Portal HTML structure has changed. Parsers require updating.");
    }
    
    return "v1.0";
  }
}
