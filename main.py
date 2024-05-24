import cProfile
import io
import os
import pstats
from fastapi import FastAPI, Request
from app.router import router

app = FastAPI(title="Jeju VRoouty Simulator", version="1.0.0")


app.include_router(router=router)


# @app.middleware("http")
# async def profile(request: Request, call_next):
#     profiler = cProfile.Profile()
#     profiler.enable()

#     response = await call_next(request)

#     profiler.disable()
#     stream = io.StringIO()
#     stats = pstats.Stats(profiler, stream=stream)

#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     project_dir = os.path.basename(current_dir)

#     def filter_and_trim_stats(stats, limit=10):
#         filtered_stats = pstats.Stats()
#         for func, (cc, nc, tt, ct, callers) in stats.stats.items():
#             filename, lineno, funcname = func
#             if current_dir in filename:
#                 trimmed_filename = filename.split(project_dir, 1)[-1]
#                 trimmed_func = (trimmed_filename, lineno, funcname)
#                 filtered_stats.stats[trimmed_func] = (cc, nc, tt, ct, callers)
#         return filtered_stats.sort_stats(pstats.SortKey.TIME).print_stats(limit)

#     stats.sort_stats(pstats.SortKey.TIME)
#     filter_and_trim_stats(stats, limit=10)

#     print(stream.getvalue())
#     return response
