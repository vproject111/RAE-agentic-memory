# Architectural Decision: Security Enforcement for RAE-Mobile & Mesh

**Date:** 2026-01-17
**Status:** Accepted
**Context:** RAE-Mobile, RAE-Windows, RAE-Mesh Vision

## 1. Context & Vision
The long-term vision for RAE includes running on edge devices (Mobile, Windows) and forming a Mesh network where users can exchange memories. A key feature of RAE-Mobile is the ability to ingest private communications (private chats with LLMs, emails) to extract "non-obvious ideas" and patterns via the Reflective Layer.

## 2. The Problem
Directly ingesting private data into the system poses a catastrophic privacy risk in a Mesh/Distributed environment. If raw private emails or chats were stored as standard memories, they could be inadvertently shared during a Mesh sync or leaked if a device file is compromised.

## 3. The Decision: Strict Enforcement of `info_class`
We have implemented strict blocking logic in `RAECoreService` to enforce ISO 27000 information classes.

### Mechanisms:
1.  **Restricted Containment:** Data classified as `RESTRICTED` (raw emails, private chat logs, PII) is **hard-blocked** from entering `Episodic`, `Semantic`, or `Reflective` layers. It can ONLY exist in the `Working` layer (short-term, encrypted, RAM-based/transient).
2.  **Idea Extraction Pipeline:**
    *   **Input:** Raw private data -> `Working Layer` (RESTRICTED).
    *   **Process:** Reflection Engine analyzes the restricted content in the Working layer.
    *   **Output:** The Engine extracts the *abstract idea* or *insight* (sanitized of PII/Secrets) and saves this new object to `Reflective/Semantic` layers as `INTERNAL` or `CONFIDENTIAL`.
3.  **Mesh Safety:** Synchronization protocols will be configured to strictly ignore `RESTRICTED` data and require explicit user consent for `CONFIDENTIAL` data.

## 4. Justification (Responsible Open Source)
As an Open Source project, we must prioritize user safety by default ("Secure by Design").
*   **Safety Rails:** This architecture prevents the accidental "leaking" of user secrets, even if the user misconfigures the upper layers.
*   **Trust:** Users will only consent to connecting RAE-Mobile to their private lives if they are mathematically guaranteed that raw logs cannot leave the transient processing loop.

## 5. Conclusion
The implemented security controls are not "restrictions" but **enablers**. They allow the "Idea Extraction" feature to exist safely, making RAE-Mesh a viable product that respects user privacy.
