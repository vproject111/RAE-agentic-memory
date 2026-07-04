# RAE Memory Go SDK Design Document

This document outlines the design for a lightweight Go SDK for the RAE (Reflective Agentic Memory) Engine. The goal is to provide a performant and idiomatic Go interface for developers to interact with the RAE Memory API.

## Core Principles

*   **Simplicity**: Easy to understand and use, with minimal external dependencies.
*   **Idiomatic Go**: Follows standard Go conventions (e.g., error handling, struct tags, context).
*   **Configurable**: Flexible configuration options (environment variables, constructor).
*   **Concurrency-safe**: Designed with concurrency in mind where applicable.

## Architecture

The SDK will consist of a `Client` struct that holds the configuration and an HTTP client. It will expose methods for each API endpoint.

### `Client` Struct

```go
package raememory

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

const (
	defaultAPIURL  = "http://localhost:8000"
	defaultTenantID = "default-tenant"
)

// Config holds the configuration for the RAE Memory Client.
type Config struct {
	APIURL  string
	APIKey  string
	TenantID string
}

// NewConfigFromEnv creates a Config from environment variables.
func NewConfigFromEnv() *Config {
	cfg := &Config{
		APIURL:  os.Getenv("RAE_API_URL"),
		APIKey:  os.Getenv("RAE_API_KEY"),
		TenantID: os.Getenv("RAE_TENANT_ID"),
	}
	if cfg.APIURL == "" {
		cfg.APIURL = defaultAPIURL
	}
	if cfg.TenantID == "" {
		cfg.TenantID = defaultTenantID
	}
	return cfg
}

// Client is the RAE Memory API client.
type Client struct {
	cfg        *Config
	httpClient *http.Client
}

// NewClient creates a new RAE Memory API client.
func NewClient(cfg *Config) *Client {
	if cfg == nil {
		cfg = NewConfigFromEnv()
	}
	return &Client{
		cfg:        cfg,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) doRequest(ctx context.Context, method, path string, requestBody interface{}) ([]byte, error) {
	url := fmt.Sprintf("%s%s", c.cfg.APIURL, path)
	
	var reqBody io.Reader
	if requestBody != nil {
		jsonBody, err := json.Marshal(requestBody)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	req, err := http.NewRequestWithContext(ctx, method, url, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", c.cfg.APIKey)
	req.Header.Set("X-Tenant-Id", c.cfg.TenantID)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("RAE API Error (%d %s): %s", resp.StatusCode, resp.Status, string(respBody))
	}

	return respBody, nil
}

// StoreMemory stores a new memory record.
func (c *Client) StoreMemory(ctx context.Context, memory *StoreMemoryRequest) (*StoreMemoryResponse, error) {
	respBody, err := c.doRequest(ctx, "POST", "/memory/store", memory)
	if err != nil {
		return nil, err
	}
	var response StoreMemoryResponse
	if err := json.Unmarshal(respBody, &response); err != nil {
		return nil, fmt.Errorf("failed to unmarshal StoreMemoryResponse: %w", err)
	}
	return &response, nil
}

// QueryMemory queries the memory for relevant records.
func (c *Client) QueryMemory(ctx context.Context, query *QueryMemoryRequest) (*QueryMemoryResponse, error) {
	respBody, err := c.doRequest(ctx, "POST", "/memory/query", query)
	if err != nil {
		return nil, err
	}
	var response QueryMemoryResponse
	if err := json.Unmarshal(respBody, &response); err != nil {
		return nil, fmt.Errorf("failed to unmarshal QueryMemoryResponse: %w", err)
	}
	return &response, nil
}

// DeleteMemory deletes a memory record by its ID.
func (c *Client) DeleteMemory(ctx context.Context, memoryID string) (*DeleteMemoryResponse, error) {
	respBody, err := c.doRequest(ctx, "DELETE", fmt.Sprintf("/memory/delete?memory_id=%s", memoryID), nil)
	if err != nil {
		return nil, err
	}
	var response DeleteMemoryResponse
	if err := json.Unmarshal(respBody, &response); err != nil {
		return nil, fmt.Errorf("failed to unmarshal DeleteMemoryResponse: %w", err)
	}
	return &response, nil
}

// EvaluateMemory (Stub) evaluates memory performance.
func (c *Client) EvaluateMemory(ctx context.Context) (interface{}, error) {
	fmt.Println("Evaluate endpoint is a stub.")
	return c.doRequest(ctx, "POST", "/memory/evaluate", nil)
}

// ReflectOnMemories (Stub) triggers memory reflection.
func (c *Client) ReflectOnMemories(ctx context.Context) (interface{}, error) {
	fmt.Println("Reflect endpoint is a stub.")
	return c.doRequest(ctx, "POST", "/memory/reflect", nil)
}

// GetTags (Stub) retrieves all available tags.
func (c *Client) GetTags(ctx context.Context) (interface{}, error) {
	fmt.Println("Get tags endpoint is a stub.")
	return c.doRequest(ctx, "GET", "/memory/tags", nil)
}
```

