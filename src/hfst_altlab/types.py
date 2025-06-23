from typing import NamedTuple, Tuple
from hfst import is_diacritic


class Analysis(NamedTuple):
    """
    An analysis of a wordform.

    This is a *named tuple*, so you can use it both with attributes and indices:

    >>> analysis = Analysis(('PV/e+',), 'wâpamêw', ('+V', '+TA', '+Cnj', '+3Sg', '+4Sg/PlO'))

    Using attributes:

    >>> analysis.lemma
    'wâpamêw'
    >>> analysis.prefixes
    ('PV/e+',)
    >>> analysis.suffixes
    ('+V', '+TA', '+Cnj', '+3Sg', '+4Sg/PlO')

    Using with indices:

    >>> len(analysis)
    3
    >>> analysis[0]
    ('PV/e+',)
    >>> analysis[1]
    'wâpamêw'
    >>> analysis[2]
    ('+V', '+TA', '+Cnj', '+3Sg', '+4Sg/PlO')
    >>> prefixes, lemma, suffix = analysis
    >>> lemma
    'wâpamêw'
    """

    prefixes: Tuple[str, ...]
    """
    Tags that appear before the lemma.
    """

    lemma: str
    """
    The base form of the analyzed wordform.
    """

    suffixes: Tuple[str, ...]
    """
    Tags that appear after the lemma.
    """


def _parse_analysis(letters_and_tags: tuple[str, ...]) -> Analysis:
    prefix_tags: list[str] = []
    lemma_chars: list[str] = []
    suffix_tags: list[str] = []

    tag_destination = prefix_tags
    for symbol in letters_and_tags:
        if not is_diacritic(symbol):
            if len(symbol) == 1:
                lemma_chars.append(symbol)
                tag_destination = suffix_tags
            else:
                assert len(symbol) > 1
                tag_destination.append(symbol)

    return Analysis(
        tuple(prefix_tags),
        "".join(lemma_chars),
        tuple(suffix_tags),
    )


class FullAnalysis:
    weight: float
    tokens: tuple[str, ...]
    analysis: Analysis
    standardized: str | None

    @property
    def prefixes(self) -> tuple[str, ...]:
        return self.analysis.prefixes

    @property
    def lemma(self) -> str:
        return self.analysis.lemma

    @property
    def suffixes(self) -> tuple[str, ...]:
        return self.analysis.suffixes

    def __init__(
        self, weight: float, tokens: tuple[str, ...], standardized: str | None = None
    ):
        self.weight = weight
        self.tokens = tuple(x for x in tokens if x and x != "@_EPSILON_SYMBOL_@")
        self.analysis = _parse_analysis(self.tokens)
        self.standardized = standardized

    def __str__(self):
        return f"FullAnalysis(weight={self.weight}, prefixes={self.analysis.prefixes}, lemma={self.analysis.lemma}, suffixes={self.analysis.suffixes})"

    def __repr__(self):
        return f"FullAnalysis(weight={self.weight}, tokens={self.tokens})"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.weight == other.weight and self.tokens == other.tokens
        else:
            return False

    def __hash__(self):
        return hash((self.weight,) + self.tokens)

    def as_fst_input(self) -> str:
        return fst_output_format(self.tokens)


class Wordform:
    weight: float
    tokens: tuple[str, ...]
    wordform: str

    def __init__(self, weight: float, tokens: tuple[str, ...]):
        self.weight = weight
        self.tokens = tokens
        self.wordform = "".join(
            x for x in tokens if x and not is_diacritic(x) and x != "@_EPSILON_SYMBOL_@"
        )

    def __str__(self):
        return self.wordform

    def __repr__(self):
        return f"Wordform(weight={self.weight}, wordform={self.wordform})"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.weight == other.weight and self.tokens == other.tokens
        else:
            return False

    def __hash__(self):
        return hash((self.weight,) + self.tokens)

    def as_fst_input(self):
        return self.wordform


def as_fst_input(data: str | FullAnalysis | Wordform) -> str:
    if isinstance(data, str):
        return data
    else:
        return data.as_fst_input()


def fst_output_format(tokens: tuple[str, ...]) -> str:
    return "".join(x for x in tokens if not is_diacritic(x))
