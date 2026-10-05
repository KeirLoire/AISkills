<div align="center">
    <img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/openclaw.png" width="120" alt="AI Agent Logo"/><br>
    <h1>AI Skills Registry</h1>
    <p>A repository of standardized, repeatable capabilities and automations for personal projects, system integrations, and custom workflows.</p>
</div>

---

## About

This repository serves as a centralized hub of **AI Skills**—structured instructions, guidelines, and automation scripts. 

Each skill represents a discrete capability or routine. By standardizing these tasks, we enable AI assistants (such as Claude Code, Gemini, or ChatGPT) to interact with our projects, databases, document formats, and smart home configurations with precision and safety.

---

## Setup for AI Agents

### 1. Load the Repository

Point your AI coding agent (Claude Code, Gemini, or another skill-aware harness) at this directory — either as its working directory or a subfolder within a larger workspace it has open:

```bash
cd C:\Users\chest\Desktop\workspace\projects\AISkills
```

Claude Code and compatible agents automatically scan `skills/**/SKILL.md` — note the exact uppercase filename. A lowercase `skill.md` is **not** detected on case-sensitive filesystems, so the loader will silently skip the skill. See [Authoring New Skills](#authoring-new-skills) below for the frontmatter format that makes a skill discoverable.

### 2. Configure `.env`

Some skills require credentials set in a local `.env` file to control devices or communicate with messengers. Copy the template and fill in real values:

```bash
cp .env.example .env
```

`.env` (Tapo accounts + Facebook messenger session details):

```env
# TP-Link Tapo Smart Home Settings
TAPO_USERNAME=your-tapo-email@example.com
TAPO_PASSWORD=your_tapo_cloud_password

# Optional room mappings if device nicknames are generic (like "Light").
# Format: room_name:ip_address,room_name:ip_address — kept in .env, never committed.
TAPO_ROOM_MAP=living room:192.168.1.20,sala:192.168.1.20

# Facebook Messenger Bot Settings
FB_COOKIES='[{"name": "c_user", "value": "..."}, {"name": "xs", "value": "..."}]'
AUTHORIZED_FB_USERS=comma_separated_facebook_user_ids
DEFAULT_FB_THREAD_ID=default_facebook_thread_id

# AI Evaluation & Routing (Optional)
GEMINI_API_KEY=your_gemini_api_key
```

- `.env` is gitignored — only the placeholder `.env.example` is tracked in git. Never commit `.env`, and never paste its values into a generated script, commit, log, or `SKILL.md`.

---

## Directory Structure

Skills are organized logically by category and name:

```text
<repository-name>/
│
├── README.md               <-- Repository guidelines (this file)
└── skills/                 
    ├── <category>/         <-- Skill domain (e.g. home, finance, social)
    │   └── <skill-name>/   <-- The specific task or capability
    │       ├── SKILL.md    <-- Main instruction file (with YAML frontmatter)
    │       └── [scripts/]  <-- (Optional) Supporting automation tools or helper scripts
    └── ...
```

---

## Skill Catalog

| Category | Skill Name & Link | Description | Key Target |
| :--- | :--- | :--- | :--- |
| **Home** | [Tapo Device Control](skills/home/tapo/SKILL.md) | Turns Tapo smart plugs and bulbs on or off and checks status/power draw using auto-discovery. | Tapo smart devices |
| **Social** | [Facebook Messenger Control](skills/social/facebook/SKILL.md) | Hosts a Messenger chat bot to listen for home automation commands from authorized users. | Facebook Messenger chats |
| **Dev** | [Antigravity CLI](skills/dev/antigravity-cli/SKILL.md) | Drives the Antigravity CLI (`agy`) for non-interactive agentic runs, with verified flag surface, permission setup, and failure-mode handling. | Antigravity CLI (`agy`) |

---

## How to Use a Skill (For AI Agents)

When assigned a task corresponding to any of the skills in this catalog, the agent should follow this lifecycle:

1. **Locate the Skill**: Find the correct skill folder under `skills/` (e.g., `skills/home/tapo/`).
2. **Read the Instructions**: Open and read the `SKILL.md` file completely before starting the task.
3. **Follow the Constraints**: Closely adhere to **Edge Cases & Constraints** (e.g., dietary restrictions, user authorization checks).
4. **Execute Automation Tools**: If the skill contains a `scripts/` folder, run or adapt the scripts as needed.
5. **Verify Outputs**: Use the **Checklist** at the end of `SKILL.md` to verify that all criteria have been met before declaring completion.

---

## How to Author New Skills

To add a new capability:
1. Create a directory: `skills/<category>/<skill-name>/`
2. Add a `SKILL.md` file using this structure:
   - **YAML Frontmatter**: Define `name` and `description` triggers.
   - **Purpose**: High-level explanation of the task.
   - **Inputs**: Required inputs/context.
   - **Detailed Steps**: Sequential guide for the AI.
   - **Edge Cases & Constraints**: Specific safety rules and parameters.
   - **Checklist**: Validation points for the AI before completing tasks.
