export function getRouteAwareChatLabel(pathname: string): string {
  if (!pathname || pathname === "/") {
    return "Dashboard Copilot"
  }

  if (pathname.startsWith("/strategies/")) {
    return "Strategy Copilot"
  }
  if (pathname.startsWith("/strategies")) {
    return "Strategies Copilot"
  }
  if (pathname.startsWith("/optimization")) {
    return "Optimization Copilot"
  }
  if (pathname.startsWith("/live")) {
    return "Live Trading Copilot"
  }
  if (pathname.startsWith("/simulation")) {
    return "Simulation Copilot"
  }
  if (pathname.startsWith("/performance")) {
    return "Performance Copilot"
  }
  if (pathname.startsWith("/operator")) {
    return "Operator Copilot"
  }
  if (pathname.startsWith("/tools")) {
    return "Tools Copilot"
  }
  if (pathname.startsWith("/documentation")) {
    return "Docs Copilot"
  }
  if (pathname.startsWith("/edge-lab")) {
    return "Edge Lab Copilot"
  }
  if (pathname.startsWith("/settings")) {
    return "Settings Assistant"
  }

  const lastSegment = pathname.split("/").filter(Boolean).at(-1) ?? "workspace"
  return `${lastSegment.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())} Copilot`
}
