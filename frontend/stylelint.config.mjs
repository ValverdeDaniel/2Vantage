// stylelint (plan.md §12.5, OQ10): one rule, no style rules, so the ported sheets stay byte-for-byte the old ones.
// A var() must name a custom property that is defined: in the file itself, in App.css's :root block (the token
// source, O.5), or inline by a component.
// The plugin accepts var(--unknown, fallback); scripts/port-proof.mjs refuses that too in the ported sheets.
import { fileURLToPath } from 'node:url';

const here = (p) => fileURLToPath(new URL(p, import.meta.url));

export default {
  plugins: ['stylelint-value-no-unknown-custom-properties'],
  rules: {
    'csstools/value-no-unknown-custom-properties': [true, {
      importFrom: [
        here('./src/styles/App/01-benibridge-design-tokens.css'),
        {
          customProperties: {
            // Set in a style attribute by the component that reads them.
            '--pg-cols': '', // the Pages grid (D-221)
            '--freeze-head-h': '', // frozen panes (D-166)
            '--freeze-label-w': '',
            '--bnf-clip-h': '', // grid sizes
          },
        },
      ],
    }],
  },
};
