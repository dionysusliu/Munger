>       pairs,

# BR algorithm (Best Response)

The **BR algorithm** (short for **Best Response algorithm**) is a fundamental method in game theory used to identify strategies that maximize a player’s payoff given the strategies chosen by other players. It is a core building block for solving static and dynamic games, and it underpins the concept of [[Nash Equilibrium]].

## Definition

In a game with \(n\) players, each player has a set of possible strategies. A **best response** for a player is a strategy (or set of strategies) that yields the highest possible payoff for that player, assuming the other players’ strategies are fixed. The BR algorithm iteratively computes these best responses – often for every player – to find stable outcomes where no player wants to unilaterally deviate.

More formally:  
For player \(i\), given the strategies \(s_{-i}\) of all other players, a strategy \(s_i^*\) is a best response if  

\[
u_i(s_i^*, s_{-i}) \ge u_i(s_i, s_{-i}) \quad \forall s_i \in S_i
\]

where \(u_i\) is player \(i\)’s utility function and \(S_i\) is the set of available strategies.

The BR algorithm can be used in two main ways:
- **Fictitious play**: Players track the empirical frequency of opponents’ strategies and choose their best response accordingly.
- **Best-response dynamics**: Starting from an arbitrary strategy profile, players take turns updating to their current best response until convergence (or cycling) occurs.

## Examples

### Example 1: Matching Pennies
Two players, each chooses Heads (H) or Tails (T). Player A wins if both choose the same side; Player B wins if they differ. The payoff matrix (A,B) is:

| A \ B | H      | T      |
|-------|--------|--------|
| H     | (1, -1)| (-1, 1)|
| T     | (-1, 1)| (1, -1)|

- If B plays H, A’s best response is H (payoff 1 > -1).
- If B plays T, A’s best response is T.
- Similarly, B’s best response depends on A’s choice.

No pure strategy is a best response to itself; the only (mixed) Nash equilibrium involves each player randomizing 50-50. The BR algorithm would alternately update strategies and never converge to a pure profile.

### Example 2: Coordination Game
Two drivers choose left (L) or right (R). They both prefer driving on the same side.

| A \ B | L      | R      |
|-------|--------|--------|
| L     | (1, 1) | (0, 0) |
| R     | (0, 0) | (1, 1) |

- If B plays L, A’s best response is L.
- If B plays R, A’s best response is R.
- The BR algorithm converges quickly to either (L,L) or (R,R) depending on the starting point. Both are pure Nash equilibria.

## Related Mental Models

- [[Nash Equilibrium]] – The endpoint of the BR algorithm when all players are simultaneously playing a best response.
- [[Dominant Strategy]] – A strategy that is a best response no matter what others do.
- [[Prisoner’s Dilemma]] – A classic game where individual best responses lead to a collectively worse outcome.
- [[Fictitious Play]] – A learning algorithm where agents use the BR algorithm with belief tracking.
- [[Best-Response Dynamics]] – The process of iteratively updating strategies to best responses.
- [[Minimax Theorem]] – In zero-sum games, the BR algorithm connects to optimal mixed strategies.
- [[Evolutionary Game Theory]] – The BR algorithm is analogous to replicator dynamics in certain settings.

## Applications

- **Economics**: Computing market equilibria, auction design.
- **Computer Science**: Multi-agent reinforcement learning, adversarial search.
- **Biology**: Animal behavior modeling (e.g., hawk-dove games).
- **Artificial Intelligence**: Self-play in games (e.g., AlphaGo uses best-response approximations).

## Limitations

- The BR algorithm may cycle in non‑zero‑sum games without a pure Nash equilibrium.
- It assumes players know others’ strategies perfectly (or have accurate beliefs).
- Multiple equilibria can exist; the algorithm’s outcome is path-dependent.

## See Also

- [[Strategy Space]]
- [[Payoff Matrix]]
- [[Replicator Dynamics]]
- [[Minimax Algorithm]]
- [[Game Theory]]