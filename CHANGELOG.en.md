# Changelog

**English** · [Español](CHANGELOG.md)

The changes that make HCC better for your home cinema, in plain language.

## [Unreleased]

### Improved

- **Follow setup on screen.** Installation and setup guides show current screenshots in English and Spanish, with
  Samsung connection, HDMI and TV application steps illustrated separately.

## [1.5.0] - 2026-11-18

### Added

- **Samsung joins your movie nights (experimental).** HCC starts coordinating your TV with the rest of your home cinema, so you can enjoy your movies with fewer steps. If you have a Samsung TV, you can try this new feature and help us improve its integration with your model and others.
- **Kodi comes to HCC.** You can now play movies and shows from Emby or Jellyfin with Kodi using NFS or SMB network shares. HCC coordinates playback with your TV and AV receiver, lets you control Kodi through its web remote, and guides you through setup. Installation guides are available in English and Spanish.
- **Turn your OPPO on and off automatically.** HCC can power on your OPPO or Chinoppo when you start a movie from Emby or Jellyfin, then power it off when you finish. Choose how long HCC waits before switching it off; starting another playback during that time cancels the pending shutdown. This feature is experimental and depends on your player's capabilities.
- **Set up your home cinema more easily.** Guided setup helps you connect and configure your devices, including the TV, AV receiver and Home Assistant. You can review settings and cancel before saving them.

### Improved

- **Diagnostics that tell you what's happening.** You can now view multiple issues at once, see which need attention, and distinguish active, resolved and dismissed issues. The history keeps information about previous problems.
- **Follow the progress of updates.** When updating HCC from the app, you can see a countdown, how many times the new version has been checked, and whether HCC is responding. This makes it easier to tell whether an update has finished or is still awaiting confirmation.
- **More reliable updates, even if the connection drops.** If Portainer rejects an update request, HCC tells you. If the app temporarily stops responding during the update, HCC keeps checking the installed version to confirm the outcome.
- **Skip forward and back in your Blu-rays without losing progress.** Use the progress bar in Emby or Jellyfin to seek within a movie when the disc and player support it. HCC also protects your saved position while Blu-ray menus are displayed, so you don't lose your place before returning to the movie.
- **Set up HCC at your own pace.** Prepare paths and Kodi connection details while devices are off, and continue without
  completing every check immediately. HCC explains what remains pending and which functions are limited; saving details
  does not verify a connection or path.
- **Find your devices with fewer steps.** Filter suggested addresses by name, IP, or manufacturer to choose your TV or
  receiver. If discovery cannot reach your home network, HCC explains the limitation and lets you enter the address
  manually.
- **Set up HCC more comfortably on mobile or with a keyboard.** Forms and dropdowns work better with touch and keyboard
  controls, without losing your selection or focus. Lists fit the available space, mobile navigation is easier to find,
  and dark-theme text has stronger contrast.

### Fixed

- **Switch titles safely, even when paused.** HCC finishes the previous playback before starting the next one, including when the player is still loading. Requests arriving during a switch cannot start another playback in parallel.
- **Switch between movies with the same title and between versions of one movie.** HCC distinguishes content and
  versions by the identifiers supplied by Emby or Jellyfin. It recognizes another selected version even when the display
  title or file name matches, through both the monitored client and cast to Home Cinema Control.
- **Fewer incorrect Emby and Jellyfin warnings.** When the server temporarily returns an empty session list, HCC no longer shows a misleading missing-device warning.
- **No false alarms when leaving the app.** If you leave Emby or Jellyfin while the OPPO keeps playing, HCC no longer incorrectly warns that the device has disappeared.
- **Correct audio and subtitles when choosing another Jellyfin version.** When a movie has multiple versions, HCC uses the audio and subtitle tracks from the file you selected, rather than mistakenly using tracks from a different version.

### Acknowledgements

- **Thank you, `@vicsuaes`.** His contribution was essential to discovering how Samsung control actually behaves on a real S90C TV. Through repeated physical tests and diagnostic scripts, we could document authorization, state readback, verified switching to HDMI3, errors for other inputs, and the different identifiers and methods used to detect versus launch Tizen applications. He also continued testing release candidates and helped us diagnose compatibility problems.

## [1.4.6] - 2026-11-15

### Added

- **Pick up the thread, two seconds earlier.** Turn on “Replay the last 2 seconds when resuming” to ease back
  into a supported video file. Playback starts up to two seconds before where you left off. The option is off
  by default.

### Fixed

- **Pick up where you left off.** The OPPO or Chinoppo reaches your saved position in Emby or
  Jellyfin more reliably, even if it needs a moment before it can seek.
