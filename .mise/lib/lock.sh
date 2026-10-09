lock_scripts() {
  local script
  while IFS= read -r script; do
    uv lock "$@" --script "$script"
  done < <(grep -lr '^# /// script' .mise/tasks)
}
