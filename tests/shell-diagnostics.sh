#!/bin/bash
# Source from synthetic test scripts only; log source syntax, not expanded secrets.
isolation_error() {
    local status=$1 line=$2 failed_command=$3 source_file=$4
    printf 'FAIL: %s:%s exit=%s command=%q\n' "$source_file" "$line" "$status" "$failed_command" >&2
    if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
        printf '::error file=%s,line=%s::Isolation command failed with exit %s; exact command is in the preceding log line.\n' "$source_file" "$line" "$status" >&2
    fi
    return "$status"
}
trap 'isolation_error "$?" "$LINENO" "$BASH_COMMAND" "${BASH_SOURCE[0]}"' ERR