- **Keep your watch progress in sync.** HCC saves your progress more reliably when you stop or switch
  titles, and keeps your bookmark if you stop in the Blu-ray menu. When you return
  to Jellyfin, HCC avoids sending you back a screen and shows its goodbye message more reliably.
- **Resume Blu-rays even when the disc menu only offers Play.** Some discs used to start over
  even when you selected Resume in Emby or Jellyfin. With experimental Blu-ray resume enabled,
  HCC tries to pick up where you left off. To start over, choose Play from beginning in Emby
  or Jellyfin.

### Acknowledgements

- **Thank you, `@bibizaza`.** Reported that Blu-ray ISO playback restarted at the disc menu despite a saved Emby resume point. The detailed report helped us investigate the cause, and after 1.4.6 shipped, they confirmed on their Chinoppo that playback resumed at the saved position.

## [1.4.5] - 2026-11-04

### Fixed

- **Blu-ray movies, without playback issues.** Some movies stored as Blu-ray or UHD Blu-ray folders failed to start
  correctly from Jellyfin. HCC now recognizes the disc structure so they can play on your OPPO/Chinoppo.

### Acknowledgements

- **Thank you, `@ThorJane86`.** Provided reproducible evidence that HCC could not open Blu-ray and UHD Blu-ray folders from Jellyfin on a Chinoppo. Their report led to the fix in 1.4.5.

## [1.4.4] - 2026-11-02

### Improved

- **A safer handoff to your cinema room.** If the player or media path isn't ready, HCC avoids disruptive TV and
  receiver changes and leaves unsupported library playback in your original app.
- **Clearer guidance when something goes wrong.** Playback messages explain what needs attention without exposing
  technical details.

### Fixed

- **Switch movies without surprises.** Starting another title no longer shuts down the OPPO unexpectedly.

## [1.4.3] - 2026-10-28

### Added

- **Help shape what's next for HCC.** The new Participate section lets you vote on ideas and share suggestions whenever
  you choose.

### Improved

- **More useful diagnostics.** Clearer information makes it easier to understand playback issues; optional technical
  metrics remain under your control.

## [1.4.2] - 2026-10-23

### Improved

- **An easier installation and update experience.** Step-by-step guides help you install or update HCC without losing
  your settings.

### Fixed

- **A smoother start from the OPPO screen saver.** HCC dismisses the screen saver before trying to play your content.

### Acknowledgements

- **Thank you, `@revin34`.** Identified the OPPO screen saver issue during playback startup, investigated its cause and proposed a solution that helped make startup more reliable.

## [1.4.1] - 2026-10-17

### Added

- **Get your room ready earlier.** Home Assistant can respond as soon as HCC detects that you're about to watch
  something.

### Improved

- **Audio and subtitles, as you selected them.** More reliable track selection from Emby and improved OPPO startup
  handling.

### Fixed

- **Keep your Continue Watching list intact.** HCC better preserves resume positions when playback stops or can't be
  started.

### Acknowledgements

- **Thank you, `@revin34`.** Their detailed reports, investigations and suggested fixes for OPPO handoffs, media paths and playback progress helped protect saved resume points and keep Continue Watching working.

## [1.4.0] - 2026-10-12

### Added

- **Your cinema room reacts to playback.** Connect HCC with Home Assistant to automate lights and other room effects as
  playback starts, pauses or ends.

### Improved

- **A more reliable experience.** Improvements to playback coordination, diagnostics and the Home Assistant setup
  screen.

## [1.3.3] - 2026-10-09

### Fixed

- **STRM playback from Emby is fixed.** Titles backed by STRM files now resolve to the right media when handed off to
  the OPPO.

### Acknowledgements

- **Thank you, `@231197671-stack`.** Carefully documented when Emby STRM-backed items were being sent to the OPPO with unplayable filenames, clarifying the difference between mapping paths and playable media that guided the fix.

## [1.3.2] - 2026-10-09

### Fixed

- **More reliable media paths.** Shared folders resolve correctly even when Windows or Linux paths use different
  separators.

## [1.3.1] - 2026-09-17

### Improved

- **Fewer interruptions during playback.** Better audio/subtitle readiness, safer media-server cleanup and clearer
  handling when an item can't be loaded.

## [1.3.0] - 2026-08-13

### Added

- **Trinnov Altitude joins your cinema room.** Native receiver control arrives, along with smoother LG pairing and more
  accurate playback detection.

## [1.2.1] - 2026-07-08

### Improved

