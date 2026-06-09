---
name: quick-summary
version: "1.0"
description: Quick summary extraction only. No entity extraction, no wiki page creation, no analysis. Fastest ingestion option.
author: munger
license: MIT
trigger: manual
---

# Quick Summary

## Overview
Generate a summary of the source material without creating wiki pages or extracting entities. This is the fastest ingestion option.

## Steps

### Step 1: Extract Text
{{step:extract_text|output:source_text}}

### Step 2: Generate Summary
{{step:llm_call|name:summary|output:summary|
  system:Provide a concise summary.|prompt:Summarize:\n\n{{source_text}}|max_tokens:1024|temperature:0.3}}

### Step 3: Save Summary to Source
Save the generated summary back to the source record.

### Step 4: Log
{{step:append_log|message:Quick summary generated for "{{source.title}}"|output:log}}
