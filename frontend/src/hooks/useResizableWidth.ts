import { useCallback, useEffect, useRef, useState } from 'react';

type Edge = 'left' | 'right';

type ResizableOptions = {
  /** Smallest allowed width in px. */
  min: number;
  /** Largest allowed width in px. */
  max: number;
  /**
   * Which side the sidebar lives on. A left sidebar grows when the handle is
   * dragged to the right (positive delta); a right sidebar grows when it is
   * dragged to the left (negative delta).
   */
  edge: Edge;
  /** When set, the chosen width is persisted to localStorage under this key. */
  storageKey?: string;
  /** Step in px used by keyboard arrow-key resizing. */
  keyboardStep?: number;
};

export type ResizableWidth = {
  width: number;
  isDragging: boolean;
  onPointerDown: (event: React.PointerEvent<HTMLElement>) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLElement>) => void;
  /** Reset to the initial width (used for double-click on the handle). */
  reset: () => void;
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const readStoredWidth = (
  storageKey: string | undefined,
  fallback: number,
  min: number,
  max: number,
) => {
  if (!storageKey || typeof window === 'undefined') {
    return fallback;
  }
  const stored = Number(window.localStorage.getItem(storageKey));
  return Number.isFinite(stored) && stored >= min && stored <= max ? stored : fallback;
};

/**
 * Drag-to-resize behaviour for a sidebar column, modelled on the VSCode side
 * panels: pointer-drag on the handle, double-click to reset, arrow keys for
 * fine adjustment, and optional localStorage persistence. The hook only owns
 * the width; the caller renders the handle and feeds the width into its grid
 * template.
 */
export function useResizableWidth(
  initial: number,
  { min, max, edge, storageKey, keyboardStep = 16 }: ResizableOptions,
): ResizableWidth {
  const [width, setWidth] = useState(() => readStoredWidth(storageKey, initial, min, max));
  const [isDragging, setIsDragging] = useState(false);
  const frame = useRef(0);

  useEffect(() => {
    if (storageKey && typeof window !== 'undefined') {
      window.localStorage.setItem(storageKey, String(width));
    }
  }, [storageKey, width]);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      event.preventDefault();
      const handle = event.currentTarget;
      handle.setPointerCapture(event.pointerId);
      const startX = event.clientX;
      const startWidth = width;
      setIsDragging(true);
      document.body.classList.add('mindocu-resizing');

      const onMove = (move: PointerEvent) => {
        const delta = move.clientX - startX;
        const raw = edge === 'right' ? startWidth - delta : startWidth + delta;
        const next = clamp(raw, min, max);
        cancelAnimationFrame(frame.current);
        frame.current = requestAnimationFrame(() => setWidth(next));
      };

      const finish = (end: PointerEvent) => {
        cancelAnimationFrame(frame.current);
        handle.releasePointerCapture(end.pointerId);
        handle.removeEventListener('pointermove', onMove);
        handle.removeEventListener('pointerup', finish);
        handle.removeEventListener('pointercancel', finish);
        setIsDragging(false);
        document.body.classList.remove('mindocu-resizing');
      };

      handle.addEventListener('pointermove', onMove);
      handle.addEventListener('pointerup', finish);
      handle.addEventListener('pointercancel', finish);
    },
    [width, min, max, edge],
  );

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      const grow = edge === 'right' ? 'ArrowLeft' : 'ArrowRight';
      const shrink = edge === 'right' ? 'ArrowRight' : 'ArrowLeft';
      if (event.key === grow) {
        event.preventDefault();
        setWidth((current) => clamp(current + keyboardStep, min, max));
      } else if (event.key === shrink) {
        event.preventDefault();
        setWidth((current) => clamp(current - keyboardStep, min, max));
      }
    },
    [edge, keyboardStep, min, max],
  );

  const reset = useCallback(() => setWidth(clamp(initial, min, max)), [initial, min, max]);

  return { width, isDragging, onPointerDown, onKeyDown, reset };
}
