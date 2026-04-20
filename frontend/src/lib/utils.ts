import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function defangUrl(url: string): string {
  let result = url.replace(/^https/i, "hxxps").replace(/^http/i, "hxxp");
  try {
    const parsed = new URL(url);
    const defangedHost = parsed.hostname.replace(/\./g, "[.]");
    result = result.replace(parsed.hostname, defangedHost);
  } catch {
    // If URL parsing fails, just replace dots after the protocol
    const protocolEnd = result.indexOf("://");
    if (protocolEnd !== -1) {
      const pathStart = result.indexOf("/", protocolEnd + 3);
      const domainEnd = pathStart === -1 ? result.length : pathStart;
      const domain = result.slice(protocolEnd + 3, domainEnd);
      result = result.slice(0, protocolEnd + 3) + domain.replace(/\./g, "[.]") + result.slice(domainEnd);
    }
  }
  return result;
}
