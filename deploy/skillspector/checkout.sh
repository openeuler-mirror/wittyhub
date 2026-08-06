#!/bin/sh

set -eu

git_url=${SCAN_GIT_URL:?SCAN_GIT_URL is required}
git_ref=${SCAN_GIT_REF:-main}
skill_path=${SCAN_SKILL_PATH:-}
repository_root=${LOCAL_REPO_ROOT:-/opt/wittyhub/skill-repositories}

case "$skill_path" in
    /*|../*|*/../*|*/..)
        echo "Invalid skill path: $skill_path" >&2
        exit 2
        ;;
esac

repository_key=$(
    printf '%s' "$git_url" |
        sed -e 's#^https\?://##' -e 's#/$##' -e 's#\.git$##' -e 's#/#_#g'
)

case "$repository_key" in
    ''|*[!A-Za-z0-9._-]*)
        echo "Local repository lookup skipped: unsupported URL format: $git_url"
        repository_key=''
        ;;
esac

local_repository=''
if [ -n "$repository_key" ]; then
    local_repository="${repository_root}/${repository_key}"
fi

archive_ref=''
archive_repository=''

if [ -n "$local_repository" ] && [ -d "${local_repository}/.git" ] && \
    git -c safe.directory="$local_repository" -C "$local_repository" \
        cat-file -e "${git_ref}^{commit}" 2>/dev/null; then
    echo "Using local repository cache: $local_repository"
    archive_repository=$local_repository
    archive_ref=$git_ref
else
    if [ -n "$local_repository" ] && [ -d "${local_repository}/.git" ]; then
        echo "Reference is not available locally; fetching from origin: $git_ref"
    else
        echo "Local repository cache not found; using remote repository: $git_url"
    fi
    git init
    git remote add origin "$git_url"
    git fetch --depth 1 origin "$git_ref"
    archive_repository=.
    archive_ref=FETCH_HEAD
fi

resolved_commit=$(git -c safe.directory="$archive_repository" \
    -C "$archive_repository" rev-parse "${archive_ref}^{commit}")
echo "Resolved commit: $resolved_commit"

archive_file="${PWD}/.wittyhub-scan.tar"
if [ -n "$skill_path" ]; then
    echo "Exporting skill path: $skill_path"
    if ! git -c safe.directory="$archive_repository" -C "$archive_repository" \
        cat-file -e "${archive_ref}:${skill_path}" 2>/dev/null; then
        echo "Skill path does not exist at commit ${resolved_commit}: ${skill_path}" >&2
        exit 3
    fi
    git -c safe.directory="$archive_repository" -C "$archive_repository" \
        archive --format=tar --output="$archive_file" "$archive_ref" -- "$skill_path"
else
    echo "Exporting repository root"
    git -c safe.directory="$archive_repository" -C "$archive_repository" \
        archive --format=tar --output="$archive_file" "$archive_ref"
fi

tar -xf "$archive_file"
rm -f "$archive_file"
echo "Prepared scan content from commit: $resolved_commit"
