# SARDINE: this is the main entry point for Sardine. __init__.py will attempt
# to load everything needed for an interactive session directly from here.
# Linters might complain about the fact some objects are not accessed. Sure,
# they are not accessed right now but will later in time when the user will
# start interacting with the system.

import asyncio
import warnings
import sys
from rich import print

try:
    import uvloop
except ImportError:
    print("[yellow]UVLoop is not installed. Not supported on Windows![/yellow]")
    print("[yellow]Rhythm accuracy may be impacted[/yellow]")
else:
    uvloop.install()

from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich import pretty
from .io import read_user_configuration, pretty_print_configuration_file
from .io import ClockListener, MidiListener, ControlTarget, NoteTarget
from .clock import *
from .superdirt import SuperColliderProcess
from .io import Client as OSC
from .io import OSCSender, MIDISender

from .sequences import ListParser
from .sequences.LexerParser.Qualifiers import qualifiers
from typing import Union
from .sequences import *

import os

print(os.getpid())

import psutil

warnings.filterwarnings("ignore")
# Use rich print by default
pretty.install()

sardine = """

░██████╗░█████╗░██████╗░██████╗░██╗███╗░░██╗███████╗
██╔════╝██╔══██╗██╔══██╗██╔══██╗██║████╗░██║██╔════╝
╚█████╗░███████║██████╔╝██║░░██║██║██╔██╗██║█████╗░░
░╚═══██╗██╔══██║██╔══██╗██║░░██║██║██║╚████║██╔══╝░░
██████╔╝██║░░██║██║░░██║██████╔╝██║██║░╚███║███████╗
╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░╚═╝╚═╝░░╚══╝╚══════╝

Sardine is a MIDI/OSC sequencer made for live-coding
Play music, read the docs, contribute, and have fun!
"""
print(f"[red]{sardine}[/red]")


def ticked(condition: bool):
    """Print an ASCII Art [X] if True or [ ] if false"""
    return "[X]" if condition else "[ ]"


# Reading / Creating / Updating the configuration file
config = read_user_configuration()
print_config = pretty_print_configuration_file


print(
    f"[yellow]BPM: [red]{config.bpm}[/red],",
    f"[yellow]BEATS: [red]{config.beats}[/red]",
    f"[yellow]SC: [red]{ticked(config.boot_superdirt)}[/red],",
    f"[yellow]DEFERRED: [red]{ticked(config.deferred_scheduling)}[/red]",
    f"[yellow]MIDI: [red]{config.midi}[/red]",
)

# Booting SuperCollider / SuperDirt
if config.boot_superdirt is True:
    try:
        SC = SuperColliderProcess(
            startup_file=config.superdirt_config_path, verbose=config.verbose_superdirt
        )
    except OSError as error:
        print("[red]SuperCollider could not be found![/red]")
else:
    print("[green]Booting without SuperCollider![/green]")

# Starting the default Clock
c = Clock(
    midi_port=config.midi,
    bpm=config.bpm,
    beats_per_bar=config.beats,
    ppqn=config.ppqn,
    deferred_scheduling=config.deferred_scheduling,
)

# Synonyms for swimming function management
cs = again = anew = a = c.schedule_func
cr = c.remove
stop = c.remove
children = c.print_children
S = c.note  # default SuperDirt
M = c.midinote  # default Midi Connexion
O = c.oscmessage  # default OSC Sender
MidiSend = MIDISender
# O = OSCSender
n = next


def hush(*args):
    """Stop all runners"""
    if len(args) >= 1:
        for runner in args:
            cr(runner)
    else:
        for runner in c.runners.values():
            runner.stop()


def midinote(delay, note: int = 60, velocity: int = 127, channel: int = 1):
    """Send a MIDI Note"""
    asyncio.create_task(
        c._midi.note(delay=delay, note=note, velocity=velocity, channel=channel)
    )


def cc(channel: int = 1, control: int = 20, value: int = 64):
    asyncio.create_task(
        c._midi.control_change(channel=channel, control=control, value=value)
    )


def pgch(channel: int = 1, program: int = 0):
    asyncio.create_task(c._midi.program_change(channel=channel, program=program))


def pwheel(channel: int = 1, pitch: int = 0):
    asyncio.create_task(c._midi.pitchwheel(channel=channel, pitch=pitch))

def sysex(data: list[int]):
    asyncio.create_task(c._midi.sysex(data))

def swim(fn):
    """Push a function to the clock"""
    cs(fn)
    return fn

def die(fn):
    """Remove a function from the clock"""
    cr(fn)
    return fn

def sleep(n_beats: Union[int, float]):
    """Artificially sleep in the current function for `n_beats`.

    Example usage: ::

        @swim
        def func(delay=4):
            sleep(3)
            for _ in range(3):
                S('909').out()
                sleep(1/2)
            cs(func)

    This should *only* be called inside functions scheduled by the clock.
    Calling this outside of a scheduled function will result in
    abnormal behavior such as overlapping sounds and clock desync.

    Using in asynchronous functions
    -------------------------------

    This can be used in `async def` functions and does *not* need to be awaited.

    Sounds scheduled in asynchronous functions will be influenced by
    real time passing. For example, if you sleep for 48 ticks and
    await a function that takes 5 ticks to complete, any sounds sent
    afterwards will occur 53 ticks from when the function was called (48 + 5).

    ::

        @swim
        async def func(delay=4):
            print(c.tick)  # 0

            sleep(1)       # +48 virtual ticks (assuming c.ppqn = 48)
            await abc()    # +5 real-time ticks

            S('bd').out()  # occurs 48 ticks from now
            print(c.tick)  # 53
            cs(func)

    Technical Details
    -----------------

    Unlike `time.sleep(n)`, this function does not actually block
    the function from running. Instead, it temporarily affects the
    value of `Clock.tick` and extends the perceived time of other
    Clock methods like `Clock.wait_after()` and `Clock.get_beat_ticks()`.

    In essence, this maintains the precision of sound scheduling
    without requiring the use of declarative syntax like
    `S('909', at=1/2).out()`.

    """
    ticks = c.get_beat_ticks(n_beats, sync=False)
    c.tick_shift += ticks


