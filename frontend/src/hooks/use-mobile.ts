import * as React from "react"

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  /* measured once on the client rather than set inside the effect, so the
     media-query listener is the only thing the effect is responsible for */
  const [isMobile, setIsMobile] = React.useState(() =>
    typeof window === "undefined"
      ? false
      : window.innerWidth < MOBILE_BREAKPOINT
  )

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    /* the initial value is measured in useState above; the effect only
       subscribes, so no state is set synchronously here */
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
