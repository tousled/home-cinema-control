# Changelog

**English** · [Español](CHANGELOG.es.md)

The changes that make HCC better for your home cinema, in plain language.

## [Unreleased]

- **Play from Kodi.** Connect through Kodi’s HTTP remote control and use NFS or SMB libraries from
  Emby or Jellyfin. Connection tests explain authentication and network problems. Existing OPPO
  profiles stay available with their own paths. Kodi credentials are kept separately. Local Kodi
  folders, add-on sources, and equivalent Blu-ray menu behaviour are outside this release.
- **Set up the room with guided steps.** The wiring assistant prepares TV and receiver settings
  for review. The Spanish and English guides cover first playback, folder matching and optional
  room and Home Assistant setup.
- **Know what happened when you update.** A failed Portainer request shows an error. If the
  connection drops, HCC keeps checking the installed version. Version checks respect GitHub rate limits.
- **See the issues that affect playback now.** An empty Emby or Jellyfin session snapshot, or a
  client leaving the screen during OPPO playback, no longer raises a misleading device warning.

## [1.4.6] - 2026-11-15

- **Pick up where you left off.** The OPPO or Chinoppo reaches your saved position in Emby or
  Jellyfin more reliably, even if it needs a moment before it can seek. Turn on “Replay the last
  2 seconds when resuming” to ease back into a supported video file. Playback starts up to two
  seconds before where you left off. The option is off by default.
- **Keep your watch progress in sync.** HCC saves your progress more reliably when you stop or switch
  titles, and keeps your bookmark if you stop in the Blu-ray menu. When you return
  to Jellyfin, HCC avoids sending you back a screen and shows its goodbye message more reliably.
- **Resume Blu-rays even when the disc menu only offers Play.** Some discs used to start over
  even when you selected Resume in Emby or Jellyfin. With experimental Blu-ray resume enabled,
  HCC tries to pick up where you left off. To start over, choose Play from beginning in Emby
  or Jellyfin.

## [1.4.5] - 2026-11-04

- **Blu-ray movies, without playback issues.** Some movies stored as Blu-ray or UHD Blu-ray folders failed to start correctly from Jellyfin. HCC now recognizes the disc structure so they can play on your OPPO/Chinoppo.

## [1.4.4] - 2026-11-02

- **Switch movies without surprises.** Starting another title no longer shuts down the OPPO unexpectedly.
- **A safer handoff to your cinema room.** If the player or media path isn't ready, HCC avoids disruptive TV and receiver changes and leaves unsupported library playback in your original app.
- **Clearer guidance when something goes wrong.** Playback messages explain what needs attention without exposing technical details.

## [1.4.3] - 2026-10-28

- **Help shape what's next for HCC.** The new Participate section lets you vote on ideas and share suggestions whenever you choose.
- **More useful diagnostics.** Clearer information makes it easier to understand playback issues; optional technical metrics remain under your control.

## [1.4.2] - 2026-10-23

- **An easier installation and update experience.** Step-by-step guides help you install or update HCC without losing your settings.
- **A smoother start from the OPPO screen saver.** HCC dismisses the screen saver before trying to play your content.

## [1.4.1] - 2026-10-17

- **Keep your Continue Watching list intact.** HCC better preserves resume positions when playback stops or can't be started.
- **Audio and subtitles, as you selected them.** More reliable track selection from Emby and improved OPPO startup handling.
- **Get your room ready earlier.** Home Assistant can respond as soon as HCC detects that you're about to watch something.

## [1.4.0] - 2026-10-12

- **Your cinema room reacts to playback.** Connect HCC with Home Assistant to automate lights and other room effects as playback starts, pauses or ends.
- **A more reliable experience.** Improvements to playback coordination, diagnostics and the Home Assistant setup screen.

## [1.3.3] - 2026-10-09

- **STRM playback from Emby is fixed.** Titles backed by STRM files now resolve to the right media when handed off to the OPPO.

## [1.3.2] - 2026-10-09

- **More reliable media paths.** Shared folders resolve correctly even when Windows or Linux paths use different separators.

## [1.3.1] - 2026-09-17

- **Fewer interruptions during playback.** Better audio/subtitle readiness, safer media-server cleanup and clearer handling when an item can't be loaded.

## [1.3.0] - 2026-08-13