c.start(active=config.active_clock)


# Loading user_configuration.py from configuration folder
import importlib

if Path(f"{config.user_config_path}").is_file():
    spec = importlib.util.spec_from_file_location(
        "user_configuration", config.user_config_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    from user_configuration import *
else:
    print(f"[red]No user provided configuration file found...")


def parser(pattern: str):
    """Parse a single expression and get result"""
    parser = ListParser()
    print(parser.parse(pattern))


def parser_repl(parser_type: str):
    """Parse a single expression and get result"""
    parser = ListParser(clock=c, parser_type=parser_type)
    try:
        while True:
            p = parser._parse_debug(pattern=input("> "))
    except KeyboardInterrupt:
        pass


def lang_debug():
    """Debug mode for language dev"""
    return parser_repl(parser_type="proto")


def Pat(pattern: str, i: int = 0):
    """Generates a pattern

    Args:
        pattern (str): A pattern to be parsed
        i (int, optional): Index for iterators. Defaults to 0.

    Returns:
        int: The ith element from the resulting pattern
    """
    parser = c.parser
    result = parser.parse(pattern)
    return result[i % len(result)]


P = Pat

tx7_params = {
        "Algorithme": lambda x: sysex([67,16,1,6,x]),
        "Feedback": lambda x: sysex([67,16,1,7,x]),
        # FreqCourse
        "FreqCourseOp1": lambda x: sysex([67,16,0,128,int(x)%256]),
        "FreqCourseOp2": lambda x: sysex([67,16,0,102,int(x)%256]),
        "FreqCourseOp3": lambda x: sysex([67,16,0,60, int(x)%256]),
        "FreqCourseOp4": lambda x: sysex([67,16,0,60, int(x)%256]),
        "FreqCourseOp5": lambda x: sysex([67,16,0,39, int(x)%256]),
        "FreqCourseOp6": lambda x: sysex([67,16,0,18, int(x)%256]),
        # FreqFine
        "FreqFineOp1": lambda x: sysex([67,16,0,124,int(x)%256]),
        "FreqFineOp2": lambda x: sysex([67,16,0,103,int(x)%256]),
        "FreqFineOp3": lambda x: sysex([67,16,0,82, int(x)%256]),
        "FreqFineOp4": lambda x: sysex([67,16,0,61, int(x)%256]),
        "FreqFineOp5": lambda x: sysex([67,16,0,40, int(x)%256]),
        "FreqFineOp6": lambda x: sysex([67,16,0,19, int(x)%256]),
        # Detune
        "DetuneOp1": lambda x: sysex([67,16,0,125,int(x)%256]),
        "DetuneOp2": lambda x: sysex([67,16,0,104,int(x)%256]),
        "DetuneOp3": lambda x: sysex([67,16,0,83,int(x)%256]),
        "DetuneOp4": lambda x: sysex([67,16,0,62,int(x)%256]),
        "DetuneOp5": lambda x: sysex([67,16,0,41,int(x)%256]),
        "DetuneOp6": lambda x: sysex([67,16,0,20,int(x)%256]),
        # Level
        "LevelOp1" : lambda x: sysex([67,16,0,121,int(x)%256]),
        "LevelOp2" : lambda x: sysex([67,16,0,100,int(x)%256]),
        "LevelOp3" : lambda x: sysex([67,16,0,79,int(x)%256]),
        "LevelOp4" : lambda x: sysex([67,16,0,58,int(x)%256]),
        "LevelOp5" : lambda x: sysex([67,16,0,37,int(x)%256]),
        "LevelOp6" : lambda x: sysex([67,16,0,16,int(x)%256]),
        # LFO
        "LFOWave":  lambda x: sysex([67,16,1,14,int(x)%256]),
        "LFOSpeed": lambda x: sysex([67,16,1,9,int(x)%256]),
        "LFODelay": lambda x: sysex([67,16,1,10,int(x)%256]),
        "LFOPMD":   lambda x: sysex([67,16,1,11,int(x)%256]),
        "LFOAMD":   lambda x: sysex([67,16,1,12,int(x)%256]),
        "LFOSync":  lambda x: sysex([67,16,1,12,int(x)%256]),
        "LFOPMS":   lambda x: sysex([67,16,1,15,int(x)%256]),
        # Portamento
        "PolyRetain/MonoFingered" : lambda x: sysex([67,16,8,67,0]),
        "PolyFollow/MonoFullTime" : lambda x: sysex([67,16,8,67,1]),
        "GlissandoOffOn"          : lambda x: sysex([67,16,8,68,int(x)%256]),
        "Time"                    : lambda x: sysex([67,16,8,69,int(x)%256]),
        "Poly/Mono"               : lambda x: sysex([67,16,8,64,int(x)%256]),
}


def tx7(algo, value):
    return tx7_params[algo](int(value))

def E(step: int, maximum: int, index: int) -> bool:
    pattern = euclid(step, maximum)
    return True if pattern[index % len(pattern)] == 1 else False

def print_param(): 
    print(tx7_params.keys())

def print_scales():
    print(qualifiers.keys())
