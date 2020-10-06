.. include:: ../../global.rst

***************
Pairs and Lists
***************

Pairs are the fundamental compound type of any :lname:`Lisp` language.

In :lname:`Scheme` a ``.`` U+002E (FULL STOP) is used to separate the
elements of a pair creating a visual distinction between a
*dotted-pair* and a *list*:

* ``(1 . 2)`` -- a dotted-pair

* ``(1 2)`` -- a list which is technically two dotted-pairs, ``(1 . (2
  . nil))``

.. aside::

   The *word* `ampersand <https://en.wikipedia.org/wiki/Ampersand>`_
   appears to be a late 18\ :sup:`th` century derivation from an
   alteration of the self-affirming "and per se and" where the first
   "and" is the symbol & -- "& is by itself 'and'".

   The glyph, &, appears to be the result of a ligature of the letters
   'e' and 't' from the Latin, "et" meaning "and."  There is
   supposedly some graffiti preserved at Pompeii as an example.

I wanted to use ``.`` for a ``value-index`` operator which meant I
needed an alternative character for dotted-pairs.  I chose ``&``
U+0026 (AMPERSAND), possibly unwisely, but its sentiment is about
right: ``a b & c`` is ``a``, ``b`` *and* (the rest in) ``c`` -- was
the use-case I was worrying about albeit that I intend to rework that
as ``a b c*`` at some point.

Of course, using an ampersand in a dotted-pair is completely at odds
with our shell-dogma that ``&`` means put the pipeline in the
background.

Given that a dotted-pair (effectively) mandates whitespace around the
``.`` and that the ``value-index`` operator should not, then I might
reverse that decision.

Should ``&``, the instruction to background, always have to appear
*after* the pipeline?  That's an interesting question.  I can
understand that as a combined end-of-statement and backgrounding sigil
it works very well.

At the time of writing there isn't a statement separator at all in
:lname:`Idio` -- barring newline -- so maybe this is another shell-ism
that can be reconsidered.

Much like invoking the shell builtin, :program:`time`, which is
followed by the command you intend to get timing metrics for, perhaps
the :program:`bg` builtin should be indicating that you want the
*following* pipeline to be backgrounded:

.. code-block:: idio

   bg zcat file | tar xf -

I'm OK with that.  It fits in better with a general sense of
:samp:`{command} {args}` where it so happens that :samp:`{args}` is
itself :samp:`{command'} {args'}` and with the general
:lname:`Scheme`\ ly sense of :samp:`{command} {args}` within a form.

Implementation
==============

The implementation is as simple as you would expect and there are the
same set of funky ``IDIO_PAIR_HTT()`` macros defined as appear to be
needed in the :lname:`C` code base, much like the ``phtt`` functions
in :lname:`Idio`.

.. code-block:: c
   :caption: gc.h

   typedef struct idio_pair_s {
       struct idio_s *grey;
       struct idio_s *h;
       struct idio_s *t;
   } idio_pair_t;

   #define IDIO_PAIR_GREY(P)	((P)->u.pair.grey)
   #define IDIO_PAIR_H(P)	((P)->u.pair.h)
   #define IDIO_PAIR_T(P)	((P)->u.pair.t)

   #define IDIO_PAIR_HH(P)	IDIO_PAIR_H (IDIO_PAIR_H (P))
   #define IDIO_PAIR_HT(P)	IDIO_PAIR_H (IDIO_PAIR_T (P))
   #define IDIO_PAIR_TH(P)	IDIO_PAIR_T (IDIO_PAIR_H (P))
   #define IDIO_PAIR_TT(P)	IDIO_PAIR_T (IDIO_PAIR_T (P))

   ...

In addition we have some :lname:`C` macros to help with the
construction of lists:

.. code-block:: c
   :caption: pair.h

   #define IDIO_LIST1(e1)		idio_pair (e1, idio_S_nil)
   #define IDIO_LIST2(e1,e2)		idio_pair (e1, idio_pair (e2, idio_S_nil))
   ...
   #define IDIO_LIST5(e1,e2,e3,e4,e5)	idio_pair (e1, ...)

Reading
-------

.. sidebox:: Notably, not ``make-pair`` and ``make-list``.
             :lname:`Scheme`\ rs are lazy programmers too!

Normally pairs and lists are constructed with ``pair`` and ``list``
with ``pair`` taking precisely two arguments and list taking zero or
more.  A zero-element list is equivalent to ``#n``.

Alternatively, both can be quoted expressions:

* dotted pairs are :samp:`'({value1} & {value2})`

* lists are :samp:`'({value} ...)`

although, obviously, being quoted, the values cannot be variables --
or, rather, any symbols will remain so (and not evaluated) which is
the very point of quoting.

Writing
-------

No particular surprise with dotted pairs being printed as
:samp:`({value1} & {value2})` and lists as :samp:`({value} ...)`.

Pairs and lists occupy a slightly strange place because of
:term:`homoiconicity` in that they are they building blocks of the
language *itself* as well as being data structures within it.

This is similar to the way that :ref:`symbols` can be values to be
passed around as well as variable names.  Which role they play is
context dependent.
