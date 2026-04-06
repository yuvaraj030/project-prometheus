---
name: web_search
description: Search the web for information using DuckDuckGo or Google
tools:
  - web_search
  - read_url
---

# Web Search Skill

You can search the web to find current information, answer questions about recent events, look up documentation, or verify facts.

## When to Use
- User asks about current events, news, or real-time data
- User needs documentation or references
- User asks "search for..." or "look up..."
- You need to verify a fact you're unsure about

## Tools Available

### web_search
Search the web with a query string.
- **query** (string, required): The search query
- Returns: List of results with title, URL, and snippet

### read_url
Fetch and read the content of a specific URL.
- **url** (string, required): The URL to read
- Returns: The text content of the page

## Instructions
1. Formulate a clear, specific search query
2. Use `web_search` to find relevant results
3. If needed, use `read_url` to get full details from a promising result
4. Summarize the findings concisely for the user
5. Always cite your sources with URLs
