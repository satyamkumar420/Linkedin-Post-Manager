# 🚀 LinkedIn Post Manager MCP 2.0 Server

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![MCP 2.0](https://img.shields.io/badge/MCP-2.0%2B-orange.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/satyam404)

An enterprise-grade, modular **Model Context Protocol (MCP 2.0)** server for drafting, optimizing, scheduling, managing, and publishing posts to **LinkedIn**.

Built with the official **MCP 2.0** architecture (`mcp.server.mcpserver.MCPServer`), official **LinkedIn REST API v2 / Posts API**, and a local **SQLite** state engine.

---

## ✨ Features

- 🛡️ **100% Safe Publishing**: Uses official LinkedIn REST APIs (`/rest/posts` and `/rest/images`). Zero risk of bot detection or account suspensions.
- 🔑 **MCP Environment Credentials**: Seamlessly reads credentials directly from your MCP client config's `env` section (with fallback to `.env`).
- 📝 **Offline Drafts Engine**: Save, search, tag, edit, and organize post ideas locally in SQLite before going live.
- ⏰ **Automated Scheduling**: Queue posts for any future date/time with automatic background dispatch.
- 🎨 **AI Post Optimizer & Formatter**: Transforms raw developer thoughts into high-engagement LinkedIn posts with punchy hooks, whitespace pacing, and strong CTAs.
- 🔍 **Readability & Hook Analyzer**: Checks character count, hook length (under 140 chars before the `...see more` fold), and hashtag density.
- 🖼️ **Media & Image Uploads**: Automated 3-step asset initialization, binary upload, and publishing.
- ⚡ **MCP 2.0 Ready**: Exposes **Tools** (`@mcp.tool`), **Resources** (`@mcp.resource`), and **Prompts** (`@mcp.prompt`).

---

## 🛠️ Tech Stack & Requirements

- **Runtime:** Python 3.10+ (tested with Python 3.14)
- **Protocol:** `mcp>=2.1.0` (MCP 2.0 `MCPServer`)
- **HTTP Client:** `httpx`
- **Database:** SQLite (built-in)
- **Scheduler:** `apscheduler`
- **Image Processing:** `pillow`

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/satyamkumar420/Linkedin-post-manager.git
cd Linkedin-post-manager
```

### 2. Install dependencies
Using `uv` (recommended):
```bash
uv pip install -e .
```
Or with standard `pip`:
```bash
pip install -e .
```

---

## 🔑 Authentication & Setup

You need a free LinkedIn Developer App with the **Share on LinkedIn** product (`w_member_social`, `openid`, `profile`, `email` permissions).

### Option A: 1-Click Interactive Token Helper (Recommended)
Run our built-in OAuth helper:
```bash
python setup_auth.py
```
This will:
1. Prompt for your LinkedIn `Client ID` and `Client Secret`.
2. Open your default browser to authorize the application.
3. Automatically capture the callback, exchange the code for an Access Token, and fetch your Person URN.
4. Output the exact ready-to-use JSON configuration snippet for your MCP client!

### Option B: Manual Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in:
```env
LINKEDIN_ACCESS_TOKEN=your_oauth_access_token
LINKEDIN_PERSON_URN=urn:li:person:your_person_id
```

---

## ⚙️ MCP Client Configuration

Add this server to your MCP configuration file (e.g. `~/.gemini/config/mcp_config.json`, Claude Desktop, or Cursor):

### Configuration in `mcp_config.json`:
```json
{
  "mcpServers": {
    "linkedin-post-manager": {
      "command": "python",
      "args": ["-m", "linkedin_post_manager.server"],
      "env": {
        "PYTHONPATH": "d:/MCP/Linkedin-post-manager/src",
        "LINKEDIN_ACCESS_TOKEN": "YOUR_LINKEDIN_ACCESS_TOKEN",
        "LINKEDIN_PERSON_URN": "urn:li:person:YOUR_URN"
      }
    }
  }
}
```

> [!NOTE]
> `LINKEDIN_PERSON_URN` is optional. If omitted from `env`, the server automatically queries `/v2/userinfo` to discover your Person URN!

---

## 🧰 Available MCP Tools

### 1. Publishing & Management
| Tool | Description |
| :--- | :--- |
| `publish_text_post` | Immediately publish text or link posts to your LinkedIn feed. |
| `publish_image_post` | Upload a local image and publish a media post. |
| `delete_post` | Delete a published LinkedIn post by its URN. |

### 2. Drafts Engine (Local SQLite)
| Tool | Description |
| :--- | :--- |
| `save_draft` | Save an idea or post draft with optional tags and image paths. |
| `list_drafts` | Filter drafts by status (`draft`, `ready`, `scheduled`, `published`) or search keyword. |
| `get_draft` | Retrieve full draft content and metadata. |
| `update_draft` | Update title, content, status, or media paths of an existing draft. |
| `delete_draft` | Delete a saved draft from the database. |

### 3. Scheduling & Queue
| Tool | Description |
| :--- | :--- |
| `schedule_post` | Schedule a post for future execution (`scheduled_at_iso`). |
| `list_scheduled_posts` | View all pending or executed scheduled posts in the queue. |
| `cancel_scheduled_post` | Cancel a pending scheduled post. |
| `check_and_publish_due_posts`| Manually trigger immediate publishing of any due posts. |

### 4. AI Optimization & Diagnostics
| Tool | Description |
| :--- | :--- |
| `format_post` | Reformat text for mobile readability, list pacing, hooks, and CTAs. |
| `analyze_post` | Character count, hook length check (<140 chars), readability score, and hashtag density. |
| `get_my_profile` | Check authenticated user details and Person URN. |
| `get_post_history` | View history of posts published through this manager. |
| `get_manager_stats` | Inspect draft counts, scheduled posts, and credential health. |

---

## 📚 MCP 2.0 Resources & Prompts

### Resources
- `linkedin://templates/list`: List available LinkedIn post templates (`project-launch`, `tech-learning`, `career-milestone`, `hot-take`).
- `linkedin://stats/summary`: Real-time JSON summary of local drafts and published posts.

### Prompts
- `draft_tech_post`: Guided prompt instructing the LLM to write an engaging tech post.
- `generate_viral_hooks`: Generates 5 high-converting opening hooks for any post topic.

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 7 test cases covering drafts CRUD, scheduling, post formatting, hook scoring, and MCP tool registration will execute in under a second.

---

## 👤 Author & Maintainer

**Satyam Kumar**
- **Role:** Software Developer
- **GitHub:** [@satyamkumar420](https://github.com/satyamkumar420)
- **LinkedIn:** [satyamkumar404](https://www.linkedin.com/in/satyamkumar404/)
- **Email:** satyamkumar2460@gmail.com
- **Phone:** +91 9693756696

---

## ☕ Support & Sponsor

If you find this project helpful and want to support its maintenance and ongoing development:

<div align="center">

<a href="https://buymeacoffee.com/satyam404" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="200" />
</a>

<br/><br/>

<a href="https://buymeacoffee.com/satyam404" target="_blank">
  <img src="./bmc_qr.png" alt="Scan to Buy Me A Coffee" width="170" style="border-radius: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.15);" />
</a>

<br/>

<sub>Scan the QR code or click the button above to buy me a coffee! Thank you for your support! ☕✨</sub>

</div>

---

## 📄 License

This project is licensed under the MIT License.
