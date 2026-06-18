from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from home_cinema_control.devices.oppo.models import OppoCommandResponse


@dataclass(frozen=True)
class OppoMountedShare:
    server: str
    folder: str
    mount_path: str
    is_nfs: bool


def parse_mounted_share_response(
    response: OppoCommandResponse,
    *,
    server: str,
    folder: str,
    is_nfs: bool,
) -> tuple[dict[str, Any], OppoMountedShare | None]:
    payload = dict(response.payload)

    if not response.is_successful:
        return _failed_payload_from_response(response, payload), None

    mount_path_key = "nfsMntPath" if is_nfs else "cifsMntPath"
    mount_path = payload.get(mount_path_key)

    if not mount_path:
        payload["success"] = False
        payload["retInfo"] = (
            f"OPPO mount response did not include {mount_path_key}. "
            f"Cannot safely continue without the real mount path."
        )
        return payload, None

    return payload, OppoMountedShare(
        server=server,
        folder=folder,
        mount_path=str(mount_path),
        is_nfs=is_nfs,
    )


def _failed_payload_from_response(
    response: OppoCommandResponse,
    payload: dict[str, Any],
) -> dict[str, Any]:
    payload["success"] = False

    if payload.get("retInfo"):
        return payload

    if response.parse_error:
        payload["retInfo"] = response.parse_error
        return payload

    if hasattr(response, "error_message") and response.error_message:
        payload["retInfo"] = response.error_message
        return payload

    payload["retInfo"] = "OPPO command did not report success"
    return payload