### Models (`models.go`)

The models will be Go structs mirroring the Pydantic models from the RAE API, using `json` tags for marshaling/unmarshaling.

```go
package raememory

import "time"

// MemoryLayer defines the different layers of memory.
type MemoryLayer string

const (
	MemoryLayerSTM MemoryLayer = "stm"
	MemoryLayerLTM MemoryLayer = "ltm"
	MemoryLayerRM  MemoryLayer = "rm"
)

// MemoryRecord represents a standard memory record.
type MemoryRecord struct {
	ID            string      `json:"id"`
	Content       string      `json:"content"`
	Source        *string     `json:"source,omitempty"`
	Importance    *float32    `json:"importance,omitempty"`
	Layer         *MemoryLayer `json:"layer,omitempty"`
	Tags          *[]string   `json:"tags,omitempty"`
	Timestamp     *time.Time  `json:"timestamp,omitempty"`
	LastAccessedAt *time.Time  `json:"last_accessed_at,omitempty"`
	UsageCount    *int        `json:"usage_count,omitempty"`
}

// ScoredMemoryRecord is a MemoryRecord with an additional score.
type ScoredMemoryRecord struct {
	MemoryRecord
	Score float32 `json:"score"`
}

// StoreMemoryRequest is the request body for storing a new memory.
type StoreMemoryRequest struct {
	Content    string      `json:"content"`
	Source     *string     `json:"source,omitempty"`
	Importance *float32    `json:"importance,omitempty"`
	Layer      *MemoryLayer `json:"layer,omitempty"`
	Tags       *[]string   `json:"tags,omitempty"`
	Timestamp  *time.Time  `json:"timestamp,omitempty"`
}

// StoreMemoryResponse is the response for storing a new memory.
type StoreMemoryResponse struct {
	ID      string `json:"id"`
	Message string `json:"message"`
}

// QueryMemoryRequest is the request body for querying memories.
type QueryMemoryRequest struct {
	QueryText string                 `json:"query_text"`
	K         *int                   `json:"k,omitempty"`
	Filters   *map[string]interface{} `json:"filters,omitempty"`
}

// QueryMemoryResponse is the response for querying memories.
type QueryMemoryResponse struct {
	Results []ScoredMemoryRecord `json:"results"`
}

// DeleteMemoryResponse is the response for deleting a memory.
type DeleteMemoryResponse struct {
	Message string `json:"message"`
}
```

## Error Handling

The `doRequest` method will return a Go `error` for network issues or non-2xx HTTP responses. The error message will include the HTTP status code and response body.

## Dependencies

*   Standard Go library (`net/http`, `encoding/json`, `context`, `os`, `time`).

## Usage Example

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"your_module_path/raememory" // Replace with actual module path
)

func main() {
	cfg := raememory.NewConfigFromEnv()
	cfg.APIKey = "your-secret-key" // Override from env if needed
	cfg.TenantID = "my-project"

	client := raememory.NewClient(cfg)
	ctx := context.Background()

	// Store a memory
	content := "Go is a statically typed, compiled programming language designed at Google."
	source := "go-docs"
	layer := raememory.MemoryLayerLTM
	importance := float32(0.7)
	tags := []string{"go", "programming", "language"}
	timestamp := time.Now()

	storeReq := &raememory.StoreMemoryRequest{
		Content:    content,
		Source:     &source,
		Importance: &importance,
		Layer:      &layer,
		Tags:       &tags,
		Timestamp:  &timestamp,
	}

	storeResp, err := client.StoreMemory(ctx, storeReq)
	if err != nil {
		log.Fatalf("Error storing memory: %v", err)
	}
	fmt.Printf("Memory stored: %s\n", storeResp.ID)

	// Query memories
	queryText := "What is Go?"
	k := 2
	queryReq := &raememory.QueryMemoryRequest{
		QueryText: queryText,
		K:         &k,
	}

	queryResp, err := client.QueryMemory(ctx, queryReq)
	if err != nil {
		log.Fatalf("Error querying memories: %v", err)
	}
	fmt.Println("\nQuery Results:")
	for _, result := range queryResp.Results {
		fmt.Printf("- ID: %s, Score: %.2f, Content: %s...\n", result.ID, result.Score, result.Content[:50])
	}

	// Delete a memory (example)
	// memoryToDeleteID := "..."
	// deleteResp, err := client.DeleteMemory(ctx, memoryToDeleteID)
	// if err != nil {
	// 	log.Fatalf("Error deleting memory: %v", err)
	// }
	// fmt.Printf("\nMemory deleted: %s\n", deleteResp.Message)
}
```
