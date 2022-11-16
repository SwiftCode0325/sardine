from rich import print
from rich.panel import Panel
import asyncio
import sys
from sys import argv
import importlib
from pathlib import Path
import os
try:
    import uvloop
except ImportError:
    print("[yellow]UVLoop is not installed. Not supported on Windows![/yellow]")
    print("[yellow]Rhythm accuracy may be impacted[/yellow]")
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    uvloop.install()

from .fish_bowl import FishBowl
from .clock.Time import Time
from .clock.InternalClock import Clock
from .clock.LinkClock import LinkClock
from .sequences.SardineParser.ListParser import ListParser
from .handlers import (
    SuperColliderHandler,
    SuperDirtHandler,
    MidiHandler, 
    OSCHandler)
from .utils.Messages import (sardine_intro, config_line_printer)

from .io.UserConfig import (
    read_user_configuration,
    pretty_print_configuration_file)
config = read_user_configuration()

#| INITIALISATION |#

# Reading user configuration
config = read_user_configuration()

hook_path = argv[0]
if "__main__.py" in hook_path:
    os.environ["SARDINE_INIT_SESSION"] = "YES"

if (
    os.getenv("SARDINE_INIT_SESSION") is not None
    and os.getenv("SARDINE_INIT_SESSION") == "YES"
):
    print(sardine_intro)
    print(config_line_printer(config))

    # Load user config
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


    # Real initialisation takes place here ############################
    bowl = FishBowl(time=Time())
    time = bowl.time # passage of time
    bowl.clock.tempo, bowl.clock._beats_per_bar = config.bpm, config.beats

    # Adding a parser
    bowl.swap_parser(ListParser)

    # Adding Senders
    bowl.add_handler(MidiHandler())
    bowl.add_handler(OSCHandler())
    bowl.add_handler(SuperColliderHandler(name="Custom SuperCollider Connexion"))
    bowl.add_handler(SuperDirtHandler())

    # Start clock
    bowl.clock.start()