- **Trinnov Altitude joins your cinema room.** Native receiver control arrives, along with smoother LG pairing and more accurate playback detection.

## [1.2.1] - 2026-07-08

- **Better endings and faster feedback.** HCC detects the end of OPPO playback more accurately and shows clearer update status.

## [1.2.0] - 2026-07-07

- **Sony BRAVIA support arrives.** Add compatible Sony TVs to your room setup and send diagnostics more easily when you need help.

## [1.1.4] - 2026-06-30

- **More dependable SMB playback.** Fixed an issue that could leave the OPPO unresponsive after playing content from SMB shares.

## [1.1.3] - 2026-06-29

- **A voice in HCC's roadmap.** Optional feedback and usage insights help guide future improvements; receiver input detection is also better.

## [1.1.2] - 2026-06-27

- **Copy diagnostics without hassle.** The copy buttons now work in more browsers.

## [1.1.1] - 2026-06-27

- **Jellyfin compatibility and easier log sharing.** Updated Jellyfin authentication support and improved log controls on mobile.

## [1.1.0] - 2026-06-26

- **Emby and Jellyfin in one experience.** Choose your media server and configure libraries, devices and paths with a clearer setup.
- **More dependable playback on Jellyfin.** Improvements to playback notifications, session cleanup and returning from the OPPO.

## [1.0.5] - 2026-06-22

- **A smoother start to movie night.** Playback handoffs, startup messages and shared-folder cleanup are more reliable.

## [1.0.4] - 2026-06-21

- **Blu-ray endings now finish cleanly.** Watched status and OPPO playback are handled more reliably at the end of a disc.

## [1.0.3] - 2026-06-21

- **More resilient OPPO connections.** Improved browsing and network-share retries, plus smoother recovery from playback and screen-saver states.

## [1.0.2] - 2026-06-20

- **More reliable Emby setup.** Safer handling of connection details and fewer false connection errors during setup.

## [1.0.0] - 2026-06-19

- **Welcome to HCC 1.0.** A redesigned, more cinematic control experience, with clearer setup, diagnostics and release updates.

## [0.9.1] - 2026-06-18

- **Playback details at a glance.** A richer OPPO remote, current-title information and improved installation guides in both languages.

## [0.9.0] - 2026-06-18

- **A simpler path from library to player.** Guided media paths, clearer diagnostics and flexible NFS/SMB sharing.

## [0.8.1] - 2026-06-13

- **Update HCC with more confidence.** Version checks, update shortcuts and rollback guidance arrive in the status screen.

## [0.8.0] - 2026-06-13

- **A new, friendlier HCC.** Modern web interface, guided setup, local device discovery and improved mobile navigation.

## [0.7.2] - 2026-06-09

- **More reliable Docker installs.** Fixed a deployment problem affecting some Docker and Portainer setups.

## [0.7.1] - 2026-06-09

- **Better audio selection for Blu-ray discs.** HCC can select the right track after a Blu-ray menu gives way to the movie.

## [0.7.0] - 2026-06-09

- **More accurate playback progress.** Improved OPPO playback tracking and recovery when status updates are interrupted.

## [0.6.1] - 2026-06-06

- **Logs appear when you need them.** Docker and Portainer now show HCC log entries without unnecessary delays.

## [0.6.0] - 2026-06-06

- **OPPO and Emby stay closer in sync.** Optional playback tracking reports play, pause and audio/subtitle changes.

## [0.5.1] - 2026-06-01

- **No more waiting on a finished movie.** HCC detects the end of playback more reliably and restores the room.

## [0.5.0] - 2026-05-31

- **Your devices, working together.** Playback, TV and receiver switching, remote commands and room recovery become part of one flow.

## [0.4.0] - 2026-05-23

- **More receiver choices.** Support for Denon, Marantz, NAD, Onkyo, Yamaha and script-based control.

## [0.3.0] - 2026-05-23

- **More accurate stopping and subtitles.** Better OPPO state detection avoids lost playback progress and subtitle confusion.

## [0.2.0] - 2026-05-22

- **HCC comes to Docker and Portainer.** Persistent settings and simpler NAS deployments.

## [0.1.1] - 2026-05-22

- **A small maintenance update.** Cleaner diagnostic logs with better protection for sensitive information.

## [0.1.0] - 2026-05-22

- **The starting point for HCC.** Initial working version and Emby playback connection fixes.
