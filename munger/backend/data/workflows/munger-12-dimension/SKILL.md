---
name: munger-12-dimension
version: "1.0"
description: >
  Charlie Munger's complete 12-dimension thinking framework analysis.
  Applies all 12 Munger analytical dimensions to source material:
  Source, Claim, Concept, Model, Mechanism, Incentive, Psychology,
  Dual-Track, Counterargument, Checklist, Case, Decision.
author: munger
license: MIT
trigger: manual
---

# Munger 12-Dimension Analysis

## Overview

This workflow applies Charlie Munger's multi-dimensional thinking framework to analyze source material. Each dimension examines the content from a different analytical perspective, building a comprehensive understanding.

## Core Philosophy

> "You must know the big ideas in the big disciplines and use them routinely — all of them, not just a few."
> — Charlie Munger

## Dimension Definitions

| # | Dimension | Color | Key Question |
|---|-----------|-------|--------------|
| 1 | Source | Terracotta #C26A5C | Where does this come from? |
| 2 | Claim | Gold #D4A843 | What is being claimed? |
| 3 | Concept | Sage #7D9B76 | What concepts are involved? |
| 4 | Model | Copper #B87333 | What universal models apply? |
| 5 | Mechanism | Emerald #5A9B7D | What mechanisms are at work? |
| 6 | Incentive | Slate Blue #6B7FA3 | What incentives drive behavior? |
| 7 | Psychology | Rust #A0553D | What cognitive biases are present? |
| 8 | Dual-Track | Ochre #C4963C | What are the rational vs. psychological explanations? |
| 9 | Counterargument | Moss #6B8E5A | What are the strongest objections? |
| 10 | Checklist | Amber #C4902A | Have all checklist items been verified? |
| 11 | Case | Steel #7A8B9A | What cases validate or refute? |
| 12 | Decision | Crimson Gold #B85C3E | What decision lessons apply? |

## Pre-Analysis

### Step 1: Ensure Text is Extracted
{{step:extract_text|output:source_text}}

### Step 2: Source-Level Pre-Analysis
{{step:llm_call|name:source_overview|output:source_overview|
  system:Provide a brief overview of this source — its type, tone, main topic, and apparent purpose. Be concise.|prompt:Analyze this text:\n\n{{source_text}}|max_tokens:500|temperature:0.3}}

## Phase 1: Foundation (Dimensions 1-3)

These dimensions establish what we're analyzing.

### Step 3: Dimension 1 — Source
{{step:llm_call|name:dim_source|output:dim_source|
  system:Analyze the provenance and credibility of this source. Consider: author expertise, publication venue, date, evidence quality, potential biases. Return structured analysis.|prompt:Source Analysis:\n\nText: {{source_text}}\n\nAnswer these questions:\n1. Who is the author and what is their expertise?\n2. What type of source is this (academic, journalism, opinion, etc.)?\n3. What is its credibility level and why?\n4. Are there any conflicts of interest or biases?\n5. What is the temporal context?|max_tokens:1024|temperature:0.3}}

### Step 4: Dimension 2 — Claim
{{step:llm_call|name:dim_claim|output:dim_claim|
  system:Extract and classify all core claims in the text. For each claim, identify: type (descriptive/normative/causal/predictive), strength, supporting evidence, and limitations.|prompt:Claim Analysis:\n\nText: {{source_text}}\n\nExtract and analyze all significant claims:\n1. What is the core thesis or main argument?\n2. What subsidiary claims support it?\n3. Classify each claim type (descriptive/normative/causal/predictive)\n4. How strong is the evidence for each?\n5. What are the limitations or caveats?|max_tokens:1024|temperature:0.3}}

### Step 5: Dimension 3 — Concept
{{step:llm_call|name:dim_concept|output:dim_concept|
  system:Identify key concepts in the text. For each: define it, explain its relationship to other concepts, note its domain of origin, and provide examples. Consider interdisciplinary connections.|prompt:Concept Analysis:\n\nText: {{source_text}}\n\nIdentify and analyze key concepts:\n1. What are the 3-5 most important concepts?\n2. How is each defined or characterized?\n3. What domain/discipline does each come from?\n4. How do they relate to each other?\n5. What are counter-concepts or opposing ideas?|max_tokens:1024|temperature:0.3}}

## Phase 2: Deep Analysis (Dimensions 4-7)

These dimensions dig into mechanisms and dynamics.

