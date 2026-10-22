# Connect your media folders to HCC

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Start HCC setup](getting-started.en.md) · [Español](configurar-rutas.md)

**If your OPPO/Chinoppo can already open your movie folders**, go straight to the steps below. HCC connects the folder Emby/Jellyfin sees to the folder your player sees.

If you still need to prepare your **NAS, PC, Raspberry Pi or shared folders**, start with the [AVPasión Xnoppo guide](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867) and return once the player can browse your folder.

## The usual path

1. Open **Media Paths** in HCC. You will see the libraries already configured in Emby or Jellyfin.
2. Choose a library, such as **Movies**, and the network folder that the OPPO can open.
3. Choose **SMB** or **NFS** — use whichever is already working when you browse files on the OPPO.
4. Press **Test path**, then save it if HCC confirms it works.

Repeat for any other library that should play through the OPPO. **A verified path** means HCC successfully tested that folder.

If the test fails, you can find the specific checks and screenshots below. You don't need them unless you get stuck.

## Screenshots and help

## 7. Media Paths: The Important Part

This is the critical setup step because it solves the real problem: Emby knows where the movie lives on the server, but
the OPPO/Chinoppo needs to reach that same movie as a NAS network share.

Think of HCC as a path translator:

```text
Emby sees:        /volume1/Video/Movies/Dune (2021).mkv
OPPO over NFS:    volume1/Video/Movies/Dune (2021).mkv
OPPO over SMB:    Video/Movies/Dune (2021).mkv
HCC saves:        this library uses this OPPO path and this protocol
```

If Emby has **Shared network folder** configured, it can report an alternate network path during playback instead of
the library path. HCC automatically translates it back to Emby's canonical path before applying the OPPO mapping, so
you do not need a second mapping for the alternate path. Jellyfin does not currently expose an equivalent field in its
API; map the canonical path returned in its `Locations`.

Do not guess these paths. NAS vendors, NFS, and SMB do not always expose the same names. HCC starts from the active
provider's libraries, asks for the equivalent player-visible path, and tests it before a real viewing session. The
screen shows an Emby/Jellyfin badge so you can tell which server you are mapping.

<p align="center">
  <img src="../assets/screenshots/install/04-media-paths-overview.png" alt="HCC Media Paths assistant overview" width="860"/>
</p>

### 7.1 Create Emby Libraries First

Before opening HCC, Emby should already have scanned libraries: Movies, TV Shows, Concerts, or whatever you use. In
Emby,
a library groups one or more physical folders. HCC detects those libraries and paths, but it does not create the library
for you.

Typical Emby path:

```text
Emby Dashboard -> Library -> Add Media Library
```

