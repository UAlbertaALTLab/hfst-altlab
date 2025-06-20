import hfst
from pathlib import Path
from .types import Analysis, FullAnalysis, Wordform, as_fst_input, fst_output_format
from typing import cast
from collections.abc import Callable


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

    def lookup_lemma_with_affixes(self, surface_form: str) -> list[Analysis]:
        return [
            analysis.analysis
            for analysis in self.weighted_lookup_full_analysis(surface_form)
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
            [x for x in analysis.flag_diacritics if x and not hfst.is_diacritic(x)]
            for analysis in self.weighted_lookup_full_analysis(input)
        ]

    def _weighted_lookup(self, input: str) -> list[tuple[str, list[str]]]:
        """
        Internal Function. Transduce the input string. The result is a list of weighted tranductions. Each
        weighted tranduction is a tuple with a number for the weight and a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        :param str input: The string to lookup.
        :return:
        :rtype: list[tuple[float,list[str]]]
        """
        return cast(
            list[tuple[str, list[str]]],
            self.transducer.lookup(str(input), time_cutoff=self.cutoff, output="raw"),
        )

    def weighted_lookup_full_analysis(
        self, wordform: str | Wordform, generator: "TransducerFile" | None = None
    ) -> list[FullAnalysis]:
        """
        Transduce a wordform into a list of analyzed outputs.
        If a generator is provided, it will incorporate a standardized version of the string when available.
        That is, it will pass the output to a secondary FST, and check if all the outputs of that "generator" FST match for an output.
        If so, the output will be marked with the output string in the `standardized` field [See FullAnalysis]
        :param str input: The string to lookup.
        :return:
        :rtype: list[FullAnalysis]
        """
        if generator:

            def generate(tokens: list[str]) -> str | None:
                entry: str | None = None
                for _, output in generator._weighted_lookup(fst_output_format(tokens)):
                    candidate = "".join(output)
                    if entry and entry != candidate:
                        return None
                    else:
                        entry = candidate
                return entry

        else:

            def generate(tokens: list[str]) -> str | None:
                return None

        return [
            FullAnalysis(float(weight), tokens, generate(tokens))
            for weight, tokens in self._weighted_lookup(as_fst_input(wordform))
        ]

    def weighted_lookup_full_wordform(
        self, analysis: str | FullAnalysis
    ) -> list[Wordform]:
        """
        Transduce the input string. The result is a list of weighted tranductions. Each
        weighted tranduction is a tuple with a float for the weight and a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        :param str input: The string to lookup.
        :return:
        :rtype: list[tuple[float,list[str]]]
        """
        return [
            Wordform(float(weight), tokens)
            for weight, tokens in self._weighted_lookup(as_fst_input(analysis))
        ]

    def symbol_count(self) -> int:
        """
        symbol_count() -> int

        Returns the number of symbols in the sigma (the symbol table or alphabet).

        :rtype: int
        """
        return len(self.transducer.get_alphabet())


class TransducerPair:
    analyser: TransducerFile
    generator: TransducerFile

    def __init__(
        self, analyser: Path | str, generator: Path | str, search_cutoff: int = 60
    ):
        self.analyser = TransducerFile(analyser, search_cutoff)
        self.generator = TransducerFile(generator, search_cutoff)

    def analyse(
        self, input: Wordform | str, distance: None | Callable[[str, str], float] = None
    ) -> list[FullAnalysis]:
        candidate = self.analyser.weighted_lookup_full_analysis(input, self.generator)
        if distance:
            # If there is a distance function, use that for sorting
            source = str(input)

            def key(other: FullAnalysis) -> float:
                if other.standardized is None:
                    return float("+Infinity")
                return distance(source, other.standardized)

            candidate.sort(key=key)
        return candidate

    def generate(self, analysis: FullAnalysis | Analysis | str) -> list[Wordform]:
        input = (
            "".join(analysis.prefixes) + analysis.lemma + "".join(analysis.suffixes)
            if isinstance(analysis, Analysis)
            else analysis
        )
        return self.generator.weighted_lookup_full_wordform(input)
