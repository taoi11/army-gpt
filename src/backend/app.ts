import fastify from 'fastify';
import { config } from './config.js';
import { logger } from './utils/logger.js';
import { errorHandler } from './utils/errors.js';
import { setupWebRoutes } from './utils/web.js';
import { setupLLMRoutes } from './llm/routes.js';
import { creditsChecker } from './llm/keycheck.js';
import { rateLimiter, checkRateLimit } from './utils/rate_limit.js';
import { setupPolicyRoutes } from './policyfoo/routes.js';

// Create Fastify instance
const app = fastify({
  logger: false, // We use our own logger
  trustProxy: true
});

// Register plugins and routes
async function bootstrap() {
  try {
    // Set error handler
    app.setErrorHandler(errorHandler);

    // Add rate limiting middleware
    app.addHook('preHandler', checkRateLimit);

    // Setup routes
    await setupWebRoutes(app);
    await setupLLMRoutes(app);
    await setupPolicyRoutes(app);

    // Start credit checker and connect it to rate limiter
    creditsChecker.start();
    creditsChecker.onCreditsChange((hasCredits) => {
      rateLimiter.setHasCredits(hasCredits);
    });

    // Start server
    const port = config.server.port || 8020;
    const host = config.server.host || '0.0.0.0';

    await app.listen({ port, host });
    logger.info(`Server listening on ${host}:${port}`);

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