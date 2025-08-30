# Sentinel Project

**Sentinel** is a personal operations platform that applies military-style mission planning principles to daily life, helping users plan, execute, and review their activities with structure and adaptability.

---

## Features

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


---

## Future Plans

* Mobile app or PWA for on-the-go mission tracking
* Advanced analytics and after-action review dashboards
* Real-time GPS tracking integration

---

## License

MIT License
