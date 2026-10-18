# Historical tag migration plan

No historical tag is created in this phase.

The audited source contains 44 tags: 31 have a GitHub Release and 13 do not.
All historical tags are lightweight. The future public tags must point only to
documentary commits in this repository; they must never point to source
objects from the historical or private repository.

## Proposed documentary graph

1. Keep the initial public documentation commit on `main` as the repository
   baseline.
2. Add chronological documentation-only commits for the historical changelog
   milestones, beginning with `0.1.0` and ending with `1.4.1`.
3. For each historical tag, create the same tag name only after review, at the
   documentary commit representing that version. Release candidates remain
   distinct tags such as `1.4.1-rc.1`.
4. Keep the 13 tag-only records represented in `RELEASE_HISTORY.md` and the
   migration manifest even when no release page exists.
5. Recreate releases only after the corresponding documentary tag exists and
   after the issue-number mapping is known.

The Git SHA recorded in the historical inventory is metadata only. It is not
reused, and the new repository has no parent commit from the source history.
The tag names remain compatible with the existing updater and release URL
conventions, subject to the later cutover review.

## Review gates

- Verify each proposed tag points to a documentary tree with no source files.
- Verify the tag count and exact names against the 44-tag audit.
- Verify no release is created before its issue links are updated.
- Verify no release workflow or Docker publication is triggered by tag
  creation; historical releases will be created deliberately and manually.
