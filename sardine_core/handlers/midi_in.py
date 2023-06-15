from collections import deque
from dataclasses import dataclass
from typing import Optional, Union

import mido
from mido import Message, get_input_names, open_input, parse_string_stream
from ..logger import print

from ..base.handler import BaseHandler

__all__ = ("MidiInHandler", "ControlTarget", "NoteTarget")


@dataclass
class ControlTarget:
    control: int
    channel: int


@dataclass
class NoteTarget:
    channel: int


class MidiInHandler(BaseHandler):
    """
    MIDI-In Listener: listen to incoming MIDI events from a selected port.
    Useful for mapping controllers to control / interact with Sardine.

    The incoming messages are stored in a queue and retrieved in FIFO order.
    """

    def __init__(
        self,
        target: Union[ControlTarget, NoteTarget, None] = None,
        port_name: Optional[str] = None,
    ):
        super().__init__()
        self.target = target
        self.queue = deque(maxlen=20)
        self._last_item: Optional[Message] = None
        self._last_value = 0

        if port_name:
            try:
                self._input = open_input(port_name)
                self._input.callback = self._callback
            except Exception:
                error_message = f"Couldn't listen on port {port_name}"
                raise OSError(error_message)
        else:
            try:
                self._input = open_input()
                self._input.callback = self._callback
                listened_port = mido.get_input_names()[0]
            except Exception:
                raise OSError(f"Couldn't listen on port {port_name}")

    def __str__(self):
        """String representation of the MIDI Listener"""
        return f"<MidiListener: {self._input} target={self.target}>"

    def _callback(self, message):
        """Callback for MidiListener Port."""
        # Add more filters
        if message:
            if isinstance(self.target, ControlTarget):
                if not (
                    message.type == "control_change"
                    and message.control == self.target.control
                    and message.channel == self.target.channel
                ):
                    return
            elif isinstance(self.target, NoteTarget):
                if not message.channel == self.target.channel:
                    return

        self.queue.appendleft(message)

    def _extract_value(self, message: Union[mido.Message, None]) -> Union[Message, int]:
        """
        Given a mido.Message, extract needed value based on message type
        """

        if message is None:
            return 0

        mtype = message.type
        if mtype == "control_change":
            value = message.value
        elif mtype in ["note_on", "note_off"]:
            value = message.note
        else:
            return message
        return value

    def get(self, last=False):
        """Get an item from the MidiListener event queue. If last is True, return the last element that was inserted and
        clear the queue."""
        target = self.target

        if self.queue:
            if last:
                self._last_item = self.queue.popleft()
                self.queue.clear()
            else:
                self._last_item = self.queue.pop()
        else:
            self._last_item = self._last_item

        return self._extract_value(self._last_item)

    def getlast(self):
        """Get the last item from the MidiListener event queue and clear the queue. This is mostly useful to get latest
        value of a control, but probably not for notes."""
        return self.get(last=True)

    def inspect_queue(self):
        print(f"{self.queue}")

    def kill(self):
        """Close the MIDIListener"""
        self._input.close()
