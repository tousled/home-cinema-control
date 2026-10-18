# Issue migration map

Issue migration is intentionally **not executed** in this phase. The source
repository still owns the historical issue tracker, and the public repository
has not received any issue, comment, or notification changes.

## Definitive mapping

The transfers are complete. Destination URLs below use the final repository
name that is planned for the later cutover.

| Original issue | Original state | Destination issue | Destination state | Original URL | Final URL |
| --- | --- | --- | --- | --- | --- |
| `#90` | open | `#1` | open | [old #90](https://github.com/tousled/home-cinema-control/issues/90) | [new #1](https://github.com/tousled/home-cinema-control/issues/1) |
| `#89` | closed | `#2` | closed | [old #89](https://github.com/tousled/home-cinema-control/issues/89) | [new #2](https://github.com/tousled/home-cinema-control/issues/2) |
| `#88` | closed | `#3` | closed | [old #88](https://github.com/tousled/home-cinema-control/issues/88) | [new #3](https://github.com/tousled/home-cinema-control/issues/3) |
| `#87` | closed | `#4` | closed | [old #87](https://github.com/tousled/home-cinema-control/issues/87) | [new #4](https://github.com/tousled/home-cinema-control/issues/4) |
| `#86` | closed | `#5` | closed | [old #86](https://github.com/tousled/home-cinema-control/issues/86) | [new #5](https://github.com/tousled/home-cinema-control/issues/5) |
| `#85` | closed | `#6` | closed | [old #85](https://github.com/tousled/home-cinema-control/issues/85) | [new #6](https://github.com/tousled/home-cinema-control/issues/6) |
| `#82` | closed | `#7` | closed | [old #82](https://github.com/tousled/home-cinema-control/issues/82) | [new #7](https://github.com/tousled/home-cinema-control/issues/7) |
| `#66` | closed | `#8` | closed | [old #66](https://github.com/tousled/home-cinema-control/issues/66) | [new #8](https://github.com/tousled/home-cinema-control/issues/8) |

The final URLs above are prepared for the later rename from
`home-cinema-control-public` to `home-cinema-control`. They can only be
verified at those exact paths after that rename.

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

The completed operation transferred `#90` while open. Each closed issue was
reopened, transferred, and immediately closed in the destination. Authors,
bodies, comments, and labels were checked against the pre-transfer inventory.
GitHub automatically rewrote a few issue references in transferred bodies,
either qualifying them with the historical repository or resolving them to a
destination issue number; no substantive body text was lost.
The operation may generate notifications; that is accepted for this project.

Release notes and public history currently retain original issue URLs. After
the mapping is known, those links must be updated to the destination URLs in
the recreated release bodies and any public documents where appropriate. Old
URLs must not be treated as the permanent link strategy because the repository
name will later be reused.
