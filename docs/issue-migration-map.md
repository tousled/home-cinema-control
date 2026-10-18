# Issue migration map

Issue migration is intentionally **not executed** in this phase. The source
repository still owns the historical issue tracker, and the public repository
has not received any issue, comment, or notification changes.

## Original issues

| Original | State | Title | Comments | Planned handling |
| --- | --- | --- | ---: | --- |
| [#90](https://github.com/tousled/home-cinema-control/issues/90) | open | Feature proposal: give each HCC installation its own device id (and an optional name) in Emby/Jellyfin | 0 | Transfer directly while open |
| [#89](https://github.com/tousled/home-cinema-control/issues/89) | closed | OPPO playback that starts behind the screensaver times out and is stopped | 2 | Reopen, transfer, close in destination |
| [#88](https://github.com/tousled/home-cinema-control/issues/88) | closed | OPPO path wizard hides folders with one- or two-character names (BR, HD) | 0 | Reopen, transfer, close in destination |
| [#87](https://github.com/tousled/home-cinema-control/issues/87) | closed | Picking a non-primary version of a movie is ignored: HCC checks the primary version's path | 0 | Reopen, transfer, close in destination |
| [#86](https://github.com/tousled/home-cinema-control/issues/86) | closed | Si el traspaso al reproductor falla, la película pierde su punto de reanudación | 1 | Reopen, transfer, close in destination |
| [#85](https://github.com/tousled/home-cinema-control/issues/85) | closed | Una película parada desde HCC desaparece de «Continuar viendo» | 1 | Reopen, transfer, close in destination |
| [#82](https://github.com/tousled/home-cinema-control/issues/82) | closed | Emby: las películas de una biblioteca con «Shared network folder» no se envían al OPPO | 0 | Reopen, transfer, close in destination |
| [#66](https://github.com/tousled/home-cinema-control/issues/66) | closed | Emby STRM-backed items are sometimes sent to OPPO as .strm instead of the playable media extension | 2 | Reopen, transfer, close in destination |

## Target preparation

The target repository should receive the equivalent labels before issue
transfer. The audited source labels and colors are:

| Label | Color | Description |
| --- | --- | --- |
| `bug` | `d73a4a` | Something isn't working |
| `documentation` | `0075ca` | Improvements or additions to documentation |
| `duplicate` | `cfd3d7` | This issue or pull request already exists |
| `enhancement` | `a2eeef` | New feature or request |
| `good first issue` | `7057ff` | Good for newcomers |
| `help wanted` | `008672` | Extra attention is needed |
| `invalid` | `e4e669` | This doesn't seem right |
| `question` | `d876e3` | Further information is requested |
| `wontfix` | `ffffff` | This will not be worked on |

The audit found no milestones to recreate.

## Later execution notes

The intended later sequence is to transfer `#90` while open, then handle each
closed issue by reopening it, transferring it, and closing it in the target.
This preserves the conversation, authors, and participants if GitHub accepts
the operation. It may generate notifications; that is accepted for this
project. The exact destination issue numbers must be recorded after transfer.

Release notes and public history currently retain original issue URLs. After
the mapping is known, those links must be updated to the destination URLs in
the recreated release bodies and any public documents where appropriate. Old
URLs must not be treated as the permanent link strategy because the repository
name will later be reused.
