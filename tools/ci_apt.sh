#!/bin/sh
# CI: install Ubuntu packages, or warn and fail softly when the runner cannot reach Ubuntu's
# archive (a network outage on GitHub's side): the step then skips what needs them. Each apt
# command has a time limit, since unreachable mirrors can stall it for most of an hour.
#   if tools/ci_apt.sh gdb; then python3 tools/dbgtest.py; fi
timeout 180 sudo apt-get update -q >/dev/null 2>&1
if timeout 300 sudo apt-get install -y -q -o Acquire::Retries=2 "$@" >/dev/null; then exit 0; fi
echo "::warning::could not install $* (Ubuntu's archive unreachable?): skipping what needs them"
exit 1
