API documentation
=================

Basic usage
-----------

``hfst-altlab`` is intended to be backwards compatible with `hfst-optimized-lookup`_.
But that package only provides a very simple interface, and requires the FST to be already formatted in the unweighted `.hfstol` format.
This package is a wrapper over the `hfst`_ package, which consumes considerably more space than `hfst-optimized-lookup`_.
If space is a strict constraint, we recommend converting your FSTs to the `hfstol` format and using the other package,
but you will lose access to sorting, flag diacritics, and weights. 

.. _hfst-optimized-lookup: http://github.com/UAlbertaALTLab/hfst-optimized-lookup
.. _hfst: https://pypi.org/project/hfst

Dealing with FOMA FSTs
----------------------
To deal with FOMA-formatted FSTs, `foma` must be installed in the machine.

TransducerFile
--------------

.. autoclass:: hfst_altlab.TransducerFile
    :members:


TransducerPair
--------------
This class is a wrapper on :py:class:`hfst_altlab.TransducerFile` that has several convenient methods
to deal with two complementary FSTs that go in opposite directions, an analyser and a generator.

The generator is used to provide a standardized form in each result of an analysis.

The key use case for TransducerPair is to combine a descriptive analiser FST and a normative generator FST.

We provide a convenience factory method to generate a TransducerPair using a single FST by inverting it to provide the other FST.

It can also be used to provide a way to sort the outputs of the Analysis FST.  For example, using Levenshtein distances:


.. autoclass:: hfst_altlab.TransducerPair
    :members:

Wordform
--------
.. autoclass:: hfst_altlab.Wordform
    :members:


Analysis
--------
The same class as in `hfst-optimized-lookup`_.

.. autoclass:: hfst_altlab.Analysis
    :members:

FullAnalysis
------------
An extension of :py:class:`hfst_altlab.Analysis`, to include possible weights, flag diacritics, and a standardized version of the wordform, obtained by a separate FST.

.. autoclass:: hfst_altlab.FullAnalysis
    :members:

