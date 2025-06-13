hfst-altlab
===========

A wrapper on the [hfst][] python package, currently working as a replacement for [hfst-optimized-lookup][], built for [itwêwina][].

[itwêwina]: https://itwewina.altlab.app
[hfst-optimized-lookup]: https://github.com/UAlbertaALTLab/hfst-optimized-lookup
[hfst]: https://pypi.org/project/hfst/

Languages currently supported:
  - [python](python)

[hfst] is a great toolkit with all sorts of functionality, and is
indispensable for building FSTs, but for various applications that only
want to do unweighted hfstol lookups, this package may be easier to use.

[hfst]: https://github.com/hfst/hfst

Although eventually we want to restore maintenance of the [hfst-optimized-lookup][] package, as it follows a more lightweight approach, we are in the process of contacting the maintainers of the pypi package to take over.  In the meantime, we want to use this project as an upstream-synced implementation and as a way to explore more advanced behaviours that can be useful for many language projects (especially for [morphodict][]). In particular, we wanted to extend the API to account for weighted FSTs and we intend to explore making flag diacritics available in the not-so-distant future.

[morphodict]: https://github.com/UAlbertaALTLab/morphodict
