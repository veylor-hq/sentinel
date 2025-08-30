import asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from models.models import User, MissionTemplate, StepTemplate 

async def seed():
    # 1. Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(database=client.sentinel_db, document_models=[User, MissionTemplate, StepTemplate])

    # TODO: Clean existing data

    # 2. Create default user
    user = await User.find_one({"username": "ihor"})
    if not user:
        user = User(username="ihor", password="$2b$12$V5Hzp0bLkYKIVJzreM6eku1zwAk4i1K9q6OOso0uAsNeK9TpksFXO")
        await user.insert()
        print("Created default user")

    # 3. Create default mission templates
    default_missions = [
        {"name": "University Day Ops", "description": "Default daily university schedule template"},
        {"name": "Field Visit", "description": "Default field work schedule template"},
        {"name": "Shopping Run", "description": "Default shopping/procurement template"},
    ]
    for m in default_missions:
        existing = await MissionTemplate.find_one(MissionTemplate.name == m["name"])
        if not existing:
            mt = MissionTemplate(name=m["name"], description=m["description"], operator=user.id)
            await mt.insert()
            print(f"Inserted template: {m['name']}")

    # 4. Create default step templates
    # Example: steps for "University Day Ops"
    uni_template = await MissionTemplate.find_one(MissionTemplate.name == "University Day Ops")
    if uni_template:
        steps = [
            {"name": "Leave Home", "order": 1}, 
            {"name": "Infiltration - Train", "order": 2},
            {"name": "Lecture 1", "order": 3},
            {"name": "Break / Free Time", "order": 4},
            {"name": "Lecture 2", "order": 5},
            {"name": "Practical", "order": 6},
            {"name": "Social Ops", "order": 7},
            {"name": "Exfiltration - Train", "order": 8},
            {"name": "Get Home", "order": 9},
        ]
        for s in steps:
            existing_step = await StepTemplate.find_one(StepTemplate.name == s["name"], StepTemplate.mission_template == uni_template.id)
            if not existing_step:
                step = StepTemplate(name=s["name"], order=s["order"], mission_template=uni_template.id)
                await step.insert()
        print("Inserted default steps for University Day Ops")

        # TODO: Add actual time-frames and locations

    print("Database seeding complete")

if __name__ == "__main__":
    asyncio.run(seed())
