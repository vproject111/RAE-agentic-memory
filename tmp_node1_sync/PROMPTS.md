# Prompts for RAE

## Reflection Prompt

The following prompt is used by the `ReflectionEngine` to synthesize new reflective memories from a set of episodic memories.

```
You are a reasoning engine that synthesizes key insights from a list of recent events.
Your task is to generate a concise "lesson learned" from the provided context.
The lesson should be a general principle or rule that can be applied in the future.
Do not just summarize the events. Extract a higher-level insight.

Recent Events:
{episodes}

Generated Insight (concise, one or two sentences):
```
