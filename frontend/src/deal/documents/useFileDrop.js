import { useRef, useState } from 'react';

/*
 * Files dropped anywhere on the tab (plan.md §8.16; E4): the drop target wears `is-dropping` while files are over it,
 * and the files go to `onFiles`. Only file drags count (dragging text or a tab does nothing); nested elements do not
 * flicker the state, because enter and leave are counted.
 */
const hasFiles = (event) => Array.from(event.dataTransfer?.types || []).includes('Files');

export default function useFileDrop(onFiles) {
  const [dropping, setDropping] = useState(false);
  const depth = useRef(0);
  const props = {
    onDragEnter: (event) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth.current += 1;
      setDropping(true);
    },
    onDragOver: (event) => {
      if (hasFiles(event)) event.preventDefault();
    },
    onDragLeave: (event) => {
      if (!hasFiles(event)) return;
      depth.current = Math.max(0, depth.current - 1);
      if (!depth.current) setDropping(false);
    },
    onDrop: (event) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth.current = 0;
      setDropping(false);
      const files = Array.from(event.dataTransfer.files || []);
      if (files.length) onFiles(files);
    },
  };
  return { dropping, props };
}
