import hfst
import gzip
from pathlib import Path
from .types import Analysis, FullAnalysis, Wordform, as_fst_input, fst_output_format
from typing import cast, Optional
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

    :param filename: The path of the transducer
    :param search_cutoff: The maximum amount of time (in seconds) that the search will go on for.  The intention of a limit is to avoid search getting stuck.  Defaults to a minute.
    """

    def __init__(self, filename: Path | str, search_cutoff: int = 60):
        self.cutoff = search_cutoff

        if not Path(filename).exists():
            exn = FileNotFoundError(f"Transducer not found: ‘{str(filename)}’")
            raise exn

        # Now we extract the transducer and store it.
        try:
            # Workaround for FOMABIN formats
            with open(filename, "rb") as f:
                if f.read(3) == b"\x1f\x8b\x08":
                    # It is a gzipped file!
                    print(
                        "\n".join(
                            [
                                f"The Transducer file {filename} is compressed.",
                                "Unfortunately, our library cannot currently handle directly compressed files (e.g. .fomabin).",
                                "Please decompress the file first.",
                                "If you don't know how, you can use the hfst_altlab.decompress_foma function as follows:\n\n",
                                "from hfst_altlab import decompress_foma",
                                'with open(output_name, "wb") as f:',
                                f'  with decompress_foma("{str(filename)}") as fst:',
                                f"    f.write(fst.read())\n\n",
                            ]
                        )
                    )
                    raise ValueError(filename)
                else:
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
            print(f"Warning: The transducer at {filename} is infinitely ambiguous.")
        if not (
            self.transducer.get_type()
            in [
                hfst.ImplementationType.HFST_OL_TYPE,
                hfst.ImplementationType.HFST_OLW_TYPE,
            ]
        ):
            print("Transducer not optimized.  Optimizing...")
            self.transducer.convert(hfst.ImplementationType.HFST_OLW_TYPE)
            self.transducer.lookup_optimize()
            print("Done.")

    def bulk_lookup(self, words: list[str]) -> dict[str, set[str]]:
        """
        Like ``lookup()`` but applied to multiple inputs. Useful for generating multiple
        surface forms.

        .. note:: Backwards-compatible with ``hfst-optimized-lookup``

        :param words: list of words to lookup
        :return: a dictionary mapping words in the input to a set of its tranductions
        """
        return {word: set(self.lookup(word)) for word in words}

    def lookup(self, input: str) -> list[str]:
        """
        Lookup the input string, returning a list of tranductions.  This is
        most similar to using ``hfst-optimized-lookup`` on the command line.

        .. note:: Backwards-compatible with ``hfst-optimized-lookup``

        :param input: The string to lookup.
        :return: list of analyses as concatenated strings, or an empty list if the input
            cannot be analyzed.
        """
        return ["".join(transduction) for transduction in self.lookup_symbols(input)]

    def lookup_lemma_with_affixes(self, surface_form: str) -> list[Analysis]:
        """
        Like lookup, but separates the results into a tuple of prefixes, a lemma, and a tuple of suffixes.  Expected to be used only on analyser FSTs.

        .. note:: Backwards-compatible with ``hfst-optimized-lookup``

        :param surface_form: The entry to search for.
        """
        return [
            analysis.analysis
            for analysis in self.weighted_lookup_full_analysis(surface_form)
        ]

    def lookup_symbols(self, input: str) -> list[list[str]]:
        """
        Transduce the input string. The result is a list of tranductions. Each
        tranduction is a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        .. note:: Backwards-compatible with ``hfst-optimized-lookup``

        :param input: The string to lookup.
        """
        return [
            [x for x in analysis.tokens if x and not hfst.is_diacritic(x)]
            for analysis in self.weighted_lookup_full_analysis(input)
        ]

    def _weighted_lookup(self, input: str) -> list[tuple[str, tuple[str, ...]]]:
        """
        Internal Function. Transduce the input string. The result is a list of weighted tranductions. Each
        weighted tranduction is a tuple with a number for the weight and a list of symbols returned in the model; that is, the symbols are
        not concatenated into a single string.

        :param input: The string to lookup.
        :return:
        """
        return cast(
            list[tuple[str, tuple[str, ...]]],
            self.transducer.lookup(str(input), time_cutoff=self.cutoff, output="raw"),
        )

    def weighted_lookup_full_analysis(
        self, wordform: str | Wordform, generator: Optional["TransducerFile"] = None
    ) -> list[FullAnalysis]:
        """
        Transduce a wordform into a list of analyzed outputs.  This method is likely only useful for analyser FSTs.

        If a generator is provided, it will incorporate a standardized version of the string when available.
        That is, it will pass the output to a secondary FST, and check if all the outputs of that "generator" FST match for an output.
        If so, the output will be marked with the output string in the `standardized` field (See :py:class:`hfst_altlab.FullAnalysis`)

        :param wordform: The string to lookup.
        :param generator: The FST that will be used to fill the standardized version of the wordform from the produced analysis.
        """
        if generator:

            def generate(tokens: tuple[str, ...]) -> str | None:
                entry: str | None = None
                for _, output in generator._weighted_lookup(fst_output_format(tokens)):
                    candidate = "".join(x for x in output if x and not hfst.is_diacritic(x))
                    if entry and entry != candidate:
                        return None
                    else:
                        entry = candidate
                return entry

        else:

            def generate(tokens: tuple[str, ...]) -> str | None:
                return None

        return [
            FullAnalysis(float(weight), tokens, generate(tokens))
            for weight, tokens in self._weighted_lookup(as_fst_input(wordform))
        ]

    def weighted_lookup_full_wordform(
        self, analysis: str | FullAnalysis
    ) -> list[Wordform]:
        """
        Transduce the input string. The result is a list of weighted wordforms. This method is likely only useful for generator FSTs.

        :param analysis: The string to lookup.
        :return:
        """
        return [
            Wordform(float(weight), tokens)
            for weight, tokens in self._weighted_lookup(as_fst_input(analysis))
        ]

    def symbol_count(self) -> int:
        """
        Returns the number of symbols in the sigma (the symbol table or alphabet).

        .. note:: Backwards-compatible with ``hfst-optimized-lookup``

        """
        return len(self.transducer.get_alphabet())

    def invert(self) -> None:
        """
        Invert the transducer.  That is, take what previously were outputs as inputs and produce as output what previously were inputs.

        Although the same process can be done directly on the terminal, the intention of this method is to provide an easy way of obtaining the inverse FST.

        .. warning:: Because the ``hfst`` python package cannot currently invert HFSTOL FSTs, we first convert the transducer to an SFST formatted equivalent.  If for any reason you find out that the inverted FST is providing unexpected results, report a bug.
        """
        # Unfortunately, hfst does not directly invert hfstol FSTs.
        # We take a detour by changing to a different format.
        # We do not use foma here just in case we are not dealing with a system that has foma.
        self.transducer.convert(hfst.ImplementationType.SFST_TYPE)
        self.transducer.invert()
        self.transducer.lookup_optimize()
        return None


class TransducerPair:
    """
    This class provides a useful wrapper to combine an analyser FST and a generator FST for the same language.
    It also provides sorted search when a distance function between two strings is provided.

    For the cases when only a single FST is available but sorting is desired, use the :py:meth:`hfst_altlab.TransducerPair.duplicate` factory method, which produces a TransducerPair from a single FST.

    On initialization, this class generates two :py:class:`hfst_altlab.TransducerFile` objects.

    :param analyser: The path to the analyser FST (input: wordform, output: analyses)
    :param generator: The path to the generator FST (input:analysis, output: wordforms)
    :param search_cutoff: The maximum amount of time allowed for lookup on each transducer.
    :param default_distance: An optional function providing a distance between two strings. (see :py:meth:`hfst_altlab.TransducerPair.analyse`)
    """

    analyser: TransducerFile
    generator: TransducerFile
    default_distance: None | Callable[[str, str], float]

    def __init__(
        self,
        analyser: Path | str,
        generator: Path | str,
        search_cutoff: int = 60,
        default_distance: None | Callable[[str, str], float] = None,
    ):
        self.analyser = TransducerFile(analyser, search_cutoff)
        self.generator = TransducerFile(generator, search_cutoff)
        self.default_distance = default_distance

    def analyse(
        self, input: Wordform | str, distance: None | Callable[[str, str], float] = None
    ) -> list[FullAnalysis]:
        """
        Provide a list of analysis for a particular wordform using the analyser FST of this object.

        If a `distance` function is provided (or the object has a `default_distance` property),
        the results provided by the FST are sorted using the function to compute a distance between the
        input wordform and the standardized wordform associated with each analysis (the result of applying the generator FST, if unique)

        :param input: The wordform to analyse.
        :param distance: The sorting function for this particular method call.  When it is not `None`, it overrides `default_distance`, but only for this particular call.
        """
        candidate = self.analyser.weighted_lookup_full_analysis(input, self.generator)
        sort_function = distance or self.default_distance
        if sort_function:
            # If there is a distance function, use that for sorting
            source = str(input)

            def key(other: FullAnalysis) -> float:
                if other.standardized is None:
                    return float("+Infinity")
                return sort_function(source, other.standardized)

            candidate.sort(key=key)
        return candidate

    def generate(self, analysis: FullAnalysis | Analysis | str) -> list[Wordform]:
        """
        Provide a list of wordforms for a particular analysis using the generator FST of this object.

        :param analysis: The analysis to generate via the FST.
        """
        input = (
            "".join(analysis.prefixes) + analysis.lemma + "".join(analysis.suffixes)
            if isinstance(analysis, Analysis)
            else analysis
        )
        return self.generator.weighted_lookup_full_wordform(input)

    @classmethod
    def duplicate(
        cls,
        transducer: Path | str,
        is_analyser: bool = False,
        search_cutoff: int = 60,
        default_distance: None | Callable[[str, str], float] = None,
    ):
        """
        Factory Method.  Generates a TransducerPair from a single FST.  You can use the is_analyser argument to tell the direction of the input FST.  Note that the FST will be generated twice before inverting one.

        :param transducer: The location of the single FST used to generate a :py:class:`hfst_altlab.TransducerPair` object.
        :param is_analyser: If true, then the generator FST is generated by inverting.  If false, then the analyser FST is generated by inverting.
        :param search_cutoff: The maximum amount of time (in seconds) that the search will go on for.  The intention of a limit is to avoid search getting stuck.
        :param default_distance: An optional function providing a distance between two strings. (see :py:meth:`hfst_altlab.TransducerPair.analyse`)
        """
        object = cls(
            transducer,
            transducer,
            search_cutoff=search_cutoff,
            default_distance=default_distance,
        )
        if is_analyser:
            object.generator.invert()
        else:
            object.analyser.invert()
        return object


def decompress_foma(filename: Path | str):
    """
    Single wrapper around gzip. This is to increase readability.
    This method is not used, but it is suggested as a way to debug the process of building a Transducer from a FOMA object.
    """
    return gzip.open(filename)
