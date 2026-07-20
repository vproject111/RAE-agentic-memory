from __future__ import annotations

import asyncio
from datetime import timezone

import git

from rae_core.interfaces.adapter import (
    IKnowledgeAdapter,
    RetrievalContext,
    RetrievedKnowledge,
    compute_content_checksum,
)
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType


class GitRuntimeAdapter(IKnowledgeAdapter[None]):
    adapter_id = "git-repository-runtime"
    source_type = KnowledgeSourceType.GIT

    def __init__(self, repo_path: str) -> None:
        self.repo = git.Repo(repo_path, search_parent_directories=False)

    def _retrieve_sync(self, limit: int) -> list[RetrievedKnowledge]:
        try:
            head_commit = self.repo.head.commit
            timestamp = head_commit.committed_datetime
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            content = (
                f"HEAD commit: {head_commit.hexsha}\n"
                f"Author: {head_commit.author}\n"
                f"Message: {head_commit.message.strip()}\n"
            )

            return [
                RetrievedKnowledge(
                    evidence_id=f"git:{head_commit.hexsha}",
                    content=content,
                    source_ref=f"git://{self.repo.working_dir}#HEAD",
                    source_type=KnowledgeSourceType.GIT,
                    authority_level=AuthorityLevel.OBSERVED,
                    score=0.95,
                    observed_at=timestamp,
                    source_version=head_commit.hexsha,
                    checksum=compute_content_checksum(content),
                    metadata={
                        "repository": self.repo.working_dir,
                        "commit_sha": head_commit.hexsha,
                    },
                )
            ][:limit]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Git retrieval failed",
                extra={
                    "error": str(exc),
                    "repo_path": self.repo.working_dir if self.repo else "unknown"
                }
            )
            return []

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[None],
    ) -> list[RetrievedKnowledge]:
        return await asyncio.to_thread(self._retrieve_sync, limit)
