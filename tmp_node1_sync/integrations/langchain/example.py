import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from rae_langchain_retriever import RAERetriever, _RAEAPIClient


# This is a placeholder for a real LangChain LLM
# You could use `langchain_openai.ChatOpenAI` or `langchain_google_genai.ChatGoogleGenerativeAI`
class FakeLLM:
    def invoke(self, prompt, *args, **kwargs):
        return f"This is a fake LLM response based on the prompt:\n---\n{prompt}"


def main():
    # 1. Configuration
    # These should be set as environment variables for security
    RAE_API_URL = os.environ.get("RAE_API_URL", "http://localhost:8000")
    RAE_TENANT_ID = os.environ.get("RAE_TENANT_ID", "langchain-example-tenant")
    RAE_API_KEY = os.environ.get(
        "RAE_API_KEY", "test-key"
    )  # Use the key you've configured in your API

    if not RAE_API_KEY:
        print(
            "RAE_API_KEY environment variable not set. Please set it to your API key."
        )
        return

    # 2. Initialize the RAE API client and retriever
    api_client = _RAEAPIClient(
        tenant_id=RAE_TENANT_ID, api_key=RAE_API_KEY, base_url=RAE_API_URL
    )
    retriever = RAERetriever(client=api_client, k=2)

    # 3. Define the RAG chain
    template = """
Answer the question based only on the following context:
{context}

Question: {question}
"""
    prompt = ChatPromptTemplate.from_template(template)

    # A simple fake LLM for demonstration purposes
    llm = FakeLLM()

    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 4. Run the chain
    print("--- RAG Chain Example ---")

    # First, let's store something in the memory so the retriever can find it.
    # We will do this manually with httpx for this example.
    import httpx

    print("Storing a memory in RAE...")
    store_payload = {
        "content": "The new password for the admin account is 'super-secret-password-123'.",
        "source": "internal-memo.txt",
        "project": "security-updates",
    }
    try:
        with httpx.Client() as client:
            client.post(
                f"{RAE_API_URL}/v1/memory/store",
                json=store_payload,
                headers={"X-API-Key": RAE_API_KEY, "X-Tenant-Id": RAE_TENANT_ID},
            ).raise_for_status()
        print("Memory stored successfully.")
    except Exception as e:
        print(
            f"Could not connect to or store memory in RAE API at {RAE_API_URL}. Is it running?"
        )
        print(f"Error: {e}")
        return

    # Now, query the RAG chain
    query = "What is the new password for the admin account?"
    print(f"\nQuerying the RAG chain with: '{query}'")

    response = rag_chain.invoke(query)

    print("\n--- RAG Chain Response ---")
    print(response)
    print("--------------------------")

    # You can also use the retriever directly
    print("\n--- Direct Retriever Usage ---")
    retrieved_docs = retriever.invoke(query)
    print(f"Retrieved {len(retrieved_docs)} documents:")
    for doc in retrieved_docs:
        print(
            f"- Source: {doc.metadata.get('source')}, Content: '{doc.page_content[:50]}...'"
        )
    print("----------------------------")


if __name__ == "__main__":
    main()
