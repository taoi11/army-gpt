import { FastifyRequest, FastifyReply } from 'fastify';
import { config } from '../config';
import { logger } from './logger';

interface RequestWindow {
  timestamps: number[];
}

interface RateLimitResponse {
  hourlyRemaining: number;
  dailyRemaining: number;
}

class RateLimiter {
  private hourlyRequests: Map<string, number[]>;
  private dailyRequests: Map<string, number[]>;
  private requestIds: Set<string>;
  private readonly HOUR = 3600; // seconds
  private readonly DAY = 86400; // seconds
  private creditsCheck: () => boolean;

  constructor() {
    this.hourlyRequests = new Map();
    this.dailyRequests = new Map();
    this.requestIds = new Set();
    this.creditsCheck = () => true;
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

    // Cleanup old request IDs
    this.requestIds = new Set(
      Array.from(this.requestIds).filter(rid => {
        const [timestamp] = rid.split('-');
        return timestamp.startsWith('t') &&
          currentTime - parseFloat(timestamp.slice(1)) < this.DAY;
      })
    );
  }

  setCreditsCheck(callback: () => boolean): void {
    this.creditsCheck = callback;
  }

  isAllowed(ip: string, requestId?: string): boolean {
    // Skip rate limiting for backup LLM
    if (!this.creditsCheck()) {
      return true;
    }

    this.cleanupOldRequests(ip);

    // Handle duplicate requests
    if (requestId) {
      if (this.requestIds.has(requestId)) {
        return true;
      }
      const timestampedId = `t${Date.now() / 1000}-${requestId}`;
      this.requestIds.add(timestampedId);
    }

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
    if (!this.creditsCheck()) {
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

// Fastify plugin for rate limiting
export async function rateLimitPlugin(
  request: FastifyRequest,
  reply: FastifyReply
) {
  const clientIp = request.ip;
  const requestId = request.headers['x-request-id'] as string;

  // Only check LLM generation endpoints
  const isLLMGeneration = (
    request.url.startsWith('/llm/pace-notes/generate') ||
    request.url.startsWith('/llm/policyfoo/generate')
  ) && request.method === 'POST';

  if (isLLMGeneration && rateLimiter.creditsCheck()) {
    if (!rateLimiter.isAllowed(clientIp, requestId)) {
      const remaining = rateLimiter.getRemaining(clientIp);
      return reply.status(429).send({
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
      });
    }
  }

  // Add response hook to track successful requests
  reply.addHook('onSend', (request, reply, payload, done) => {
    if (isLLMGeneration && reply.statusCode === 200) {
      rateLimiter.addRequest(clientIp);
    }
    
    // Add rate limit headers
    const remaining = rateLimiter.getRemaining(clientIp);
    reply.header('X-RateLimit-Remaining-Hour', remaining.hourlyRemaining.toString());
    reply.header('X-RateLimit-Remaining-Day', remaining.dailyRemaining.toString());
    reply.header('Access-Control-Expose-Headers', 'X-RateLimit-Remaining-Hour, X-RateLimit-Remaining-Day');
    
    done(null, payload);
  });
} 