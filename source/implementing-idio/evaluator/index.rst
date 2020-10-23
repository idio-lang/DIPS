.. include:: ../../global.rst

*************
The Evaluator
*************

The evaluator's role is to infer some meaning from the reader-supplied
lists of lists.

Evaluation is a slight misnomer.  The evaluator has a hidden task
which confuses and exasperates in equal measure.  If a *template* is
identified then the template is *expanded* and the result is
(re-)evaluated.  This is problematic because :lname:`Idio` code is
going to be run *during* evaluation.  `Ducks in a row
<https://en.wiktionary.org/wiki/have_one%27s_ducks_in_a_row>`_,
people, ducks in a row.

You get used to it!  *-ish!*

If this was an interpreter then as soon as the evaluator has decided
that something is, say, a function call then it can immediately invoke
the function value with the argument values (having evaluated
everything).

:lname:`Idio`, following in the style of :ref-title:`LiSP`
(:cite:`LiSP`) instead generates code for the virtual machine and then
asks the virtual machine to run it.

Ostensibly, that doesn't sound terribly different but we're advancing
two causes in this approach:

#. we've stopped using variable names (mostly) -- although that's
   possible for a interpreter too.  See :ref-title:`LiSP` for the
   details of a fast interpreter.

#. we're generating lean and mean byte code

   Sort of.  Generating byte code *at all* is a huge leap forward in
   terms of processing speed.

There are further opportunities in and around the evaluator as well,
primarily in the form of optimisation.

.. toctree::
   :maxdepth: 2

   evaluating
.. expanding
.. code generation

.. include:: ../../commit.rst

