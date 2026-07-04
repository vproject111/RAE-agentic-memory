import os

from llama_index import Document, ServiceContext, StorageContext, VectorStoreIndex
from llama_index.llms import OpenAI  # Or any other LLM
from rae_llamaindex_store import RAEVectorStore


def main():
    # 1. Configuration
    RAE_API_URL = os.environ.get("RAE_API_URL", "http://localhost:8000")
    RAE_TENANT_ID = os.environ.get("RAE_TENANT_ID", "llamaindex-example-tenant")
    RAE_API_KEY = os.environ.get("RAE_API_KEY", "test-key")

    if not RAE_API_KEY:
        print(
            "RAE_API_KEY environment variable not set. Please set it to your API key."
        )
        return

    print("--- LlamaIndex RAE Vector Store Example ---")

    # 2. Initialize the RAEVectorStore
    try:
        vector_store = RAEVectorStore(
            tenant_id=RAE_TENANT_ID, api_key=RAE_API_KEY, base_url=RAE_API_URL
        )
        print("RAEVectorStore initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize RAEVectorStore: {e}")
        return

    # 3. Create a StorageContext and ServiceContext
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # You can configure your LLM here. We'll use a placeholder for this example if no key is set.
    llm = None
    if os.environ.get("OPENAI_API_KEY"):
        llm = OpenAI(model="gpt-3.5-turbo")
        print("Using OpenAI LLM.")
    else:
        print(
            "OPENAI_API_KEY not set. Query engine will use retriever only, not an LLM."
        )

    service_context = ServiceContext.from_defaults(llm=llm)

    # 4. Create an index
    # This will automatically use our RAEVectorStore
    index = VectorStoreIndex.from_documents(
        [],  # Start with an empty index, we'll add docs directly
        storage_context=storage_context,
        service_context=service_context,
    )

    # 5. Add documents to the index (and thus to RAE)
    print("\nAdding documents to RAE via LlamaIndex...")
    documents = [
        Document(
            text="The project codenamed 'Phoenix' is scheduled for release next month.",
            metadata={"source": "meeting-notes.txt"},
        ),
        Document(
            text="The budget for project 'Phoenix' has been increased by 20%.",
            metadata={"source": "budget-approval.eml"},
        ),
    ]
    index.insert_nodes(documents)
    print("Documents added successfully.")

    # 6. Create a query engine and query
    query_engine = index.as_query_engine()
    query = "What is the status of project Phoenix?"

    print(f"\nQuerying the index with: '{query}'")
    response = query_engine.query(query)

    print("\n--- LlamaIndex Response ---")
    print(response)
    print("--------------------------")

    # You can see the retrieved nodes
    print("\n--- Retrieved Source Nodes ---")
    for node in response.source_nodes:
        print(
            f"- Score: {node.score:.4f}, Source: {node.metadata.get('source')}, Text: '{node.text[:50]}...'"
        )
    print("----------------------------")


if __name__ == "__main__":
    main()
