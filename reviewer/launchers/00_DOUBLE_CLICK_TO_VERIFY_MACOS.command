#!/bin/bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x "runtime/bin/python3" ]; then
    echo "REVIEWER KIT INCOMPLETE"
    echo
    echo "The private runtime is missing from this folder."
    echo "Re-extract the complete reviewer ZIP or download it again."
    echo "You do not need to install Python or any other software."
    if [ "${BGVD_REVIEWER_NO_PAUSE:-0}" != "1" ]; then
        printf "\nPress Return to close this window."
        read -r _
    fi
    exit 1
fi

unset PYTHONHOME
unset PYTHONPATH
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

"runtime/bin/python3" -I -s "reviewer_offline_check.py"
BGVD_EXIT=$?

echo
if [ "$BGVD_EXIT" -eq 0 ]; then
    echo "Reviewer check completed successfully. Opening the result page..."
else
    echo "Reviewer check did not pass. Opening the explanation and logs..."
fi

if [ "${BGVD_REVIEWER_NO_OPEN:-0}" != "1" ] && \
   [ -f "reviewer_output/REVIEWER_CHECK_SUMMARY.html" ]; then
    open "reviewer_output/REVIEWER_CHECK_SUMMARY.html"
fi

if [ "${BGVD_REVIEWER_NO_PAUSE:-0}" != "1" ]; then
    printf "\nPress Return to close this window."
    read -r _
fi

exit "$BGVD_EXIT"