- **Better endings and faster feedback.** HCC detects the end of OPPO playback more accurately and shows clearer update
  status.

## [1.2.0] - 2026-07-07

### Added

- **Sony BRAVIA support arrives.** Add compatible Sony TVs to your room setup and send diagnostics more easily when you
  need help.

## [1.1.4] - 2026-06-30

### Fixed

- **More dependable SMB playback.** Fixed an issue that could leave the OPPO unresponsive after playing content from SMB
  shares.

## [1.1.3] - 2026-06-29

### Added

- **A voice in HCC's roadmap.** Optional feedback and usage insights help guide future improvements; receiver input
  detection is also better.

## [1.1.2] - 2026-06-27

### Fixed

- **Copy diagnostics without hassle.** The copy buttons now work in more browsers.

## [1.1.1] - 2026-06-27

### Fixed

- **Jellyfin compatibility and easier log sharing.** Updated Jellyfin authentication support and improved log controls
  on mobile.

## [1.1.0] - 2026-06-26

### Added

- **Emby and Jellyfin in one experience.** Choose your media server and configure libraries, devices and paths with a
  clearer setup.

### Fixed

- **More dependable playback on Jellyfin.** Improvements to playback notifications, session cleanup and returning from
  the OPPO.

## [1.0.5] - 2026-06-22

### Improved

- **A smoother start to movie night.** Playback handoffs, startup messages and shared-folder cleanup are more reliable.

## [1.0.4] - 2026-06-21

### Fixed

- **Blu-ray endings now finish cleanly.** Watched status and OPPO playback are handled more reliably at the end of a
  disc.

## [1.0.3] - 2026-06-21

### Improved

- **More resilient OPPO connections.** Improved browsing and network-share retries, plus smoother recovery from playback
  and screen-saver states.

## [1.0.2] - 2026-06-20

### Fixed

- **More reliable Emby setup.** Safer handling of connection details and fewer false connection errors during setup.

## [1.0.0] - 2026-06-19

### Added

- **Welcome to HCC 1.0.** A redesigned, more cinematic control experience, with clearer setup, diagnostics and release
  updates.

## [0.9.1] - 2026-06-18

### Added

- **Playback details at a glance.** A richer OPPO remote, current-title information and improved installation guides in
  both languages.

## [0.9.0] - 2026-06-18

### Added

- **A simpler path from library to player.** Guided media paths, clearer diagnostics and flexible NFS/SMB sharing.

## [0.8.1] - 2026-06-13

### Added

- **Update HCC with more confidence.** Version checks, update shortcuts and rollback guidance arrive in the status
  screen.

## [0.8.0] - 2026-06-13

### Added

- **A new, friendlier HCC.** Modern web interface, guided setup, local device discovery and improved mobile navigation.

## [0.7.2] - 2026-06-09

### Fixed

- **More reliable Docker installs.** Fixed a deployment problem affecting some Docker and Portainer setups.

## [0.7.1] - 2026-06-09

### Fixed

- **Better audio selection for Blu-ray discs.** HCC can select the right track after a Blu-ray menu gives way to the
  movie.

## [0.7.0] - 2026-06-09

### Improved

- **More accurate playback progress.** Improved OPPO playback tracking and recovery when status updates are interrupted.

## [0.6.1] - 2026-06-06

### Fixed

- **Logs appear when you need them.** Docker and Portainer now show HCC log entries without unnecessary delays.

## [0.6.0] - 2026-06-06

### Added

- **OPPO and Emby stay closer in sync.** Optional playback tracking reports play, pause and audio/subtitle changes.

## [0.5.1] - 2026-06-01

### Fixed

- **No more waiting on a finished movie.** HCC detects the end of playback more reliably and restores the room.

## [0.5.0] - 2026-05-31

### Added

- **Your devices, working together.** Playback, TV and receiver switching, remote commands and room recovery become part
  of one flow.

## [0.4.0] - 2026-05-23

### Added

- **More receiver choices.** Support for Denon, Marantz, NAD, Onkyo, Yamaha and script-based control.

## [0.3.0] - 2026-05-23

### Fixed

- **More accurate stopping and subtitles.** Better OPPO state detection avoids lost playback progress and subtitle
  confusion.

## [0.2.0] - 2026-05-22

### Added

- **HCC comes to Docker and Portainer.** Persistent settings and simpler NAS deployments.

## [0.1.1] - 2026-05-22

### Improved

- **A small maintenance update.** Cleaner diagnostic logs with better protection for sensitive information.

## [0.1.0] - 2026-05-22

### Added

- **The starting point for HCC.** Initial working version and Emby playback connection fixes.
