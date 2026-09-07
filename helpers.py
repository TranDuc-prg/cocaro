# helpers.py (helpers_6.py)
import random, hashlib
def generate_room_id():
    return "phong_" + hashlib.md5(str(random.random()).encode()).hexdigest()[:8]