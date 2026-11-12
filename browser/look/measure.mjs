// What the Look lane reads from a drawn page besides pixels (Q.5): the order of the old app's classes, and the
// computed style of a screen's key selectors.

export const CLASS_PREFIX = /^(bnf|bb|gk|rr)-/;

export const STYLE_PROPS = [
  'font-family', 'font-size', 'font-weight', 'line-height', 'color', 'background-color',
  'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
  'border-top-style', 'border-top-color', 'border-radius',
  'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
];

// Every bnf-/bb-/gk-/rr- class in document order, one entry per element and class, hidden elements left out.
export function classOrder(page) {
  return page.evaluate((source) => {
    const prefix = new RegExp(source);
    const out = [];
    for (const el of document.body.querySelectorAll('[class]')) {
      if (!el.checkVisibility || !el.checkVisibility()) continue;
      for (const name of el.classList) if (prefix.test(name)) out.push(name);
    }
    return out;
  }, CLASS_PREFIX.source);
}

// The first visible match of each selector: its computed style and its box. null where nothing matches.
export function styles(page, selectors) {
  return page.evaluate(({ selectors: wanted, props }) => {
    const out = {};
    for (const selector of wanted) {
      let el = null;
      try {
        el = [...document.querySelectorAll(selector)].find((node) => node.checkVisibility && node.checkVisibility());
      } catch {
        el = null;
      }
      if (!el) {
        out[selector] = null;
        continue;
      }
      const style = getComputedStyle(el);
      const box = el.getBoundingClientRect();
      out[selector] = {
        style: Object.fromEntries(props.map((prop) => [prop, style.getPropertyValue(prop)])),
        box: { x: Math.round(box.x), y: Math.round(box.y + window.scrollY), width: Math.round(box.width), height: Math.round(box.height) },
      };
    }
    return out;
  }, { selectors, props: STYLE_PROPS });
}
