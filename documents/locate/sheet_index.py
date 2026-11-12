"""A workbook's visible cells as searchable figures and text, built once (E81, E82; the old docscan/locate.SheetIndex).

An exact cell beats a figure inside a longer cell ("$1,500 / $3,000" for 1500), which beats a figure among words
("Gold 1500"). Within a tier the cell that sits where the plan's words (`hint`) and the field's words (`anchors`) meet
wins: the plan's column and the field's row, or the other way round in a transposed sheet. The old locator scored the
better of row or column alone, so two plans printing one figure on the same row ($6,500 under both HDHPs) opened the
first plan's cell for both; scoring the crossing tells them apart. A common figure with no such word is WEAK. Pure.
"""

import re

from ..sheets import column_letter
from .fold import as_number, compact, figures_in, fold, is_common, words
from .query import DERIVED, FOUND, NOCHECK, WEAK, Located, figures, first_strong, missing, text_forms


class SheetIndex:
    def __init__(self, sheets):
        """`sheets` as sheet_cells.visible_sheets returns them: [(name, rows of cell text)]."""
        self.cells = {}  # (sheet, row, col) -> folded text
        self.exact = {}  # canonical figure or folded text -> [(sheet, r, c)]
        self.contains = {}  # canonical figure -> [(sheet, r, c)] (inside longer cells)
        self.row_words = {}  # (sheet, row) -> words
        self.col_words = {}  # (sheet, col) -> words
        self.wordy = set()  # cells whose figures sit among words ("Gold 1500")
        for name, rows in sheets:
            for r, row in enumerate(rows):
                for c, raw in enumerate(row):
                    self._add(name, r, c, fold(raw))

    def _add(self, name, r, c, text):
        if not text:
            return
        key = (name, r, c)
        self.cells[key] = text
        figure = as_number(text)
        self.exact.setdefault(figure if figure is not None else text, []).append(key)
        if figure is None:
            if re.search(r'[a-z]{2,}', text):
                self.wordy.add(key)
            for found in figures_in(text):
                self.contains.setdefault(found, []).append(key)
        cell_words = words(text)
        self.row_words.setdefault((name, r), set()).update(cell_words)
        self.col_words.setdefault((name, c), set()).update(cell_words)

    def _best(self, keys, wanted):
        plan, field = wanted

        def score(key):
            sheet, r, c = key
            row, col = self.row_words.get((sheet, r), set()), self.col_words.get((sheet, c), set())
            return max(len(field & row) + len(plan & col), len(plan & row) + len(field & col))

        ranked = sorted(keys, key=lambda key: (-score(key), key in self.wordy, key[0], key[1], key[2]))
        return ranked[0], score(ranked[0])

    def _found(self, keys, state, via, wanted, need_anchor):
        key, score = self._best(keys, wanted)
        if need_anchor and not score:
            state = WEAK
        sheet, r, c = key
        return Located(state, sheet=sheet, cell=f'{column_letter(c)}{r + 1}', hits=len(keys), via=via)

    def _find_words(self, wording, via, wanted):
        target = fold(wording)
        keys = [key for key, cell in self.cells.items() if target in cell]
        return self._found(keys, DERIVED, via, wanted, True) if keys else None

    def _find_figure(self, figure, via, wanted):
        keys = self.exact.get(figure) or self.contains.get(figure)
        if not keys:
            return None
        return self._found(keys, FOUND if via == 'number' else DERIVED, via, wanted, is_common(figure))

    def _find_code(self, query, wanted):
        target = compact(query.value)
        if len(target) < 4:
            return missing(query)
        keys = [key for key, text in self.cells.items() if target in re.sub(r'[^a-z0-9]', '', text)]
        return self._found(keys, FOUND, 'code', wanted, False) if keys else missing(query)

    def locate(self, query):
        plan = words(query.hint)
        wanted = (plan, {word for anchor in query.anchors for word in words(anchor)} - plan)
        if query.kind == 'code':
            return self._find_code(query, wanted)
        if as_number(query.value) is not None:
            found = first_strong(self._find_figure(figure, via, wanted) for figure, via in figures(query))
            if found is None or found.state == WEAK:
                worded = first_strong(self._find_words(wording, via, wanted) for wording, via in query.wordings)
                found = first_strong([worded, found])
            return found or missing(query)
        if len(fold(query.value)) < 3:
            return Located(NOCHECK, why='short')
        for form in text_forms(query.value):
            keys = self.exact.get(form)
            if keys:
                return self._found(keys, FOUND, 'text', wanted, False)
        text = fold(query.value)
        keys = [key for key, cell in self.cells.items() if text in cell]
        if keys:
            return self._found(keys, FOUND, 'text', wanted, False)
        return missing(query)
