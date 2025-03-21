#/bin/sh

set -eo pipefail

if [ "$#" != "1" ]; then
    echo "USAGE: $0 TARGET"
    echo "Where TARGET is any target from:"
    cargo fuzz list
    exit 1
fi
TARGET="$1"

cd "$(dirname "$0")/.."

# Writes to …/tinyvm/fuzz/{artifacts,corpus}/${TARGET}/* :
# cargo fuzz run "${TARGET}" -- -max_len=131072 -close_fd_mask=1

# Writes to …/tinyvm/fuzz/coverage/${TARGET}/coverage.profdata :
cargo fuzz coverage ${TARGET} -- -close_fd_mask=1

llvm-cov show "target/x86_64-unknown-linux-gnu/coverage/x86_64-unknown-linux-gnu/release/${TARGET}" \
    --format=html \
    -Xdemangler=rustfilt \
    --ignore-filename-regex="\.cargo" \
    "-instr-profile=fuzz/coverage/${TARGET}/coverage.profdata" \
    --show-branches=percent \
    --show-instantiations \
    --show-mcdc \
    "--output-dir=fuzz/coverage/${TARGET}/"

echo "Run some httpd at: $(realpath "fuzz/coverage/${TARGET}/index.html")"
