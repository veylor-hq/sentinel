import asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from models.models import Location, Step, User, Mission, StepTemplate 

async def seed():
    # 1. Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(database=client.sentinel_db, document_models=[User, Mission, Step, Location])

    # TODO: Clean existing data

    # 2. Create default user
    user = await User.find_one({"username": "ihor"})
    if not user:
        user = User(username="ihor", password="$2b$12$V5Hzp0bLkYKIVJzreM6eku1zwAk4i1K9q6OOso0uAsNeK9TpksFXO")
        await user.insert()
        print("Created default user")

    # 3. Create default mission templates
    default_missions = [
        {
            "name": "Small Tesco [walk]"
        }
        # {"name": "University Day Ops", "description": "Default daily university schedule template"},
    ]
    for m in default_missions:
        existing = await Mission.find_one(Mission.name == m["name"])
        if not existing:
            mt = Mission(name=m["name"], operator=user.id)
            await mt.insert()
            print(f"Inserted template: {m['name']}")

    tesco_location = await Location(
        **{
            "name": "Tesco Express Goring",
            "coordinates": {
                "lat": 50.8166891,
                "lon": -0.4306186
            }
        }
    ).insert()

    home_location = await Location(
        **{
            "name": "Home",
            "coordinates": {
                "lat": 0,
                "lon": 0
            }
        }
    ).insert()
    

    small_tesco_walk = await Mission.find_one(Mission.name == default_missions[0]["name"])
    steps = [
        {
            "order": 1,
            "name": "Leave Home",
            "mission_id": small_tesco_walk.id,
            "step_type": "custom",
            "status": "planned",
            "planned_start": "2025-09-09T10:00:00Z",
            "planned_end": "2025-09-09T10:10:00Z",
            "location": home_location.id
        },
        {
            "order": 2,
            "name": "Enter Tesco",
            "mission_id": small_tesco_walk.id,
            "step_type": "custom",
            "status": "planned",
            "planned_start": "2025-09-09T10:10:00Z",
            "planned_end": "2025-09-09T10:11:00Z",
            "location": tesco_location.id
        },
        {
            "order": 3,
            "name": "Buy stuff",
            "mission_id": small_tesco_walk.id,
            "step_type": "custom",
            "status": "planned",
            "planned_start": "2025-09-09T10:10:00Z",
            "planned_end": "2025-09-09T10:30:00Z",
            "location": tesco_location.id
        },
        {
            "order": 4,
            "name": "Leave Tesco",
            "mission_id": small_tesco_walk.id,
            "step_type": "custom",
            "status": "planned",
            "planned_start": "2025-09-09T10:30:00Z",
            "planned_end": "2025-09-09T10:31:00Z",
            "location": tesco_location.id
        },
         {
            "order": 5,
            "name": "Get Home",
            "mission_id": small_tesco_walk.id,
            "step_type": "custom",
            "status": "planned",
            "planned_start": "2025-09-09T10:31:00Z",
            "planned_end": "2025-09-09T10:41:00Z",
            "location": home_location.id
        }
    ]
    for s in steps:
        step = Step(**s)
        await step.insert()
    print("Inserted default steps for Tesco Walk 1")

    print("Database seeding complete")

if __name__ == "__main__":
    asyncio.run(seed())
