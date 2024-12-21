import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { creditsChecker } from './keycheck';
import { rateLimiter } from '../utils/rate_limit';
import { logger } from '../utils/logger';
import { LLMError } from '../utils/errors';
import { v4 as uuidv4 } from 'uuid';

// Types
interface PaceNoteRequest {
  content: string;
  temperature?: number;
  stream?: boolean;
}

interface PolicyFooRequest {
  content: string;
  conversationHistory?: Array<{ role: string; content: string }>;
  temperature?: number;
  stream?: boolean;
}

interface RateLimitResponse {
  hourlyRemaining: number;
  dailyRemaining: number;
}

interface StreamData {
  note?: string;
  remainingRequests: RateLimitResponse;
  error?: {
    message: string;
  };
}

// Setup LLM routes
export async function setupLLMRoutes(app: FastifyInstance) {
  // Initialize agents
  // TODO: Initialize PaceNoteAgent and PolicyFoo agents
  logger.info('LLM routes initialized');

  // Credits check endpoint
  app.get('/llm/credits', async (request: FastifyRequest, reply: FastifyReply) => {
    return {
      creditsAvailable: creditsChecker.hasCredits
    };
  });

  // Rate limits endpoint
  app.get('/llm/limits', async (request: FastifyRequest, reply: FastifyReply) => {
    const remaining = rateLimiter.getRemaining(request.ip);
    return {
      hourlyRemaining: remaining.hourlyRemaining,
      dailyRemaining: remaining.dailyRemaining
    };
  });

  // Pace notes generation endpoint
  app.post<{ Body: PaceNoteRequest }>(
    '/llm/pace-notes/generate',
    async (request, reply) => {
      try {
        const requestId = uuidv4();
        const rateLimits = rateLimiter.getRemaining(request.ip);

        if (request.body.stream) {
          reply.raw.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
          });

          // TODO: Implement PaceNoteAgent
          // const stream = await PaceNoteAgent.generate(
          //   request.body.content,
          //   request.body.temperature,
          //   requestId
          // );

          // Temporary placeholder stream
          const stream = async function* () {
            yield 'Placeholder response - PaceNoteAgent not implemented yet';
          };

          try {
            // Stream the response
            for await (const chunk of stream()) {
              const data: StreamData = {
                note: chunk,
                remainingRequests: rateLimits
              };
              reply.raw.write(`data: ${JSON.stringify(data)}\n\n`);
            }
          } catch (error) {
            const errorData: StreamData = {
              error: {
                message: error instanceof Error ? error.message : 'Unknown error'
              },
              remainingRequests: rateLimits
            };
            reply.raw.write(`data: ${JSON.stringify(errorData)}\n\n`);
          }

          reply.raw.end();
          return reply;
        }

        // Non-streaming response
        // TODO: Implement PaceNoteAgent
        // const note = await PaceNoteAgent.generate(
        //   request.body.content,
        //   request.body.temperature,
        //   requestId
        // );
        const note = 'Placeholder response - PaceNoteAgent not implemented yet';

        if (!note) {
          throw new LLMError('Failed to generate note. Please try again later.');
        }

        return {
          note,
          remainingRequests: rateLimits
        };

      } catch (error) {
        logger.error('Error in pace note generation endpoint:', error);
        throw new LLMError('Internal server error');
      }
    }
  );

  // Cancel generation endpoint
  app.post('/llm/pace-notes/cancel', async (request, reply) => {
    try {
      // Return 200 immediately to allow quick page refreshes
      return reply.status(200).send();
    } catch (error) {
      logger.error('Error in cancel endpoint:', error);
      return reply.status(200).send(); // Still return 200 to allow quick refresh
    }
  });

  // Policy response generation endpoint
  app.post<{ Body: PolicyFooRequest }>(
    '/llm/policyfoo/generate',
    async (request, reply) => {
      try {
        const requestId = uuidv4();

        reply.raw.writeHead(200, {
          'Content-Type': 'text/plain',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no'
        });

        // TODO: Import and implement policy agents
        // const policyFinder = new PolicyFinder();
        // const policyReader = new PolicyReader();
        // const chatAgent = new ChatAgent();

        // Step 1: Find relevant policies
        // const policyRefs = await policyFinder.findRelevantPolicies(
        //   request.body.content,
        //   request.body.conversationHistory,
        //   requestId
        // );

        // Temporary placeholder response
        reply.raw.write(
          '<response><answer>Policy finder not implemented yet</answer><citations></citations><follow_up>Try again later?</follow_up></response>'
        );
        reply.raw.end();
        return reply;

      } catch (error) {
        logger.error('Error in generate_policy_response:', error);
        reply.raw.write(
          '<response><answer>An error occurred while processing your request. Please try again.</answer><citations></citations><follow_up>Try asking a different question?</follow_up></response>'
        );
        reply.raw.end();
        return reply;
      }
    }
  );
} 