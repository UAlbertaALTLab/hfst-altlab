from typing import NamedTuple, Tuple
from hfst import is_diacritic


class Analysis(NamedTuple):
    """
    An analysis of a wordform.  This class is backwards compatible with the ``hfst-optimized-lookup`` package.

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
    """
    An analysis for a wordform.  Objects of this class include an analysis, a tuple of tokens (which provides information about flag diacritics), a weight (for weighted FST support), and a space to hold a standardized version of the wordform.
    """

    weight: float
    """
    The weight provided by the FST.  If the FST is not weighted, it is likely to be ``0.0``.
    """

    tokens: tuple[str, ...]
    """
    The real output of the FST.  Each element of the tuple is a symbol coming out of the FST.
    The tuple includes flag diacritic symbols, which begin and end with an ``@`` character.  
    We remove empty flag diacritic transitions (``@_EPSILON_SYMBOL_@``) to make the information usable and comparable with the output of the CLI tools.
    """

    analysis: Analysis
    """
    A grouping of the prefixes, lemma, and suffixes produced in the output of the FST.

    The analysis is a split of the non-diacritic symbols in the tokens list.  We consider as the lemma the concatenation of all single-character symbols.  Prefixes are all multi-character symbols happening before the first single-character symbol, and suffixes are all multi-character symbols happening after that.

    .. note:: The assumption of single-character symbols will conflict with multi-character emojis (for example, skin toned emojis). Although we are currently keeping this implementation, an alternative future approach would be to define prefixes as all multi-character symbols terminating in ``+``, suffixes as all multi-character symbols beginning with ``+``, and the lemma to be the concatenation of all other symbols.
    """
    standardized: str | None

    @property
    def prefixes(self) -> tuple[str, ...]:
        """
        For simplicity, prefixes can be accessed directly as if this were an :py:class:`hfst_altlab.Analysis` object.
        """
        return self.analysis.prefixes

    @property
    def lemma(self) -> str:
        """
        For simplicity, the lemma can be accessed directly as if this were an :py:class:`hfst_altlab.Analysis` object.
        """
        return self.analysis.lemma

    @property
    def suffixes(self) -> tuple[str, ...]:
        """
        For simplicity, suffixes can be accessed directly as if this were an :py:class:`hfst_altlab.Analysis` object.
        """
        return self.analysis.suffixes

    def __init__(
        self, weight: float, tokens: tuple[str, ...], standardized: str | None = None
    ):
        """
        This object is not usually created directly by library users, but it is the output of some methods of :py:class:`hfst_altlab.TransducerFile` and :py:class:`hfst_altlab.TransducerPair`.
        The information comes from direct calls to the ``hfst`` library.
        :param weight: The weight of this analysis
        :param tokens: The tuple of tokens coming from the FST.  It might contain empty symbols and epsilon diacritic transitions, which the FullAnalysis does not keep.
        :param standardized: A standardized version of the associated wordform (only intrpoduced by :py:class:`hfst_altlab.TransducerPair` objects).  It is the result of providing the analysis to some other generator FST.
        """
        self.weight = weight
        self.tokens = tuple(x for x in tokens if x and x != "@_EPSILON_SYMBOL_@")
        self.analysis = _parse_analysis(self.tokens)
        self.standardized = standardized

    def __str__(self):
        return f"FullAnalysis(weight={self.weight}, prefixes={self.analysis.prefixes}, lemma={self.analysis.lemma}, suffixes={self.analysis.suffixes})"

    def __repr__(self):
        return f"FullAnalysis(weight={self.weight}, tokens={self.tokens})"

    def __eq__(self, other):
        """
        Note that equality between wordforms considers both weight and all tokens generated by the FST.  That is, there might be two Analysis objects such that ``a != b`` while ``a.lemma == b.lemma``, ``a.prefixes == b.prefixes``, and ``a.suffixes == b.suffixes``, if their flag diacritics are different.
        """
        if isinstance(other, self.__class__):
            return self.weight == other.weight and self.tokens == other.tokens
        else:
            return False

    def __hash__(self):
        """
        By providing a hashing function, we can place objects of this class into standard Python sets.
        """
        return hash((self.weight,) + self.tokens)

    def as_fst_input(self) -> str:
        return fst_output_format(self.tokens)


class Wordform:
    """
    A wordform is the output of passing an analysis to a generator FST.
    """

    weight: float
    """
    For weighted FSTs, the weight of this particular wordform output.
    """

    tokens: tuple[str, ...]
    """
    The real output of the FST.  Each element of the tuple is a symbol coming out of the FST.
    The tuple includes flag diacritic symbols, which begin and end with an ``@`` character.  
    We remove empty flag diacritic transitions (``@_EPSILON_SYMBOL_@``) to make the information usable and comparable with the output of the CLI tools.
    """

    wordform: str
    """
    The wordform associated with the FST output, obtained by concatenating all the non-flag diacritic symbols in the tokens tuple.
    """

    def __init__(self, weight: float, tokens: tuple[str, ...]):
        self.weight = weight
        self.tokens = tokens
        self.wordform = "".join(
            x for x in tokens if x and not is_diacritic(x) and x != "@_EPSILON_SYMBOL_@"
        )

    def __str__(self):
        """
        The string representation of this object.  Equivalent to ``self.wordform``.
        """
        return self.wordform

    def __repr__(self):
        return f"Wordform(weight={self.weight}, wordform={self.wordform})"

    def __eq__(self, other):
        """
        Note that equality between wordforms considers both weight and all tokens generated by the FST.  That is, there might be two Wordform objects such that ``a != b`` while ``str(a) == str(b)``, if their flag diacritics are different.
        """
        if isinstance(other, self.__class__):
            return self.weight == other.weight and self.tokens == other.tokens
        else:
            return False

    def __hash__(self):
        """
        By providing a hashing function, we can place objects of this class into standard Python sets.
        """
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
