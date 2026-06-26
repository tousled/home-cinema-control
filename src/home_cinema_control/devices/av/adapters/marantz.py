from home_cinema_control.devices.av.adapters.denon_marantz import (
    BaseDenonMarantzAvReceiver,
)


class MarantzAvReceiver(BaseDenonMarantzAvReceiver):
    receiver_name = "Marantz"

    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "CD", "Param": "SICD\n"},
            {"Id": 2, "Name": "DVD", "Param": "SIDVD\n"},
            {"Id": 3, "Name": "Blu-ray (BD)", "Param": "SIBD\n"},
            {"Id": 4, "Name": "TV AUDIO(TV)", "Param": "SITV\n"},
            {"Id": 5, "Name": "CBL/SAT", "Param": "SISAT/CBL\n"},
            {"Id": 5, "Name": "SAT", "Param": "SISAT\n"},
            {"Id": 5, "Name": "PEPE", "Param": "SICBL\n"},
            {"Id": 6, "Name": "GAME", "Param": "SIGAME\n"},
        ]
