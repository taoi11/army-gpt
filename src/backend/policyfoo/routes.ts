import { FastifyInstance } from 'fastify';
import { rateLimitPlugin } from '../utils/rate_limit';
import { PolicyError } from './types';
import { PolicyFinder } from './finder';
import { PolicyReader } from './reader';
import { PolicyChat } from './chat';

// Initialize agents
const finder = new PolicyFinder();
const reader = new PolicyReader();
const chat = new PolicyChat();

export async function setupPolicyRoutes(app: FastifyInstance) {
  // Apply rate limiting to all policy routes
  app.addHook('preHandler', rateLimitPlugin);

  // Search policies endpoint
  app.post('/api/policy/search', async (request, reply) => {
    try {
      const { query, options = {} } = request.body as { query: string; options?: any };
      const results = await finder.search(query, options);
      return reply.send(results);
    } catch (error) {
      if (error instanceof PolicyError) {
        return reply.status(400).send({ error: error.message });
      }
      throw error;
    }
  });

  // Read policy endpoint
  app.post('/api/policy/read', async (request, reply) => {
    try {
      const { policyNumber, section, options = {} } = request.body as { 
        policyNumber: string;
        section: string;
        options?: any;
      };
      const content = await reader.read(policyNumber, section, options);
      return reply.send(content);
    } catch (error) {
      if (error instanceof PolicyError) {
        return reply.status(400).send({ error: error.message });
      }
      throw error;
    }
  });

  // Chat endpoint
  app.post('/api/policy/chat', async (request, reply) => {
    try {
      const { message, history = [], options = {} } = request.body as {
        message: string;
        history?: any[];
        options?: any;
      };
      const response = await chat.respond(message, history, options);
      return reply.send(response);
    } catch (error) {
      if (error instanceof PolicyError) {
        return reply.status(400).send({ error: error.message });
      }
      throw error;
    }
  });

  // Stream chat endpoint
  app.post('/api/policy/chat/stream', async (request, reply) => {
    try {
      const { message, history = [], options = {} } = request.body as {
        message: string;
        history?: any[];
        options?: any;
      };

      reply.raw.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
      });

      for await (const chunk of chat.streamResponse(message, history, { ...options, stream: true })) {
        reply.raw.write(`data: ${JSON.stringify({ content: chunk })}\n\n`);
      }

      reply.raw.write('data: [DONE]\n\n');
      reply.raw.end();
    } catch (error) {
      if (!reply.sent) {
        if (error instanceof PolicyError) {
          return reply.status(400).send({ error: error.message });
        }
        throw error;
      }
    }
  });
} 