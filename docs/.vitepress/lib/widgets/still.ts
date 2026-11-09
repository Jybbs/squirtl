/**
 * Runs `apply`, which sets styles on `nodes`, with every transition on them off,
 * so each lands where `apply` puts it in one frame, then turns the transitions
 * back on once the browser has laid the new styles out.
 */
export function still(nodes: readonly HTMLElement[], apply: () => void): void {
  for (const node of nodes) node.style.transition = 'none'
  apply()
  nodes[0]?.getBoundingClientRect()
  for (const node of nodes) node.style.transition = ''
}
