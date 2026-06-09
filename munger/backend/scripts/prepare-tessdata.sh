#!/usr/bin/env bash
# Copy Tesseract .traineddata files into the backend Docker build context.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${TESSDATA_SOURCE:-${HOME}/Documents/dev/tesseract}"
DEST_DIR="${BACKEND_DIR}/tessdata"

mkdir -p "${DEST_DIR}"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Tesseract source directory not found: ${SOURCE_DIR}" >&2
  echo "Set TESSDATA_SOURCE to a directory containing *.traineddata files." >&2
  exit 1
fi

shopt -s nullglob
files=("${SOURCE_DIR}"/*.traineddata)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No .traineddata files found in ${SOURCE_DIR}" >&2
  exit 1
fi

cp -f "${files[@]}" "${DEST_DIR}/"
echo "Prepared ${#files[@]} tessdata file(s) in ${DEST_DIR}"
