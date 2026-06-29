from home_cinema_control.config.models import AvInputSource
from home_cinema_control.devices.av.adapters.denon_marantz import (
    BaseDenonMarantzAvReceiver,
)


class MarantzAvReceiver(BaseDenonMarantzAvReceiver):
    receiver_name = "Marantz"

    def _fallback_inputs(self) -> list[AvInputSource]:
        return [
            AvInputSource(id=1, name="CD",      param="SICD\n"),
            AvInputSource(id=2, name="DVD",     param="SIDVD\n"),
            AvInputSource(id=3, name="BD",      param="SIBD\n"),
            AvInputSource(id=4, name="TV",      param="SITV\n"),
            AvInputSource(id=5, name="SAT/CBL", param="SISAT/CBL\n"),
            AvInputSource(id=6, name="MPLAY",   param="SIMPLAY\n"),
            AvInputSource(id=7, name="GAME",    param="SIGAME\n"),
            AvInputSource(id=8, name="AUX1",    param="SIAUX1\n"),
            AvInputSource(id=9, name="AUX2",    param="SIAUX2\n"),
        ]
