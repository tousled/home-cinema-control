#!/usr/bin/env bash
set -euo pipefail

manifest=${MANIFEST:-docs/release-migration-manifest.json}
repo=${REPO:?Set REPO to the destination GitHub repository}
mode=${1:---dry-run}

if [[ "$mode" != "--dry-run" && "$mode" != "--apply" ]]; then
  printf 'Usage: REPO=owner/repository %s [--dry-run|--apply]\n' "$0" >&2
  exit 2
fi

while IFS= read -r release; do
  tag=$(jq -r '.new_public_tag' <<<"$release")
  title=$(jq -r '.name' <<<"$release")
  original_date=$(jq -r '.originally_released // empty' <<<"$release")
  prerelease=$(jq -r '.prerelease' <<<"$release")
  body=$(jq -r '.body // ""' <<<"$release")
  notes=$(mktemp)
  trap 'rm -f "$notes"' EXIT
  printf '%s\n\nOriginally released: %s\n' "$body" "$original_date" >"$notes"

  if [[ "$mode" == "--dry-run" ]]; then
    printf 'Would recreate %s (%s) in %s\n' "$tag" "$([[ "$prerelease" == true ]] && printf prerelease || printf stable)" "$repo"
  else
    gh api "repos/$repo/git/ref/tags/$tag" >/dev/null
    args=(release create "$tag" --repo "$repo" --verify-tag --title "$title" --notes-file "$notes")
    [[ "$prerelease" == true ]] && args+=(--prerelease)
    gh "${args[@]}"
  fi
  rm -f "$notes"
  trap - EXIT
done < <(jq -c '.[]' "$manifest")
