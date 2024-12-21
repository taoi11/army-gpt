// Message types
export interface Message {
  role: string;
  content: string;
}

// Response types
export interface PolicyResponse {
  answer: string;
  citations: string[];
  followUp: string;
}

export interface PolicyReference {
  number: string;
  title: string;
  relevance: number;  // 0-1 score
}

export interface PolicyContent {
  policyNumber: string;
  section: string;
  content: string;
}

// Agent options
export interface PolicyAgentOptions {
  temperature?: number;
  stream?: boolean;
  maxTokens?: number;
}

// Error types
export class PolicyError extends Error {
  constructor(
    message: string,
    public readonly type: 'FINDER_ERROR' | 'READER_ERROR' | 'CHAT_ERROR',
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'PolicyError';
  }
}

// XML Response helpers
export const formatResponse = (
  answer: string,
  citations: string[] = [],
  followUp: string = ''
): string => {
  return `<response>
  <answer>${answer}</answer>
  <citations>${citations.join('\n')}</citations>
  <follow_up>${followUp}</follow_up>
</response>`;
}

export const parseResponse = (xml: string): PolicyResponse => {
  // Simple XML parsing - we can make this more robust if needed
  const getContent = (tag: string): string => {
    const match = xml.match(new RegExp(`<${tag}>(.*?)</${tag}>`, 's'));
    return match ? match[1].trim() : '';
  };

  return {
    answer: getContent('answer'),
    citations: getContent('citations').split('\n').filter(Boolean),
    followUp: getContent('follow_up')
  };
}; 