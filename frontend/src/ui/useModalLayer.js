import { useEffect, useRef } from 'react';

const FIELDS = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
const FOCUSABLE =
  'button:not([disabled]), [href], input:not([type="hidden"]):not([disabled]), select:not([disabled]), ' +
  'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

let modalLayers = 0;

/**
 * A layer over the page (Modal, Drawer), rendered outside #root. While a `modal` layer is open the app behind it is
 * inert, so focus and clicks stay in the layer. Focus moves in to `initialFocus.current`, an element marked
 * data-autofocus, the first field of the body (when `focusField`), or the first focusable element; Escape calls
 * `onEscape`; focus returns to the element that opened the layer when it closes.
 */
export function useModalLayer(ref, { initialFocus, focusField = true, onEscape, modal = true } = {}) {
  const escape = useRef(onEscape);
  useEffect(() => {
    escape.current = onEscape;
  });

  useEffect(() => {
    const layer = ref.current;
    if (!layer) return undefined;
    const previous = document.activeElement;
    const root = document.getElementById('root');
    if (modal && root) {
      modalLayers += 1;
      root.inert = true;
    }
    const body = layer.querySelector('[data-dialog-body]') || layer;
    const target =
      initialFocus?.current ||
      layer.querySelector('[data-autofocus]') ||
      (focusField && body.querySelector(FIELDS)) ||
      body.querySelector(FOCUSABLE) ||
      layer.querySelector(FOCUSABLE);
    target?.focus();

    function onKeyDown(event) {
      if (event.key !== 'Escape' || !escape.current) return;
      event.preventDefault();
      event.stopPropagation();
      escape.current();
    }
    layer.addEventListener('keydown', onKeyDown);
    return () => {
      layer.removeEventListener('keydown', onKeyDown);
      if (modal && root) {
        modalLayers = Math.max(0, modalLayers - 1);
        if (modalLayers === 0) root.inert = false;
      }
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, [ref, initialFocus, focusField, modal]);
}
