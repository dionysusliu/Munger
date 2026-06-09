> estion con

# FQ Gateways

## Overview

**FQ Gateways** is a mental model that describes how information, decisions, or resources must pass through specific controlled access points (gateways) that filter, transform, or regulate flow based on **F**requency and **Q**uality thresholds. The "FQ" can refer to Frequency-Quality, Flow-Quantity, or Function-Question, depending on the domain of application.

At its core, the model posits that **gateways** act as selective bottlenecks that determine what passes through based on criteria related to how often something occurs (frequency) and how well it meets standards (quality). Understanding these gateways helps in optimizing systems, improving decision-making, and identifying leverage points for change.

## Key Components

### 1. Gateway
A **gateway** is a checkpoint or filter that controls the transition of entities (information, people, resources, decisions) from one state or system to another. Gateways can be:
- **Physical** (e.g., a security checkpoint)
- **Logical** (e.g., an approval workflow)
- **Cognitive** (e.g., a mental heuristic)
- **Systemic** (e.g., an API rate limiter)

### 2. Frequency (F)
The **frequency** dimension refers to how often an entity attempts to pass through the gateway. This includes:
- **Rate** – number of attempts per unit time
- **Pattern** – periodic, burst, or random arrival
- **Volume** – total count in a given period

### 3. Quality (Q)
The **quality** dimension refers to the attributes or standards an entity must meet to pass through. This includes:
- **Threshold** – minimum acceptable level
- **Completeness** – having all required components
- **Relevance** – alignment with gateway purpose
- **Validity** – correctness or authenticity

## The Gateway Function

The FQ Gateway model can be expressed as:

**Pass = f(F, Q) when F ≥ F₀ AND Q ≥ Q₀**

Where:
- F₀ = frequency threshold
- Q₀ = quality threshold
- Both conditions must be met for passage

## Examples

### Example 1: Job Application Process
- **Gateway**: Resume screening
- **Frequency**: Number of applications received (e.g., 500/week)
- **Quality**: Minimum qualifications, experience level, skill match
- **Outcome**: Only applications meeting both frequency (submitted during open window) and quality (meets requirements) proceed to interview

### Example 2: Content Moderation
- **Gateway**: Algorithmic filter
- **Frequency**: Posts per user per hour (rate limiting)
- **Quality**: Content scoring against policy guidelines
- **Outcome**: High-frequency low-quality posts are blocked; low-frequency high-quality posts are approved

### Example 3: Cognitive Decision Gate
- **Gateway**: Your attention filter
- **Frequency**: How often a thought or distraction appears
- **Quality**: Relevance to current goal
- **Outcome**: Only thoughts that appear infrequently but are highly relevant get processed deeply

## Applications

### System Design
Use FQ Gateways to:
- Design efficient [[API Rate Limiting]] systems
- Build [[Queue Management]] systems
- Implement [[Spam Filtering]] algorithms
- Create [[Approval Workflows]]

### Personal Productivity
Apply the model to:
- [[Attention Management]] – filter tasks by frequency of interruption and quality of impact
- [[Decision Fatigue]] – reduce decisions by setting quality thresholds higher for low-frequency choices
- [[Information Diet]] – regulate information intake through frequency and quality gates

### Organizational Management
Leverage in:
- [[Hiring Pipelines]] – screen candidates effectively
- [[Meeting Cadence]] – determine meeting frequency based on quality of outcomes
- [[Innovation Funnels]] – filter ideas by how often they arise and how viable they are

## Related Mental Models

- [[Bottleneck Analysis]] – identifies the slowest gateway in a system
- [[Pareto Principle]] – often 20% of inputs (high quality, appropriate frequency) produce 80% of outputs
- [[Diminishing Returns]] – beyond optimal frequency, quality degrades
- [[Filter Bubbles]] – when gateways become too restrictive on frequency or quality

## Limitations

- **Oversimplification** – Real systems often have multiple interacting gateways
- **Dynamic Thresholds** – F₀ and Q₀ may change over time or context
- **Subjectivity** – Quality is often difficult to measure objectively
- **Gaming** – Entities may learn to manipulate frequency or perceived quality to bypass gates

## See Also

- [[Gatekeeper Fallacy]]
- [[Signal vs Noise]]
- [[Threshold Effects]]
- [[Critical Mass]]

---

*Created for the Mental Model Wiki. Last updated: 2025.*