# RAE Memory Node.js SDK Design Document

This document outlines the design for a lightweight Node.js SDK for the RAE (Reflective Agentic Memory) Engine. The goal is to provide an idiomatic and easy-to-use interface for Node.js developers to interact with the RAE Memory API.

## Core Principles

*   **Simplicity**: Easy to understand and use, with minimal boilerplate.
*   **Idiomatic Node.js**: Follows common Node.js patterns (e.g., async/await, Promises).
*   **Configurable**: Flexible configuration options (environment variables, constructor).
*   **Type-safe (TypeScript)**: Designed with TypeScript in mind for better developer experience.

## Architecture

The SDK will consist of a single main class, `RaeMemoryClient`, which encapsulates all API interactions.

### `RaeMemoryClient` Class

```typescript
import { RaeMemoryClientConfig } from './config';
import {
  MemoryLayer,
  MemoryRecord,
  ScoredMemoryRecord,
  StoreMemoryRequest,
  StoreMemoryResponse,
  QueryMemoryRequest,
  QueryMemoryResponse,
  DeleteMemoryResponse,
} from './models';

class RaeMemoryClient {
  private config: RaeMemoryClientConfig;
  private baseUrl: string;
  private headers: { [key: string]: string };

  constructor(options?: Partial<RaeMemoryClientConfig>) {
    this.config = { ...RaeMemoryClientConfig.fromEnv(), ...options }; // Load from env, then override
    this.baseUrl = this.config.raeApiUrl;
    this.headers = {
      'X-API-Key': this.config.raeApiKey,
      'X-Tenant-Id': this.config.raeTenantId,
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    method: 'GET' | 'POST' | 'DELETE',
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `RAE API Error (${response.status} ${response.statusText}): ${errorText}`
      );
    }
    return response.json() as Promise<T>;
  }

  async store(memory: StoreMemoryRequest): Promise<StoreMemoryResponse> {
    return this.request<StoreMemoryResponse>('POST', '/memory/store', memory);
  }

  async query(request: QueryMemoryRequest): Promise<QueryMemoryResponse> {
    return this.request<QueryMemoryResponse>('POST', '/memory/query', request);
  }

  async delete(memoryId: string): Promise<DeleteMemoryResponse> {
    return this.request<DeleteMemoryResponse>(
      'DELETE',
      `/memory/delete?memory_id=${memoryId}`
    );
  }

  // Stubs for future endpoints
  async evaluate(): Promise<any> {
    console.warn('Evaluate endpoint is a stub.');
    return this.request('POST', '/memory/evaluate');
  }

  async reflect(): Promise<any> {
    console.warn('Reflect endpoint is a stub.');
    return this.request('POST', '/memory/reflect');
  }

  async getTags(): Promise<string[]> {
    console.warn('Get tags endpoint is a stub.');
    return this.request('GET', '/memory/tags');
  }
}
```

### Configuration (`config.ts`)

```typescript
export interface RaeMemoryClientConfig {
  raeApiUrl: string;
  raeApiKey: string;
  raeTenantId: string;
}

export const RaeMemoryClientConfig = {
  fromEnv: (): RaeMemoryClientConfig => ({
    raeApiUrl: process.env.RAE_API_URL || 'http://localhost:8000',
    raeApiKey: process.env.RAE_API_KEY || 'your-rae-api-key',
    raeTenantId: process.env.RAE_TENANT_ID || 'default-tenant',
  }),
};
```

### Models (`models.ts`)

The models will be TypeScript interfaces mirroring the Pydantic models from the RAE API.

```typescript
export enum MemoryLayer {
  Stm = 'stm',
  Ltm = 'ltm',
  Rm = 'rm',
}

export interface MemoryRecord {
  id: string;
  content: string;
  source?: string;
  importance?: number;
  layer?: MemoryLayer;
  tags?: string[];
  timestamp?: string; // ISO 8601 string
  lastAccessedAt?: string; // ISO 8601 string
  usageCount?: number;
}

export interface ScoredMemoryRecord extends MemoryRecord {
  score: number;
}

export interface StoreMemoryRequest {
  content: string;
  source?: string;
  importance?: number;
  layer?: MemoryLayer;
  tags?: string[];
  timestamp?: string;
}

export interface StoreMemoryResponse {
  id: string;
  message: string;
}

export interface QueryMemoryRequest {
  queryText: string;
  k?: number;
  filters?: { [key: string]: any };
}

export interface QueryMemoryResponse {
  results: ScoredMemoryRecord[];
}

export interface DeleteMemoryResponse {
  message: string;
}
```

## Error Handling

The `request` method will throw an `Error` on non-2xx HTTP responses, including the status code and response text.

## Dependencies

*   `node-fetch` (if targeting older Node.js versions without native `fetch`)
*   `typescript` (for type definitions and compilation)

## Usage Example

```typescript
import { RaeMemoryClient, StoreMemoryRequest, MemoryLayer } from '@rae/memory-sdk';

async function main() {
  const client = new RaeMemoryClient({
    raeApiKey: 'my-secret-key',
    raeTenantId: 'my-project',
  });

  // Store a memory
  const newMemory: StoreMemoryRequest = {
    content: 'Node.js is a JavaScript runtime built on Chrome\'s V8 JavaScript engine.',
    source: 'nodejs-docs',
    layer: MemoryLayer.Ltm,
    tags: ['nodejs', 'javascript', 'runtime'],
  };
  try {
    const response = await client.store(newMemory);
    console.log(`Memory stored: ${response.id}`);
  } catch (error) {
    console.error('Error storing memory:', error.message);
  }

  // Query memories
  try {
    const queryResults = await client.query({ queryText: 'What is Node.js?', k: 2 });
    console.log('\nQuery Results:');
    queryResults.results.forEach((result) => {
      console.log(`- ID: ${result.id}, Score: ${result.score.toFixed(2)}, Content: ${result.content.substring(0, 50)}...`);
    });
  } catch (error) {
    console.error('Error querying memories:', error.message);
  }
}

main();
```
