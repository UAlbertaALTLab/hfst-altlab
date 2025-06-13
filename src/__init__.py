import hfst
from pathlib import Path
from errno import ENOENT
from os import strerror
from .types import Analysis


class TransducerFile:
    """
    Loads an ``.hfst`` or an ``.hfstol`` transducer file.
    This is intended as a replacement and extension of the
    hfst-optimized-lookup python package, but depending on the
    hfst project to pack the C code directly.  This provides the
    added benefit of regaining access to weighted FSTs without extra work.
    Note that lookup will only be fast if the input file has been processed
    into the hfstol format.
    """

    def __init__(self, filename: Path | str, search_cutoff: int = 60):
        self.cutoff = search_cutoff

        if not Path(filename).exists():
            exn = FileNotFoundError(f"Transducer not found: ‘{str(filename)}’")
            raise exn

        # Now we extract the transducer and store it.
        try:
            stream = hfst.HfstInputStream(str(filename))
        except hfst.exceptions.NotTransducerStreamException as e:
            # Expected message for backwards compatibility.
            e.args = ("wrong or corrupt file?",)
            raise e

        transducers = stream.read_all()
        if not len(transducers) == 1:
            error = ValueError(self)
            error.add_note("We expected a single transducer to arise in the file.")
            stream.close()
            raise error

        stream.close()
        self.transducer = transducers[0]
        if self.transducer.is_infinitely_ambiguous():
            raise RuntimeWarning("The transducer is infinitely ambiguous.")
        if not (
            self.transducer.get_type()
            in [
                hfst.ImplementationType.HFST_OL_TYPE,
                hfst.ImplementationType.HFST_OLW_TYPE,
            ]
        ):
            print("Transducer not optimized.  Optimizing...")
            self.transducer.lookup_optimize()
            print("Done.")

    def bulk_lookup(self, words: list[str]) -> dict[str, set[str]]:
        """
         Like ``lookup()`` but applied to multiple inputs. Useful for generating multiple
        surface forms.

        :param words: list of words to lookup
        :type words: list[str]
        :return: a dictionary mapping words in the input to a set of its tranductions
        :rtype: dict[str, set[str]]
        """
        return {word: set(self.lookup(word)) for word in words}

    def lookup(self, input: str) -> list[str]:
        """
        Lookup the input string, returning a list of tranductions.  This is
        most similar to using ``hfst-optimized-lookup`` on the command line.

        :param str string: The string to lookup.
        :return: list of analyses as concatenated strings, or an empty list if the input
            cannot be analyzed.
        :rtype: list[str]
        """
        return ["".join(transduction) for transduction in self.lookup_symbols(input)]

    def weighted_lookup_lemma_with_affixes(
        self, surface_form: str
    ) -> list[tuple[float, Analysis]]:
        """
        Analyze the input string, returning a list
        of tuples containing a ``float`` and a :py:class:`types.Analysis` object.

        .. note::
            this method assumes an analyzer in which all multicharacter symbols
            represent affixes, and all lexical symbols are contiguous.


        :param str string: The string to lookup.
        :return: list of analyses as :py:class:`types.Analysis`
            objects, or an empty list if there are no analyses.
        :rtype: list of :py:class:`types.Analysis`
        """
        raw_weighted_analyses = self.weighted_lookup_symbols(surface_form)
        return [
            (weight, _parse_analysis(analysis))
            for weight, analysis in raw_weighted_analyses
        ]

    def lookup_lemma_with_affixes(self, surface_form: str) -> list[Analysis]:
        return [
            analysis
            for weight, analysis in self.weighted_lookup_lemma_with_affixes(
                surface_form
            )
        ]

    def lookup_symbols(self, input: str) -> list[list[str]]:
        """
        Transduce the input string. The result is a list of tranductions. Each
        tranduction is a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        :param str input: The string to lookup.
        :return:
        :rtype: list[list[str]]
        """
        return [
            transduction for weight, transduction in self.weighted_lookup_symbols(input)
        ]

    def weighted_lookup_symbols(self, input: str) -> list[tuple[float, list[str]]]:
        """
        Transduce the input string. The result is a list of weighted tranductions. Each
        weighted tranduction is a tuple with a float for the weight and a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        :param str input: The string to lookup.
        :return:
        :rtype: list[tuple[float,list[str]]]
        """
        return [
            (
                float(weight),
                [
                    symbol
                    for symbol in symbols
                    if not hfst.is_diacritic(symbol) and symbol
                ],
            )
            for weight, symbols in self.weighted_lookup_symbols_with_flags(input)
        ]

    def weighted_lookup_symbols_with_flags(
        self, input: str
    ) -> list[tuple[float, list[str]]]:
        """
        Transduce the input string, preserving the weight information coming from HFST and separating each symbol

        :param str input: The string to lookup.
        :return: A list of tuples, each containing the weight(float), and a list of strings, each a language symbol
        :rtype: list[tuple[float,list[str]]]
        """
        return list(
            self.transducer.lookup(input, time_cutoff=self.cutoff, output="raw")
        )

    def symbol_count(self) -> int:
        """
        symbol_count() -> int

        Returns the number of symbols in the sigma (the symbol table or alphabet).

        :rtype: int
        """
        return len(self.transducer.get_alphabet())


def _parse_analysis(letters_and_tags: list[str]) -> Analysis:
    prefix_tags: list[str] = []
    lemma_chars: list[str] = []
    suffix_tags: list[str] = []

    tag_destination = prefix_tags
    for symbol in letters_and_tags:
        if not hfst.is_diacritic(symbol):
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
