/*
 * The boxes over a page (plan.md §10.7; E23): the value (`bb-pdf-highlight`, which flashes) and, fainter, its line
 * (`bb-pdf-highlight-context`). Keyed on `flashKey`, so a new find remounts them and the flash plays again.
 */
const at = (rect) => ({
  left: `${rect.left}px`,
  top: `${rect.top}px`,
  width: `${rect.width}px`,
  height: `${rect.height}px`,
});

export default function Highlights({ boxes, flashKey }) {
  return (
    <>
      {boxes.context.map((rect, i) => (
        <div key={`ctx-${flashKey}-${i}`} className="bb-pdf-highlight-context" style={at(rect)} />
      ))}
      {boxes.main.map((rect, i) => (
        <div key={`${flashKey}-${i}`} className="bb-pdf-highlight" style={at(rect)} />
      ))}
    </>
  );
}
