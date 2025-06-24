#################
API documentation
#################

Basic usage
***********

``hfst-altlab`` is intended to be backwards compatible with `hfst-optimized-lookup`_.
But that package only provides a very simple interface, and requires the FST to be already formatted in the unweighted `.hfstol` format.
This package is a wrapper over the `hfst`_ package, which consumes considerably more space than `hfst-optimized-lookup`_.
If space is a strict constraint, we recommend converting your FSTs to the `hfstol` format and using the other package,
but you will lose access to sorting, flag diacritics, and weights. 

.. _hfst-optimized-lookup: http://github.com/UAlbertaALTLab/hfst-optimized-lookup
.. _hfst: https://pypi.org/project/hfst

Examples of usage
=================

If you have two FSTs, for example, `"analyser-dict-gt-desc.hfstol"` and `"generator-dict-gt-norm.hfstol"`, you can perform any searches you want::
    
    from hfst_altlab import TransducerPair
    
    p = TransducerPair(analyser="analyser-dict-gt-desc.hfstol",
                       generator="generator-dict-gt-norm.hfstol")

.. note: Most likely you will want to use a **strict** or **normative** generator.  Descriptive generators usually have a lot of ambiguity and do not produce good (nor fast) results.
.. note: For future compatibility, Analyses and Wordforms are targeted towards weighted FSTs.  If your FST is unweighted, all results will have a default weight (likely `0.0`, but you should not rely on the value provided).

:py:class:`hfst_altlab.TransducerPair` will accept any FST format accepted by the ``hfst`` package.  Including ``.hfstol``, ``.hfst``, ``.att``, and uncompressed FOMA (see the following section for details).

If you have a single FST, you can use either :py:class:`hfst_altlab.TransducerFile` objects directly, or generate the appropriate generator and analyser versions for the FST.  You can do this directly from the package. We recommend to use :py:meth:`hfst_altlab.TransducerPair.duplicate` as we intend to provide extended functionality in the future that depends on knowing both directions of the FST.

For example, if you have an `ojibwe.fomabin` FST, you can just use::
    
    p = TransducerPair.duplicate("ojibwe.fomabin")

Then we can use methods :py:meth:`hfst_altlab.TransducerPair.generate` and :py:meth:`hfst_altlab.TransducerPair.analyse` to query the FSTs::
    >>> [r.analysis for r in p.analyse("atim")]
    [Analysis(prefixes=(), lemma='atim', suffixes=('+N', '+A', '+Sg')), Analysis(prefixes=(), lemma='atimêw', suffixes=('+V', '+TA', '+Imp', '+Imm', '+2Sg', '+3SgO'))]
    >>> p.generate(Analysis(prefixes=(), lemma='atim', suffixes=('+N', '+A', '+Sg')))
    [Wordform(weight=0.0, wordform=atim)]
    >>> [str(x) for x in p.generate("atim+N+A+Sg")]
    ['atim']
    >>> {a.analysis for w in ["itwewina", "itwêwina"] for a in p.analyse(w)}
    {Analysis(prefixes=(), lemma='itwêwin', suffixes=('+N', '+I', '+Pl'))}
    >>> {w for a in p.analyse("atim") for w in p.generate(a)}
    {Wordform(weight=0.0, wordform=atim), Wordform(weight=0.0, wordform=atim)}

Note that in the last example, we seem to have two entries for the same wordform, even though we asked for a set!
The key is the comparison of both wordforms and analyses *includes flag diacritics*. If you want to observe the difference::
    >>> {w.tokens for a in p.analyse("atim") for w in p.generate(a)}
    {('@U.order.imp@', '@U.wici.NULL@', 'a', 't', 'i', 'm', '', '', '', '', '@U.wici.NULL@', '@U.order.imp@', '', '@U.person.NULL@', '', '', '', '@D.frag.FRAG@', '@D.cnj.CC@', '@D.joiner.NULL@'), ('@P.person.NULL@', '@R.person.NULL@', 'a', 't', 'i', 'm', '', '', '@R.person.NULL@', '@U.person.NULL@', '@D.number.PL@', '@R.person.NULL@', '@D.sg@', '', '@D.dim@')}


Dealing with FOMA FSTs
======================
To deal with FOMA-formatted FSTs, `foma` must be installed in the machine.  The FST also must not be compressed.
If a compressed FOMA FST is used, a `ValueError` exception is raised and instructions to build a decompressed version of the FST are printed out. 
Those instructions can be used, for example, from a python interpreter.

For example, if you try to build a :py:class:`hfst_altlab.TransducerPair` from a compressed ``.fomabin`` file like ``"ojibwe.hfstol"``, you should see the following error:

::
    >>> p = hfst_altlab.TransducerPair.duplicate("ojibwe.fomabin")
    The Transducer file ojibwe.fomabin is compressed.
    Unfortunately, our library cannot currently handle directly compressed files (e.g. .fomabin).
    Please decompress the file first.
    If you don't know how, you can use the hfst_altlab.decompress_foma function as follows:
     
     
    from hfst_altlab import decompress_foma
    with open(output_name, "wb") as f:
      with decompress_foma("ojibwe.fomabin") as fst:
        f.write(fst.read())
     
         
    ValueError: ojibwe.fomabin

Do not forget to provide the name of the file to store the decompressed FOMA, in the example, ``output_name``.

Beyond compression, the ``hfst-altlab`` package should work seamlessly independent of the format of the FST, which will be internally converted to an HFSTOL representation for optimized lookup.


Class API
*********

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

