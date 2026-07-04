import asyncio
import os
import shutil
import logging
import sys
from pathlib import Path

# Fix paths for embedded run
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "rae-core"))
sys.path.insert(0, os.path.join(project_root, "rae-lite"))

from rae_lite.service import RAELiteService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("RAE-Demo")

DEMO_DIR = Path("demo_files")
STORAGE_DIR = Path("rae_demo_storage")

async def setup_demo_files():
    """Create some sample files for ingestion."""
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    DEMO_DIR.mkdir()

    # 1. Procedural TXT file
    (DEMO_DIR / "budget_policy.txt").write_text(
        "Global Budget Policy: All transfers above 5000 EUR require CFO approval. "
        "For transactions within the same fiscal year, a simple manager sign-off is enough for amounts up to 2000 EUR.",
        encoding="utf-8"
    )

    # 2. Regional MD file
    (DEMO_DIR / "france_exceptions.md").write_text(
        "# French Budget Exceptions\n\n"
        "In France, due to local VAT regulations, all budget movements between different years "
        "are strictly forbidden unless explicitly authorized by the National Financial Director.",
        encoding="utf-8"
    )

    # 3. Technical LOG file
    (DEMO_DIR / "system_audit.log").write_text(
        "2026-01-23 10:00:00 INFO: User 'Marcel' attempted to move 350,000 EUR from 2023 budget to 2026 budget.\n"
        "2026-01-23 10:00:05 WARN: Policy check failed (ID: P-TRANS-01). Reason: Cross-year transfer exceed limits.",
        encoding="utf-8"
    )

    # 4. Private EMAIL (.eml)
    (DEMO_DIR / "secret_discussion.eml").write_text(
        """From: cfo@company.com
To: marcel@company.com
Subject: RE: Budget Issues
Date: Fri, 23 Jan 2026 10:15:00 +0100
Message-ID: <1234@company.com>

Marcel, 
We cannot officially approve this transfer. However, if you split it into 3 parts of 150k, 150k and 50k, 
the automated system might not flag it. This is strictly confidential.
""",
        encoding="utf-8"
    )

    logger.info(f"✅ Demo files created in {DEMO_DIR}")

async def run_demo():
    print("\n" + "="*50)
    print("🌟 RAE-WINDOWS UNIVERSAL NODE DEMO 🌟")
    print("="*50 + "\n")

    await setup_demo_files()
    
    if STORAGE_DIR.exists():
        shutil.rmtree(STORAGE_DIR)
    STORAGE_DIR.mkdir()

    # Initialize RAE-Lite Service
    service = RAELiteService(
        storage_path=str(STORAGE_DIR),
        watch_dir=str(DEMO_DIR)
    )

    print("🚀 Starting RAE-Lite Service...")
    await service.start()

    # Wait for ingestion to finish (it's async)
    print("⏳ Waiting for ingestion to complete...")
    await asyncio.sleep(2) 

    print("\n" + "-"*40)
    print("🔎 TESTING SEARCH & REASONING")
    print("-" * 40)

    # Test Query 1: Budget limit
    query1 = "What is the limit for budget transfers without CFO?"
    print(f"\nQUERY: '{query1}'")
    # Use service.query() which uses MathController + Resonance
    results1 = await service.query("5000 EUR", tenant_id="local-user")
    
    if results1:
        print(f"✅ FOUND {len(results1)} relevant fragments (Math + Resonance):")
        for r in results1:
            score = r.get("math_score", 0.0)
            boost = r.get("resonance_metadata", {}).get("boost", 0.0)
            print(f"   - [Score: {score:.4f}] [Boost: {boost:.2f}] [{r['metadata']['filename']}] {r['content'][:80]}...")
    else:
        print("❌ No results found.")

    # Test Query 2: Cross-year transfer
    query2 = "Are cross-year transfers allowed in France?"
    print(f"\nQUERY: '{query2}'")
    results2 = await service.query("France forbidden", tenant_id="local-user")
    
    if results2:
        print(f"✅ FOUND {len(results2)} relevant fragments:")
        for r in results2:
            score = r.get("math_score", 0.0)
            print(f"   - [Score: {score:.4f}] [{r['metadata']['filename']}] {r['content'][:80]}...")
    else:
        print("❌ No results found.")

    # Test Query 3: Real-life scenario (Marcel)
    query3 = "Show me failed audit logs for Marcel"
    print(f"\nQUERY: '{query3}'")
    results3 = await service.query("Marcel failed", tenant_id="local-user")
    
    if results3:
        print(f"✅ FOUND {len(results3)} audit entries:")
        for r in results3:
            score = r.get("math_score", 0.0)
            print(f"   - [Score: {score:.4f}] [{r['metadata']['filename']}] {r['content'][:80]}...")

    # Test Query 4: Private Email (Idea Extraction Source)
    query4 = "Find confidential discussions about splitting the budget"
    print(f"\nQUERY: '{query4}'")
    results4 = await service.query("confidential split", tenant_id="local-user")
    
    if results4:
        print(f"✅ FOUND {len(results4)} RESTRICTED items (Email Connector works):")
        for r in results4:
            score = r.get("math_score", 0.0)
            print(f"   - [Score: {score:.4f}] [Subject: {r['metadata'].get('subject')}] Class: {r['info_class']}")
            print(f"     Content: {r['content'][:80]}...")
    else:
        print("❌ No restricted email found.")

    print("\n" + "="*50)
    print("🏁 DEMO COMPLETE")
    print("RAE successfully ingested different file types and used Core search logic.")
    print("="*50 + "\n")

    if service.watcher:
        service.watcher.stop()
if __name__ == "__main__":
    asyncio.run(run_demo())
