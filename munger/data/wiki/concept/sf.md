# Conversation Active Threshold

## Definition

The **Conversation Active Threshold** is the boundary condition used to determine whether a dialogue between two or more participants is considered ongoing (active) rather than finished or dormant. This threshold is typically defined in terms of time elapsed without a new turn, number of exchanged utterances, or a combination of contextual signals (e.g., topic continuity or participant attention). It is a critical parameter in conversational systems, user interfaces, and cognitive models where the state of a conversation must be automatically inferred.

## Examples

- **Chat applications** – A 5‑minute idle period after the last message may mark the conversation as “inactive”, triggering a warning or automatic archival.
- **Voice assistants** – The system stays in “listening mode” for 30 seconds of silence before assuming the conversation has ended.
- **Collaborative editing tools** – A conversation thread is considered active if new comments have been added within the last hour; otherwise it appears collapsed.
- **LLM context windows** – A threshold of 10 consecutive user messages without a system prompt may reset the conversation’s active memory, discarding older turns.

## Related Mental Models

- [[Context Window]] – The limited span of information a system retains, often tied to the active threshold.
- [[Session Timeout]] – A broader security or UX concept that defines when a session (possibly including conversations) ends.
- [[Working Memory]] – In cognitive science, the limited capacity to hold and manipulate active information, analogous to conversation thresholds.
- [[Attention Span]] – Human limitation that influences natural conversation durations and the design of artificial thresholds.
- [[Garbage Collection (Memory)]] – How inactive data is freed, similar to how conversations beyond the threshold are pruned.
- [[Turn-Taking]] – The rhythmic exchange that defines active conversation, and the threshold can be seen as an extended pause in this model.
- [[Forgetting Curve]] – Psychological model predicting memory decay over time, which informs how quickly a conversation should be considered “closed”.
- [[Idle Detection]] – Technical pattern used in interfaces to infer user disengagement, directly applies to conversation activity thresholds.

## Applications

| Domain | Typical threshold | Purpose |
|--------|-------------------|---------|
| Instant messaging | 1–5 minutes | Reduce visual clutter, save resources |
| Customer support chat | 10–15 minutes | Escalate to email when inactive |
| AI conversation agents | Variable (e.g., 3 turns or 30 s) | Manage context length, avoid confusion |
| Group chat (team tools) | 1 hour – 1 day | Archive threads automatically |

## Design Considerations

- **Too short** → Prematurely closes conversations, frustrates participants who pause to think.
- **Too long** → Wastes resources (memory, UI space), retains stale context.
- **Dynamic thresholds** can adapt based on conversation history, participant role, or topic complexity.
- Combining multiple signals (idle time + content recency + user intent) yields more robust detection than a single value.

## See Also

- [[Conversation State Machine]]
- [[Response Timeout]]
- [[Cognitive Load & Conversation Modeling]]