Emby's official [Library Setup](https://emby.media/support/articles/Library-Setup.html) covers this step. Its
[Quick Start](https://emby.media/support/articles/Quick-Start.html) also recommends separating media by type, such as
Movies, TV Shows, or Music.

When done, go to HCC and use **Reload libraries** in Media Paths. If a library does not appear, fix Emby first instead
of typing paths blindly.

### 7.2 Choose Which Libraries HCC Should Intercept

Not everything in Emby has to go through the OPPO. You can leave music, documentaries, tests, or lightweight libraries
on the normal Emby playback path.

The screen shows detected libraries and lets you enable only the ones you want HCC to control. The rest keep playing
through the normal Emby flow.

<p align="center">
  <img src="../assets/screenshots/install/05-media-paths-library-filter.png" alt="Intercepted libraries selection in Home Cinema Control" width="860"/>
</p>

### 7.3 Prepare NFS Or SMB/CIFS On The NAS

HCC does not configure NAS permissions. The OPPO/Chinoppo must be able to browse the share from its own network menu.

For NFS:

- enable NFS on the NAS;
- export the media folder;
- allow access from the player IP;
- check read permissions;
- confirm from the OPPO that the share appears and you can browse to the library folder.

For SMB/CIFS:

- enable SMB on the NAS;
- share the media folder;
- create or choose a user with read permission;
- save username and password in HCC if the share is not guest-accessible;
- confirm from the OPPO that you can browse to the folder.

When you use SMB/CIFS, HCC keeps credentials in the same Media Paths screen so you do not have to jump between screens
or edit files.

<p align="center">
  <img src="../assets/screenshots/install/07-media-paths-smb-credentials.png" alt="SMB credentials in the Home Cinema Control path assistant" width="860"/>
</p>

For shared folders on a NAS, PC or Raspberry Pi, see the [AVPasión guide](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867). This page covers the setup within HCC.

### 7.4 Find The Path As The OPPO Sees It

This step prevents most failures. Do not copy only the Emby path. Open the OPPO/Chinoppo network browser and note how
the folder appears there.

Common examples:

| Emby may see            | OPPO may see                |
|-------------------------|-----------------------------|
| `/volume1/Video/Movies` | NFS: `volume1/Video/Movies` |
| `/volume1/Video/Movies` | SMB: `Video/Movies`         |
| `/mnt/media/Movies`     | SMB: `NAS/Movies`           |
| `D:\Movies` on Windows  | SMB: `Server/Movies`        |

If you are unsure whether to use NFS or SMB, start with the protocol that already works manually from the player. You
can
add another mapping with another protocol later if a specific library needs it.

### 7.5 Create And Test The Mapping In HCC

In **Media Paths**, work library by library:

1. Click **Reload libraries** to load the current Emby libraries.
2. Select the library you want HCC to intercept.
3. Review the **server path** HCC read from Emby.
4. Choose `nfs` or `cifs` for that library.
5. Enter or select the **OPPO path** exactly as the player sees it.
6. If you use SMB with a user, fill in SMB credentials.
7. Click **Test path**.
8. Save when the route is verified.

HCC joins mappings as paths rather than literal text: the **OPPO path** may or may not end with `/`, and Windows-style
Emby paths such as `Z:\` are normalized automatically. For example, `//192.168.1.149/Z` plus
`HD-Olimpo/Movie` produces `//192.168.1.149/Z/HD-Olimpo/Movie`.

<p align="center">
  <img src="../assets/screenshots/install/06-media-paths-nfs-mapping.png" alt="Verified NFS mapping between Emby and OPPO" width="860"/>
</p>

State meanings:

| State    | What to do                                                                    |
|----------|-------------------------------------------------------------------------------|
| Verified | The player mounted this route successfully.                                   |
| Pending  | Something changed and the route needs another test.                           |
| Review   | The mapping exists, but related setup changed. Test again.                    |
| Error    | HCC could not mount the route. Read the suggestion and filter logs by errors. |

<p align="center">
  <img src="../assets/screenshots/install/08-media-paths-states.png" alt="Route state legend for verified, pending, and error states" width="860"/>
</p>

### 7.6 When To Use Manual Mode

Manual mode exists for real edge cases, not as a return to the old workflow:

- Emby does not return the expected folder;
- a library combines multiple physical folders;
- the NAS exposes different names through NFS and SMB;
- you want a test route before touching the main library;
- you are migrating from an older setup and want to review each mapping.

The important improvement is that manual mode is no longer “type something and hope”: you can test the mount, read the
diagnostic, and save only when you know which route works.

<p align="center">
  <img src="../assets/screenshots/install/09-media-paths-manual.png" alt="Manual path mapping mode in Home Cinema Control" width="860"/>
</p>

### 7.7 Mapping Concepts

| Field       | Meaning                                                         |
|-------------|-----------------------------------------------------------------|
| Server path | Physical path reported by Emby for the library.                 |
| OPPO path   | NFS or SMB/CIFS path visible from the player's network browser. |
| Protocol    | `nfs` or `cifs`, selected for each mapping.                     |
| Verified    | HCC has confirmed that the player can mount the path.           |

HCC does not silently switch between SMB and NFS. A mapping configured as SMB is tested and played over SMB; a mapping
configured as NFS uses NFS.

HCC checks complete directory names: `/media/Movies` matches `/media/Movies/Alien.mkv`, but not
`/media/Movies-Old/Alien.mkv`. If paths are nested, such as `/media/Movies` and `/media/Movies/4K`, HCC uses the most
specific one. That exact path must be verified; HCC does not try a broader path or send an unverified route to the OPPO.
When playback is blocked, the Status screen explains which path is missing or needs to be tested and saved.

If an item has multiple versions, HCC uses the version the user selected in Emby or Jellyfin. The server identifies that
version with `MediaSourceId`; HCC finds the matching path in `MediaSources` and applies the mapping to that path instead
of always assuming the primary version's path. If the server does not return an exact match, HCC keeps the primary item
path as a compatible fallback.

### 7.8 Why This Step Matters

Emby or Jellyfin and the OPPO may refer to the same content with different paths. The path known by the media server
is not always the path the player can open from the network.

A verified mapping tells HCC exactly:

- which folder the OPPO must mount;
- which protocol it must use;
- which libraries should go through the player;
- which configuration worked before a real playback starts.

That is why each mapping should be tested and verified. If a route fails, the problem stays focused on the NAS,
protocol, or permissions instead of appearing later as an ambiguous playback failure.