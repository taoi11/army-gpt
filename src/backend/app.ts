import fastify from 'fastify';
import { config } from './config.js';
import { logger } from './utils/logger.js';
import { errorHandler } from './utils/errors.js';
import { setupWebRoutes } from './utils/web.js';
import { setupLLMRoutes } from './llm/routes.js';
import { creditsChecker } from './llm/keycheck.js';
import { rateLimiter, checkRateLimit } from './utils/rate_limit.js';
import { setupPolicyRoutes } from './policyfoo/routes.js';

// Immediate environment check
console.log('Environment check:', {
  NODE_ENV: process.env.NODE_ENV,
  DEBUG_MODE: process.env.DEBUG_MODE,
  LOG_LEVEL: process.env.LOG_LEVEL
});

// Create Fastify instance
const app = fastify({
  logger: false, // We use our own logger
  trustProxy: true
});

// Register plugins and routes
async function bootstrap() {
  try {
    logger.debug('Starting server bootstrap process');
    logger.debug('Server config:', { 
      debug: config.server.debug,
      logLevel: config.server.logLevel,
      port: config.server.port,
      host: config.server.host
    });

    // Set error handler
    app.setErrorHandler(errorHandler);
    logger.debug('Error handler registered');

    // Add rate limiting middleware
    app.addHook('preHandler', checkRateLimit);
    logger.debug('Rate limit middleware registered');

    // Setup routes
    await setupWebRoutes(app);
    logger.debug('Web routes initialized');
    
    await setupLLMRoutes(app);
    logger.debug('LLM routes initialized');
    
    await setupPolicyRoutes(app);
    logger.debug('Policy routes initialized');

    // Start credit checker and connect it to rate limiter
    creditsChecker.start();
    creditsChecker.onCreditsChange((hasCredits) => {
      rateLimiter.setHasCredits(hasCredits);
      logger.debug('Credits state changed:', { hasCredits });
    });
    logger.debug('Credit checker initialized');

    // Start server
    const port = config.server.port || 8020;
    const host = config.server.host || '0.0.0.0';

    await app.listen({ port, host });
    logger.info(`Server listening on ${host}:${port}`);
    logger.debug('Server bootstrap completed successfully');

    // Graceful shutdown
    const shutdown = async () => {
      logger.info('Shutting down server...');
      creditsChecker.stop();
      await app.close();
      process.exit(0);
    };

    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);

  } catch (err) {
    logger.error('Error starting server:', err);
    process.exit(1);
  }
}

// Start the server
bootstrap(); 