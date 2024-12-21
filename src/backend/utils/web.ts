import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { join } from 'path';
import { fileURLToPath } from 'url';
import fastifyStatic from '@fastify/static';
import fastifyView from '@fastify/view';
import fastifyCors from '@fastify/cors';
import ejs from 'ejs';
import { config } from '../config';
import { logger } from './logger';

const __filename = fileURLToPath(import.meta.url);
const __dirname = join(__filename, '..');

// Setup web routes
export async function setupWebRoutes(app: FastifyInstance) {
  // Register static file serving
  await app.register(fastifyStatic, {
    root: join(__dirname, '../../frontend/static'),
    prefix: '/static/'
  });

  // Register template engine (using @fastify/view with ejs)
  await app.register(fastifyView, {
    engine: {
      ejs: ejs
    },
    root: join(__dirname, '../../frontend/templates')
  });

  // Web routes
  app.get('/', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      return reply.view('index.ejs', { request });
    } catch (error) {
      logger.error('Error serving index page:', error);
      return reply.status(500).send('Internal Server Error');
    }
  });

  app.get('/pace-notes', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      return reply.view('pace-notes.ejs', { request });
    } catch (error) {
      logger.error('Error serving pace notes page:', error);
      return reply.status(500).send('Internal Server Error');
    }
  });

  app.get('/policy-foo', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      return reply.view('policy-foo.ejs', { request });
    } catch (error) {
      logger.error('Error serving policy foo page:', error);
      return reply.status(500).send('Internal Server Error');
    }
  });

  // API routes
  app.get('/api/costs', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      // TODO: Implement cost tracking
      const costs = { api: 0, server: 0 }; // Placeholder
      logger.debug('Returning costs:', costs);
      return reply.send(costs);
    } catch (error) {
      logger.error('Error getting costs:', error);
      return reply.status(500).send({
        error: 'Internal server error'
      });
    }
  });

  // Register CORS
  await app.register(fastifyCors, {
    origin: true, // In production, replace with specific origins
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
    exposedHeaders: ['X-RateLimit-Remaining-Hour', 'X-RateLimit-Remaining-Day'],
    credentials: true
  });

  // Error handler
  app.setErrorHandler((error, request, reply) => {
    logger.error('Unhandled error:', error);
    reply.status(500).send({
      error: 'Internal Server Error'
    });
  });
} 