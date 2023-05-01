from .control import *
from .tidal_euclid import *
from .pattern import *
from .utils import *
from .mini import *
from .stream import SuperDirtStream

__streams = {}

def tidal_factory(env, osc_client):
    """Returns a tidal function to play Tidal patterns on a given OSC client"""
    env = env

    def tidal(key, pattern=None):
        if key not in __streams:
            __streams[key] = SuperDirtStream(name=key, osc_client=osc_client)
            env.clock.subscribe(__streams[key])
        if pattern:
            __streams[key].pattern = pattern
        return __streams[key]

    return tidal

def hush_factory(env, osc_client):

    def hush():
        for stream in __streams.values():
            stream.pattern = silence
            env.clock.unsubscribe(stream)
        __streams.clear()

    return hush


class __Streams:
    def __setitem__(self, key, value):
        p(key, value)


d = __Streams()
