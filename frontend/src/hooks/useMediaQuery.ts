import { useCallback, useSyncExternalStore } from 'react';

/**
 * Subscribe to a CSS media query and re-render when it starts or stops
 * matching. Used to drive *behavioural* responsiveness that CSS alone cannot
 * express (e.g. auto-closing the sidebars when the layout collapses to its
 * compact, drawer-based form). Pure styling stays in the stylesheet.
 *
 * Built on useSyncExternalStore — matchMedia is an external store, so this is
 * the idiomatic way to read it without an effect or cascading renders.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const mediaQuery = window.matchMedia(query);
      mediaQuery.addEventListener('change', onStoreChange);
      return () => mediaQuery.removeEventListener('change', onStoreChange);
    },
    [query],
  );

  const getSnapshot = () => window.matchMedia(query).matches;
  const getServerSnapshot = () => false;

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
