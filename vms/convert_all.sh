#!/bin/sh

set -e
cd -P -- "$(dirname -- "$0")"

ASSEMBLER="../assembler/asm.py"

for ASM_FILENAME in */*.asm; do
    SEGMENT_FILENAME="$(echo "${ASM_FILENAME}" | sed -Ee 's/.asm$/.segment/')"
    if [ "${ASM_FILENAME}" = "${SEGMENT_FILENAME}" ]; then
        echo "Weird asm filename?! ${ASM_FILENAME}"
        continue
    fi
    echo "${ASM_FILENAME} -> ${SEGMENT_FILENAME}"
    "${ASSEMBLER}" "${ASM_FILENAME}" "${SEGMENT_FILENAME}"
done
