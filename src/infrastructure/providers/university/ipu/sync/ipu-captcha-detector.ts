import { CaptchaRequiredError } from "@/core/errors/provider.error";
import { logger } from "@/shared/lib/logger";

export class IPUCaptchaDetector {
  static detect(html: string): void {
    if (html.includes("g-recaptcha") || html.includes("captcha-image")) {
      logger.warn("IPUCaptchaDetector: Captcha detected in response.");
      throw new CaptchaRequiredError("IPU", "IPU Portal is requesting a captcha. Sync blocked.");
    }
    
    if (html.includes("Access Denied") || html.includes("Cloudflare")) {
      throw new CaptchaRequiredError("IPU", "Access blocked by WAF/Cloudflare.");
    }
  }
}
