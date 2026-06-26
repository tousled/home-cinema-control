from home_cinema_control.devices.av.adapters.denon_marantz import (
    BaseDenonMarantzAvReceiver,
)


class DenonAvReceiver(BaseDenonMarantzAvReceiver):
    receiver_name = "Denon"

    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "CD", "Param": "SICD\n"},
            {"Id": 2, "Name": "DVD", "Param": "SIDVD\n"},
            {"Id": 3, "Name": "Blu-ray (BD)", "Param": "SIBD\n"},
            {"Id": 4, "Name": "TV AUDIO(TV)", "Param": "SITV\n"},
            {"Id": 5, "Name": "CBL/SAT", "Param": "SISAT/CBL\n"},
            {"Id": 6, "Name": "MEDIA PLAYER", "Param": "SIMPLAY\n"},
            {"Id": 7, "Name": "GAME", "Param": "GAME\n"},
        ]
