# RAE Configuration Profiles

Pre-defined configuration profiles for different use cases and workload types.

## Available Profiles

### 1. **Balanced Default** (`profile_balanced_default.yaml`)
**Recommended starting point for most users**

- **Use case:** General purpose applications
- **Latency:** ~1 second
- **Quality:** 92% accuracy
- **Cost:** Moderate
- **Best for:** First-time users, standard APIs, knowledge management

### 2. **Real-time Performance** (`profile_realtime.yaml`)
**Ultra-low latency for interactive applications**

- **Use case:** Live chat, real-time Q&A
- **Latency:** <100ms
- **Quality:** 85-90% accuracy
- **Cost:** Moderate (caching overhead)
- **Best for:** Interactive demos, live chat assistants, low-latency APIs

### 3. **Research Grade** (`profile_research.yaml`)
**Maximum quality for academic and deep analysis**

- **Use case:** Research, complex problem solving
- **Latency:** 1-5 seconds
- **Quality:** 98%+ accuracy
- **Cost:** High
- **Best for:** Academic research, thorough investigations, high-stakes decisions

### 4. **Enterprise Safe** (`profile_enterprise_safe.yaml`)
**Production-grade reliability**

- **Use case:** Business applications, customer-facing systems
- **Latency:** <1 second
- **Quality:** 95%+ accuracy
- **Cost:** Moderate
- **Best for:** Production APIs, enterprise workflows, reliable operations

### 5. **Fast Development** (`profile_fast_dev.yaml`)
**Speed and iteration velocity**

- **Use case:** Development, testing, prototyping
- **Latency:** <500ms
- **Quality:** 90%+ accuracy
- **Cost:** Low
- **Best for:** Local development, rapid prototyping, testing and debugging

## How to Use Profiles

### Loading a Profile

```python
import yaml

with open("profiles/profile_balanced_default.yaml") as f:
    config = yaml.safe_load(f)

# Use config parameters
math_level = config["parameters"]["math_level"]
batch_size = config["parameters"]["batch_size"]
```

### Customizing a Profile

Start with the closest profile and override specific parameters:

```yaml
# my_custom_profile.yaml
base: profile_balanced_default.yaml

# Override specific parameters
parameters:
  math_level: 3  # Increase reasoning
  batch_size: 100  # Larger batches

memory_config:
  context_window: 10000  # Larger context
```

## Profile Selection Guide

| Your Priority | Recommended Profile |
|--------------|-------------------|
| **Speed** (latency critical) | Real-time Performance |
| **Quality** (accuracy critical) | Research Grade |
| **Reliability** (production) | Enterprise Safe |
| **Cost** (budget conscious) | Fast Development |
| **Unsure** (good starting point) | Balanced Default |

## Performance Comparison

| Profile | Latency | Quality | Cost | Use Case |
|---------|---------|---------|------|----------|
| Real-time | ★★★★★ | ★★★☆☆ | ★★★☆☆ | Interactive |
| Research | ★☆☆☆☆ | ★★★★★ | ★★★★★ | Analysis |
| Enterprise | ★★★★☆ | ★★★★★ | ★★★☆☆ | Production |
| Fast Dev | ★★★★☆ | ★★★★☆ | ★★☆☆☆ | Development |
| Balanced | ★★★☆☆ | ★★★★☆ | ★★★☆☆ | General |

## Creating Custom Profiles

See `.ai-templates/profile_template.yaml` for a template to create your own profiles.

## Testing Profiles

Use the ORB benchmark to validate profile performance:

```bash
python -m benchmarking.nine_five_benchmarks.runner --benchmarks ORB
```

Or use the auto-tuner to find optimal configurations:

```bash
python benchmarking/scripts/orb_autotuner.py
```

---

**Version:** 1.0.0
**Last Updated:** 2025-12-12