### Step 6: Dimension 4 — Model (Universal Models)
{{step:llm_call|name:dim_model|output:dim_model|
  system:Identify universal mental models and interdisciplinary frameworks that apply to this content. Consider models from: economics, physics, biology, psychology, mathematics, engineering.|prompt:Universal Model Analysis:\n\nText: {{source_text}}\nSource Overview: {{source_overview}}\n\nWhat universal models apply:\n1. What mental models from different disciplines illuminate this topic?\n2. What are the core variables in each model?\n3. What are the model's boundaries and limitations?\n4. How do multiple models interact or conflict?\n5. What predictions do these models make?|max_tokens:1024|temperature:0.4}}

### Step 7: Dimension 5 — Mechanism
{{step:llm_call|name:dim_mechanism|output:dim_mechanism|
  system:Trace causal chains, feedback loops, and system dynamics described or implied in the text. Identify direct causes, mediating factors, and emergent properties.|prompt:Mechanism Analysis:\n\nText: {{source_text}}\n\nAnalyze mechanisms:\n1. What cause-and-effect relationships are described?\n2. What are the intermediate steps between cause and effect?\n3. Are there feedback loops (positive or negative)?\n4. What are the time delays or lags?\n5. What are potential tipping points or phase transitions?|max_tokens:1024|temperature:0.4}}

### Step 8: Dimension 6 — Incentive
{{step:llm_call|name:dim_incentive|output:dim_incentive|
  system:Map the incentive structures. Identify all stakeholders, what they want, what they risk, information asymmetries, principal-agent problems, and moral hazards.|prompt:Incentive Analysis:\n\nText: {{source_text}}\n\nMap incentive structures:\n1. Who are the key stakeholders?\n2. What does each want? What do they risk?\n3. Who has information advantages?\n4. Are incentives aligned or misaligned?\n5. Are there principal-agent problems or moral hazards?\n6. Who benefits and who bears costs?|max_tokens:1024|temperature:0.4}}

### Step 9: Dimension 7 — Psychology (Cognitive Biases)
{{step:llm_call|name:dim_psychology|output:dim_psychology|
  system:Analyze psychological factors. Check for Munger's 25 cognitive biases: reward/punishment superresponse, liking tendency, disliking tendency, doubt-avoidance, inconsistency-avoidance, curiosity, Kantian fairness, envy, reciprocation, association, denial, excessive self-regard, over-optimism, deprival superreaction, social proof, contrast misreaction, stress influence, availability, use-it-or-lose-it, drug distortion, senescence, authority, twaddle, reason-respecting, lollapalooza.|prompt:Psychology Analysis:\n\nText: {{source_text}}\n\nAnalyze psychological dimensions:\n1. What cognitive biases might the author or subjects exhibit?\n2. What emotional factors are at play?\n3. How might social proof or authority influence perceptions?\n4. What psychological tendencies reinforce or challenge the claims?\n5. Are there any lollapalooza (multiple bias) effects?|max_tokens:1024|temperature:0.4}}

## Phase 3: Critical Thinking (Dimensions 8-10)

These dimensions stress-test our analysis.

### Step 10: Dimension 8 — Dual-Track
{{step:llm_call|name:dim_dualtrack|output:dim_dualtrack|
  system:Apply dual-track analysis: examine both the rational/economic explanation and the psychological/social explanation. Determine if they align or conflict, and which has more explanatory power.|prompt:Dual-Track Analysis:\n\nText: {{source_text}}\n\nApply dual-track thinking:\n1. Rational track: What variables objectively drive outcomes?\n2. Psychological track: What subconscious factors influence behavior?\n3. Do the two tracks reinforce or contradict each other?\n4. If they conflict, which explanation is more powerful?\n5. What would each track predict about future outcomes?|max_tokens:1024|temperature:0.4}}

### Step 11: Dimension 9 — Counterargument
{{step:llm_call|name:dim_counterargument|output:dim_counterargument|
  system:Generate the strongest possible counterarguments. Consider: what would a smart opponent say? What evidence would disprove the claims? What alternative explanations exist? What are the author's blind spots?|prompt:Counterargument Analysis:\n\nText: {{source_text}}\n\nSteel-man the opposition:\n1. What is the strongest argument against the main thesis?\n2. What evidence would falsify the core claims?\n3. What alternative theories explain the same phenomena?\n4. What are the author's blind spots or unstated assumptions?\n5. What would a domain expert with the opposite view say?|max_tokens:1024|temperature:0.4}}

### Step 12: Dimension 10 — Checklist
{{step:llm_call|name:dim_checklist|output:dim_checklist|
  system:Evaluate against Munger's checklist: Do I know first-order facts? Have I separated facts from interpretation and narrative? Do I know key stakeholders? Have I analyzed incentive structures? Have I found the strongest counterargument? Have I identified evidence that could disprove me? Have I checked for psychological biases? Have I compared base rates? Am I within my circle of competence? Do I know the worst-case scenario?|prompt:Checklist Verification:\n\nText: {{source_text}}\nPrevious Analysis: {{dim_source}} {{dim_claim}} {{dim_counterargument}}\n\nRun through Munger's checklist:\n1. Do I know first-order facts vs. second-hand interpretation?\n2. Have I separated facts, interpretation, and narrative?\n3. Do I know all major stakeholders and their incentives?\n4. Have I identified the strongest counterargument?\n5. What evidence would prove me wrong?\n6. Have I checked for cognitive biases in my own analysis?\n7. What are the base rates for claims made?\n8. Am I operating within my circle of competence?\n9. What is the worst-case scenario?\n10. What is my confidence level and why?|max_tokens:1024|temperature:0.3}}

## Phase 4: Application (Dimensions 11-12)

These dimensions connect to real-world cases and decisions.

### Step 13: Dimension 11 — Case
{{step:llm_call|name:dim_case|output:dim_case|
  system:Connect to historical cases and real-world examples. Identify cases that validate or refute the models and claims. Consider transferability to other domains.|prompt:Case Study Analysis:\n\nText: {{source_text}}\n\nConnect to cases:\n1. What historical cases validate the claims or models?\n2. What cases refute or complicate them?\n3. What are the boundary conditions — where does this NOT apply?\n4. Can these insights transfer to other domains?\n5. What is the most relevant contemporary parallel?|max_tokens:1024|temperature:0.4}}

### Step 14: Dimension 12 — Decision
{{step:llm_call|name:dim_decision|output:dim_decision|
  system:Extract decision-making lessons. Frame the analysis as a decision journal entry: what was decided, on what basis, what was assumed, what was ignored, and what would change the decision.|prompt:Decision Review:\n\nText: {{source_text}}\nAll Previous Analysis: {{dim_source}} {{dim_claim}} {{dim_model}} {{dim_mechanism}} {{dim_incentive}} {{dim_psychology}} {{dim_dualtrack}} {{dim_counterargument}} {{dim_checklist}} {{dim_case}}\n\nDecision analysis:\n1. If someone acted on this information, what would they decide?\n2. What are the key assumptions underlying that decision?\n3. What information is missing that would change the decision?\n4. What could go wrong and how would we know?\n5. How should this decision be revisited over time?|max_tokens:1024|temperature:0.3}}

## Synthesis

### Step 15: Compile Analysis
{{step:llm_call|name:synthesis|output:synthesis|
  system:Synthesize all 12 dimensions into a coherent analysis document. Create a structured report with key insights, confidence levels, and actionable takeaways.|prompt:Synthesize the following 12-dimension analysis into a coherent report:\n\n1. SOURCE: {{dim_source}}\n2. CLAIM: {{dim_claim}}\n3. CONCEPT: {{dim_concept}}\n4. MODEL: {{dim_model}}\n5. MECHANISM: {{dim_mechanism}}\n6. INCENTIVE: {{dim_incentive}}\n7. PSYCHOLOGY: {{dim_psychology}}\n8. DUAL-TRACK: {{dim_dualtrack}}\n9. COUNTERARGUMENT: {{dim_counterargument}}\n10. CHECKLIST: {{dim_checklist}}\n11. CASE: {{dim_case}}\n12. DECISION: {{dim_decision}}\n\nCreate a synthesis that:\n- Highlights the 3-5 most important insights\n- Notes confidence levels for key claims\n- Identifies actionable takeaways\n- Flags areas of uncertainty|max_tokens:2048|temperature:0.3}}

### Step 16: Save to Wiki
{{step:save_wiki|name:analysis_page|page_type:analysis|output:analysis_page|
  title:Munger Analysis: {{source.title}}|
  content:{{synthesis}}}}

### Step 17: Log Completion
{{step:append_log|message:Completed Munger 12-dimension analysis for "{{source.title}}"|output:log_result}}
