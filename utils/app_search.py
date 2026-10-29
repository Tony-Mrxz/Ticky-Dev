# utils/app_search.py
"""Flow Launcher-style application matching.

Acronym matching runs first, then an ordered-subsequence fuzzy match. Scores
reward early matches, tight matches, word boundaries, and short target names.
All query terms must match, in order.
"""

from __future__ import annotations

from dataclasses import dataclass

SEARCH_PRECISION = 50.0
_WORD_BREAKS = set(" \t-_/\\|()[]{}.,:;+&'!\"")
_EMPTY_INDICES: list[int] = []


@dataclass(slots=True)
class TextMatch:
    score: float
    indices: list[int]
    tier: int
    contiguous: bool


def normalize_query(text: str) -> str:
    return " ".join(text.casefold().split())


def _word_boundaries(text: str) -> set[int]:
    boundaries = {0}
    for i in range(1, len(text)):
        prev = text[i - 1]
        char = text[i]
        if prev in _WORD_BREAKS:
            boundaries.add(i)
        elif char.isupper() and (prev.islower() or prev.isdigit()):
            boundaries.add(i)
        elif char.isdigit() and prev.isalpha():
            boundaries.add(i)
    return boundaries


def _acronym_match(query: str, target: str) -> TextMatch | None:
    entries: list[tuple[str, int, int]] = []
    total_groups = 0
    for i, char in enumerate(target):
        is_acronym = (
            i == 0
            or target[i - 1].isspace()
            or char.isupper()
            or char.isdigit()
        )
        if not is_acronym:
            continue
        if char.isdigit():
            if i > 0 and target[i - 1].isdigit() and entries:
                group = entries[-1][2]
            else:
                total_groups += 1
                group = total_groups
        else:
            total_groups += 1
            group = total_groups
        entries.append((char.casefold(), i, group))

    if not entries:
        return None

    query_index = 0
    matched: list[tuple[int, int]] = []
    for char, index, group in entries:
        if query_index < len(query) and char == query[query_index]:
            matched.append((index, group))
            query_index += 1
    if query_index != len(query):
        return None

    matched_groups = {group for _, group in matched}
    score = 100.0 * len(matched_groups) / total_groups
    starts_target = matched[0][0] == 0
    if starts_target:
        score += 50
    return TextMatch(
        score=score,
        indices=[index for index, _ in matched],
        tier=1 if starts_target else 0,
        contiguous=False,
    )


def _best_alignment(
    term: str,
    target: str,
    boundaries: set[int],
    min_start: int,
) -> tuple[list[int], bool] | None:
    best: tuple[list[int], bool] | None = None
    best_quality = float("-inf")
    term_len = len(term)
    target_len = len(target)

    for start in range(min_start, target_len):
        if target[start] != term[0]:
            continue
        indices = [start]
        query_index = 1
        while query_index < term_len:
            for i in range(indices[-1] + 1, target_len):
                if target[i] == term[query_index]:
                    indices.append(i)
                    query_index += 1
                    break
            else:
                break
        if query_index != term_len:
            continue

        span = indices[-1] - start + 1
        contiguous = span == term_len
        at_word_start = start in boundaries
        quality = 0.0
        if at_word_start:
            quality += 2.0
        if contiguous:
            quality += 2.0
        quality += 1.0 / span
        quality -= start * 0.0001
        if quality > best_quality:
            best_quality = quality
            best = (indices, contiguous)

    return best


def _fuzzy_match(
    query: str,
    terms: list[str],
    target: str,
    target_fold: str,
) -> TextMatch | None:
    boundaries = _word_boundaries(target)
    position = 0
    indices: list[int] = []
    term_starts: list[int] = []
    all_contiguous = True
    internal_gaps = 0

    for term in terms:
        alignment = _best_alignment(term, target_fold, boundaries, position)
        if alignment is None:
            return None
        term_indices, contiguous = alignment
        indices.extend(term_indices)
        term_starts.append(term_indices[0])
        all_contiguous = all_contiguous and contiguous
        internal_gaps += (term_indices[-1] - term_indices[0] + 1) - len(term)
        position = term_indices[-1] + 1

    first = indices[0]
    last = indices[-1]
    query_chars = sum(len(term) for term in terms)
    span = last - first + 1
    preceding_space = target_fold.rfind(" ", 0, first)
    first_from_word = first - preceding_space - 1

    score = 100.0 * (query_chars + 1) / ((1 + first_from_word) + (span + 1))

    length_difference = len(target_fold) - query_chars
    if length_difference < 5:
        score += 20
    elif length_difference < 10:
        score += 10

    if all_contiguous:
        if query_chars <= 4:
            score += query_chars * 10
        else:
            score += 40 + (query_chars - 4) * 5

    score -= 8 * internal_gaps

    all_at_word_starts = all(start in boundaries for start in term_starts)
    if all_at_word_starts:
        score += 12
    if first == 0:
        score += 18

    if target_fold == query:
        score += 60
        tier = 3
    elif target_fold.startswith(query):
        score += 30
        tier = 2
    elif all_at_word_starts:
        tier = 1
    else:
        tier = 0

    return TextMatch(
        score=score,
        indices=indices,
        tier=tier,
        contiguous=all_contiguous,
    )


def match_text(query: str, target: str, precision: float = SEARCH_PRECISION) -> TextMatch | None:
    if not query or not target:
        return None

    terms = query.split(" ")
    target_fold = target.casefold()
    best = _fuzzy_match(query, terms, target, target_fold)

    if len(terms) == 1:
        acronym = _acronym_match(query, target)
        if acronym is not None and (best is None or acronym.score > best.score):
            best = acronym

    if best is None or best.score < precision:
        return None
    return best


def match_application(
    query: str,
    name: str,
    exe_stem: str | None = None,
) -> TextMatch | None:
    match = match_text(query, name)
    if match is not None:
        return match

    if exe_stem:
        stem_fold = exe_stem.casefold()
        if stem_fold and stem_fold != name.casefold():
            fallback = match_text(query, exe_stem)
            if fallback is not None:
                return TextMatch(
                    score=fallback.score * 0.95,
                    indices=_EMPTY_INDICES,
                    tier=min(fallback.tier, 1),
                    contiguous=fallback.contiguous,
                )
    return None
