<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/sentinel_banner.png">
  <img alt="Sentinel logo" src=".github/sentinel_banner.png">
</picture>

# Sentinel

**Sentinel** is a modular, HQ-centric operations platform designed to scale from personal daily life to high-stakes tactical coordination. It applies military-style Command & Control (C2) principles to manage intelligence, logistics, and situational awareness.
---

### The Vision: From Personal to Tactical
Originally built as a personal operations tool, Sentinel v2 has evolved into a distributed HQ system. It treats every user as a "Node" and every task as a "Mission."

Whether you are planning a University semester, tracking a Gym routine, or coordinating a Multi-device Field Operation, Sentinel provides the infrastructure to maintain the tactical advantage.


## Modular Architecture
Sentinel is built on a Modular Core. You deploy the "HQ" and enable only the capabilities required for your current Theater of Operations, you're the one responsible for the security, privacy and success of your operations.

### Core System (The "HQ")
* **Mission Planning (C2):** Organize operations into phases with sequential or adaptive steps.
* **Node Telemetry:** Real-time tracking of participants (Nodes) via WebSockets/CoT protocols.
* **Situational Awareness (COP):** A Common Operational Picture that overlays missions, routes, and points of interest on a unified map.
* **After-Action Review (AAR):** Systematic logging of deviations and performance metrics to ensure mission success.

### 📦 Available Modules (Plugin-Based)
* **mod-telemetry**: High-precision GPS tracking, breadcrumbs, and device heartbeat.
* **mod-logistics**: Asset tracking and gear readiness (maintenance schedules, battery levels).
* **mod-humint**: Human Intelligence mapping. Track contacts, affiliations, and reliability ratings.
* **mod-comms**: SOS protocols and encrypted signaling (ntfy.sh, Telegram, or private WebSockets).
* more to come soon, this list might be changed multiple times in near future.

## Features (to be reviewed, active WIP)

* **Mission Planning**: Organize your daily operations as missions with sequential or flexible steps.
* **Asset Tracking**: Keep accountability for personal equipment and assign them to missions.
* **Situational Awareness**: Sync calendars, overlay missions on maps, and track routes.
* **After-Action Review**: Log notes, delays, and unexpected changes to learn and improve.
* **Flexible Operations**: Support templates, checklists, and ad-hoc missions.

---

## Tech Stack

* **Backend**: FastAPI, MongoDB
* **Frontend**: Next.js, TailwindCSS, Framer Motion
* **Integrations**: Traccar (GPS logging), ICS calendar import, Tailscale VPN
* **UI Components**: shadcn/ui, Lucide Icons

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/veylor-hq/sentinel.git
cd sentinel
```

### 2. Install dependencies

```bash
poetry install

```

### 3. Set up environment variables
Create a `.env` from the `sample.env` file and customize it with your own values.  
```bash
cp sample.env .env
```

## 4. Enter the virtual environment  

```bash
poetry shell
```  
or  
```bash
poetry env activate
```   
And make sure you have mongodb running.  

### 4. Run the development server

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to view the API documentation.

---

## API Example

### Get Mission

```http
GET /missions/{mission_id}?include_steps=true&include_locations=true
Authorization: Bearer <token>
```

**Response:**

```json
{
  "mission": { ... },
  "steps": [
    {
      "id": "step1",
      "name": "Lecture 1",
      "locations": [ ... ]
    },
    ...
  ]
}
```

---

## Deployment
TBD

---

## Future Plans

TBD

---

## ⚖️ License
Licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
Sentinel is, and will always remain, open-source and sovereign software.
