import { FastifyRequest, FastifyReply } from 'fastify';
import { config } from '../config.js';
import { logger } from './logger.js';

// Types
interface RateLimitResponse {
  hourlyRemaining: number;
  dailyRemaining: number;
}

interface RateLimitError {
  error: {
    code: 429;
    message: string;
    details: {
      hourlyRemaining: number;
      dailyRemaining: number;
      hourlyLimit: number;
      dailyLimit: number;
      retryAfter: string;
    };
  };
}

const RATE_LIMITED_ENDPOINTS = [
  '/api/llm/pace-notes/generate',
  '/api/llm/policyfoo/chat'
] as const;

type RateLimitedEndpoint = typeof RATE_LIMITED_ENDPOINTS[number];

// Simple rate limiter class
class RateLimiter {
  private hourlyRequests: Map<string, number[]>;
  private dailyRequests: Map<string, number[]>;
  private readonly HOUR = 3600; // seconds
  private readonly DAY = 86400; // seconds
  private hasCredits: boolean;

  constructor() {
    this.hourlyRequests = new Map();
    this.dailyRequests = new Map();
    this.hasCredits = true;
  }

  setHasCredits(value: boolean): void {
    this.hasCredits = value;
  }

  private cleanupOldRequests(ip: string): void {
    const currentTime = Date.now() / 1000;

    // Cleanup hourly requests
    const hourlyTimestamps = this.hourlyRequests.get(ip) || [];
    this.hourlyRequests.set(
      ip,
      hourlyTimestamps.filter(ts => currentTime - ts < this.HOUR)
    );

    // Cleanup daily requests
    const dailyTimestamps = this.dailyRequests.get(ip) || [];
    this.dailyRequests.set(
      ip,
      dailyTimestamps.filter(ts => currentTime - ts < this.DAY)
    );
  }

  isAllowed(ip: string): boolean {
    // Skip rate limiting when using backup LLM
    if (!this.hasCredits) {
      return true;
    }

    this.cleanupOldRequests(ip);

    const hourlyCount = (this.hourlyRequests.get(ip) || []).length;
    const dailyCount = (this.dailyRequests.get(ip) || []).length;

    return hourlyCount < config.rateLimiting.hourlyLimit &&
           dailyCount < config.rateLimiting.dailyLimit;
  }

  addRequest(ip: string): void {
    const currentTime = Date.now() / 1000;
    
    // Initialize arrays if they don't exist
    if (!this.hourlyRequests.has(ip)) {
      this.hourlyRequests.set(ip, []);
    }
    if (!this.dailyRequests.has(ip)) {
      this.dailyRequests.set(ip, []);
    }

    // Add timestamps
    this.hourlyRequests.get(ip)?.push(currentTime);
    this.dailyRequests.get(ip)?.push(currentTime);
  }

  getRemaining(ip: string): RateLimitResponse {
    this.cleanupOldRequests(ip);

    // Return unlimited for backup LLM
    if (!this.hasCredits) {
      return {
        hourlyRemaining: 999,
        dailyRemaining: 999
      };
    }

    const hourlyCount = (this.hourlyRequests.get(ip) || []).length;
    const dailyCount = (this.dailyRequests.get(ip) || []).length;

    return {
      hourlyRemaining: Math.max(0, config.rateLimiting.hourlyLimit - hourlyCount),
      dailyRemaining: Math.max(0, config.rateLimiting.dailyLimit - dailyCount)
    };
  }
}

// Create singleton instance
export const rateLimiter = new RateLimiter();

// Simple middleware function
export async function checkRateLimit(request: FastifyRequest, reply: FastifyReply): Promise<void> {
  // Only check specific endpoints
  const isLimitedEndpoint = (
    RATE_LIMITED_ENDPOINTS.includes(request.url as RateLimitedEndpoint) &&
    request.method === 'POST'
  );

  if (!isLimitedEndpoint) {
    return;
  }

  const clientIp = request.ip;

  if (!rateLimiter.isAllowed(clientIp)) {
    const remaining = rateLimiter.getRemaining(clientIp);
    const response: RateLimitError = {
      error: {
        code: 429,
        message: 'Rate limit exceeded',
        details: {
          hourlyRemaining: remaining.hourlyRemaining,
          dailyRemaining: remaining.dailyRemaining,
          hourlyLimit: config.rateLimiting.hourlyLimit,
          dailyLimit: config.rateLimiting.dailyLimit,
          retryAfter: 'Wait for the next hour or day depending on which limit was exceeded'
        }
      }
    };
    reply.status(429).send(response);
    return;
  }

  // Add rate limit headers
  const remaining = rateLimiter.getRemaining(clientIp);
  reply.header('X-RateLimit-Remaining-Hour', remaining.hourlyRemaining.toString());
  reply.header('X-RateLimit-Remaining-Day', remaining.dailyRemaining.toString());
  reply.header('Access-Control-Expose-Headers', 'X-RateLimit-Remaining-Hour, X-RateLimit-Remaining-Day');
} 