import os

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
from dotenv import load_dotenv

from pipline import run

# import consumers

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# def get_redis_connection():
#     return redis.Redis(
#         host=os.getenv("REDIS_HOST"),
#         port=os.getenv("REDIS_PORT"),
#         password=os.getenv("REDIS_PASSWORD"),
#         decode_responses=True,
#     )


redis = get_redis_connection(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)


class Task(HashModel):
    url: str

    class Meta:
        database = redis


# Define the models for the Redis Hashes
class Delivery(HashModel):
    budget: int = 0
    notes: str = ""

    class Meta:
        database = redis


class Event(HashModel):
    delivery_id: str = None
    type: str
    data: str

    class Meta:
        database = redis


# @app.get("/deliveries/{pk}/status")
# async def get_state(pk: str):
#     state = redis.get(f"delivery:{pk}")

#     if state is not None:
#         return json.loads(state)

#     state = build_state(pk)
#     redis.set(f"delivery:{pk}", json.dumps(state))
#     return state


@app.get("/tasks/{pk}")
async def get_task(pk: str):  # Change the type from int to str
    # Construct the key as used in the create_task function
    task_key = f"task:{pk}"

    # Check if the task exists
    if not redis.exists(task_key):
        raise HTTPException(status_code=404, detail="Task not found")

    # Fetch all hash values for the given task key
    task_data = redis.hgetall(task_key)

    # Optionally, convert empty string values to None or handle them as you prefer
    task_data = {k: (v if v != "" else None) for k, v in task_data.items()}

    return {"task_id": pk, "data": task_data}


# def build_state(pk: str):
#     pks = Event.all_pks()
#     all_events = [Event.get(pk) for pk in pks]
#     events = [event for event in all_events if event.delivery_id == pk]
#     state = {}

#     for event in events:
#         state = consumers.CONSUMERS[event.type](state, event)

#     return state


@app.post("/tasks/create")
async def create_task(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    task = Task(url=body["url"]).save()
    ##TODO redis.set
    redis.hmset(
        f"task:{task.pk}",
        {
            "chapter_list": "",
            "sub_chapter_list": "",
            "term_list": "",
            "status": "Loading Video Data",
        },
    )
    background_tasks.add_task(run, body["url"], task.pk, redis)
    return {"taskid": task.pk}


# @app.post("/deliveries/create")
# async def create(request: Request):
#     body = await request.json()
#     print(body)
#     delivery = Delivery(
#         budget=body["data"]["budget"], notes=body["data"]["notes"]
#     ).save()
#     event = Event(
#         delivery_id=delivery.pk, type=body["type"], data=json.dumps(body["data"])
#     ).save()
#     state = consumers.CONSUMERS[event.type]({}, event)
#     print(state)
#     redis.set(f"delivery:{delivery.pk}", json.dumps(state))
#     return state


# @app.post("/event")
# async def dispatch(request: Request):
#     body = await request.json()
#     delivery_id = body["delivery_id"]
#     # print(delivery_id)
#     state = await get_state(delivery_id)
#     event = Event(
#         delivery_id=delivery_id, type=body["type"], data=json.dumps(body["data"])
#     ).save()
#     new_state = consumers.CONSUMERS[event.type](state, event)
#     redis.set(f"delivery:{delivery_id}", json.dumps(new_state))
#     return new_state
