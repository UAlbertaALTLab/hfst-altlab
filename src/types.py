from typing import NamedTuple, Tuple


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


class RichAnalysis:
    """The one true FST analysis class.

    Put all your methods for dealing with things like `PV/e+nipâw+V+AI+Cnj+3Pl`
    here.
    """

    def __init__(self, analysis):
        if isinstance(analysis, Analysis):
            self._tuple = analysis
        elif (isinstance(analysis, list) or isinstance(analysis, tuple)) and (
            len(analysis) == 6 or len(analysis == 3)
        ):
            if len(analysis == 3):
                prefix_tags, lemma, suffix_tags = analysis
                self._tuple = Analysis(
                    prefixes=tuple(prefix_tags),
                    lemma=lemma,
                    suffixes=tuple(suffix_tags),
                    prefix_flags=[],
                    lemma_flags=[],
                    suffix_flags=[],
                )
            else:
                (
                    prefix_tags,
                    lemma,
                    suffix_tags,
                    prefix_flags,
                    lemma_flags,
                    suffix_flags,
                ) = analysis
                self._tuple = Analysis(
                    prefixes=tuple(prefix_tags),
                    lemma=lemma,
                    suffixes=tuple(suffix_tags),
                    prefix_flags=prefix_flags,
                    lemma_flags=lemma_flags,
                    suffix_flags=suffix_flags,
                )
        else:
            raise Exception(f"Unsupported argument: {analysis=!r}")

    @property
    def tuple(self):
        return self._tuple

    @property
    def lemma(self):
        return self._tuple.lemma

    @property
    def prefix_tags(self):
        return self._tuple.prefixes

    @property
    def suffix_tags(self):
        return self._tuple.suffixes

    def generate(self):
        return strict_generator().lookup(self.smushed())

    def generate_with_morphemes(self, inflection):
        try:
            results = strict_generator_with_morpheme_boundaries().lookup(self.smushed())
            if len(results) != 1:
                for result in results:
                    if "".join(re.split(r"[<>]", result)) == inflection:
                        return re.split(r"[<>]", result)
                return None
            return re.split(r"[<>]", results[0])
        except RuntimeError as e:
            print("Could not generate morphemes:", e)
            return []

    def smushed(self):
        return "".join(self.prefix_tags) + self.lemma + "".join(self.suffix_tags)

    def tag_set(self):
        return set(self.suffix_tags + self.prefix_tags)

    def tag_intersection_count(self, other):
        """How many tags does this analysis have in common with another?"""
        if not isinstance(other, RichAnalysis):
            raise Exception(f"Unsupported argument: {other=!r}")
        return len(self.tag_set().intersection(other.tag_set()))

    def __iter__(self):
        """Allows doing `head, _, tail = rich_analysis`"""
        return iter(self._tuple)

    def __hash__(self):
        return hash(self._tuple)

    def __eq__(self, other):
        if not isinstance(other, RichAnalysis):
            return NotImplemented
        return self._tuple == other.tuple

    def __repr__(self):
        return f"RichAnalysis({[self.prefix_tags, self.lemma, self.suffix_tags]!r})"
