---
name: kimi-find-skills
description: Search and discover skills for the agent. Use when the user expresses intent to find a skill, search for a skill, or needs a skill to solve a specific problem. Triggers on phrases like "find skill", "search skill", "look for skill", or when the user describes a problem and asks for a skill recommendation. Also triggers when the user asks about available skills or skill discovery.
---

# Kimi Find Skills

Search and discover skills across multiple sources to help users find the right capability for their needs.

## Workflow

### Step 1: Check Existing Skills

When the user asks to find a skill, first scan the current skill list (both `/app/.agents/skills/` and `/app/.user/skills/`) to see if any existing skill matches their need.

If a matching skill is found, present it to the user with its description and confirm if it meets their needs.

If no matching skill is found, proceed to Step 2.

### Step 2: Ask for Extended Search

If no matching skill exists in the current environment, ask the user politely:

> No matching skill was found in the current skill list. Would you like me to expand the search scope and look in broader skill repositories? I can search the built-in skill library, GitHub open-source skill repositories, and the SkillHub skill marketplace.

Wait for user confirmation before proceeding to Step 3.

### Step 3: Multi-Source Search (User Confirmed)

Search in the following priority order. Stop and present results as soon as a suitable match is found.

#### 3.1 Search Built-in Skills (`/app/.agents/skills/`)

Use `shell` to list all skill directories:

```bash
ls /app/.agents/skills/
```

Read SKILL.md files of potentially matching skills to verify relevance. If found, present the skill name and description to the user.

#### 3.2 Search GitHub

If not found in built-in skills, search GitHub using the `web_search` tool:
- Query pattern: `kimi skill <keywords>` or `kimi agent skill <keywords>`
- Also try: `site:github.com kimi skill <keywords>`

Evaluate results by:
1. **Description relevance** - Does the README/SKILL.md describe solving the user's problem?
2. **Star count** - Prefer repositories with more stars (indicates community validation)
3. **Recent activity** - Prefer actively maintained repositories

Present the top 1-2 matches with:
- Repository name and link
- Star count
- Brief description of what it does
- Why it matches the user's need

#### 3.3 Search SkillHub (`https://skillhub.cn/`)

If still not found, search SkillHub:
1. Visit `https://skillhub.cn/` using `browser_visit`
2. Use the search functionality on the site with the user's keywords
3. Browse results and identify the most relevant skill

To help users quickly find skills on SkillHub, guide them to:
- Use the search bar with specific keywords (e.g., "PDF", "weather", "image")
- Browse categories if the site has category filters
- Check skill ratings/download counts if available
- Read the skill description to verify it matches their need

Present the best match with:
- Skill name and link
- Description
- How to install/use it

### Step 4: Summarize Results

After searching all sources, provide a clear summary:
- If found: Present the skill and explain how to use it
- If not found: Inform the user that no matching skill was found across all sources, and suggest:
  - Creating a custom skill for their specific need
  - Using general agent capabilities without a specialized skill
  - Checking back later as new skills are added regularly

## Search Strategy Tips

- **Keyword extraction**: Identify the core task/problem the user wants to solve. Convert their natural language request into 1-3 concise search keywords.
- **Fuzzy matching**: Consider synonyms and related terms. For example, if the user asks for "PDF editor", also search for "PDF modify", "PDF manipulation".
- **Problem-to-skill mapping**: If the user describes a problem rather than asking for a skill directly, infer what type of skill would solve it. For example, "I need to merge PDFs" -> search for PDF-related skills.
