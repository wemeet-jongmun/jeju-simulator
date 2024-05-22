import os
import json
import aiohttp

from app.models.vroouty import RequestParam, VRooutyResponse

BASE_URL = os.environ["VROOUTY_URL"]


async def VRooutyRequest(
    param: RequestParam,
) -> VRooutyResponse | None:
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            BASE_URL,
            json=json.loads(param.model_dump_json()),
            headers={"Content-Type": "application/json"},
        )
        status = response.status
        response = await response.json()

        if status != 200:
            return None
        return VRooutyResponse(**response)
