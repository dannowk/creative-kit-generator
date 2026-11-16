#!/bin/sh
# Double-click in Finder to install and open the wizard (Terminal stays visible for progress).
cd "$(dirname "$0")"
exec ./install.sh "$@"