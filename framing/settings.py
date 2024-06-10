import os
from evora.debug import DEBUGGING

MAX_SOURCES = 50
CACHE_DIR = "/data/astrometry-index"

if DEBUGGING:
    CACHE_DIR = './' + CACHE_DIR
    os.makedirs(os.path.dirname(CACHE_DIR), exist_ok=True)