.. include:: global.rst

++++++++
Glossary
++++++++

.. glossary::

   acronym

        `acronym <https://en.wiktionary.org/wiki/acronym>`_

	A term formed from the initial letters of several words and
	pronounced as a word, eg. laser.

	See also :term:`initialism`.

   association list

        A list of the form:

	.. code-block:: scheme

	   ((key1 value1)
	    (key2 value2)
	    ...)

   CLOS

	Common Lisp Object System -- see CLOS_.

   concomitant

        My dictionary says:

	    naturally accompanying or associated

	and with our computer science hats on we can suggest that they
	are *required* to be defined together.

	Of interest, the dictionary's etymology says:

	    early 17th century: from late Latin *concomitant*-
	    ‘accompanying’, from *concomitari*, from *con*- ‘together
	    with’ + *comitari*, from Latin *comes* ‘companion’

	So, "me and my mate" rather than, as I thought,
	co-committed/co-defined.

   grok

        to understand intuitively

	A neologism from :ref-author:`Robert A Heinlein`'s 1961 novel
	:ref-title:`Stranger in a Strange Land`.

        `grok <https://en.wikipedia.org/wiki/Grok>`_

   homoiconicity

        `Homoiconicity <https://en.wikipedia.org/wiki/Homoiconicity>`_
        is defined as:

	    A language is homoiconic if a program written in it can be
	    manipulated as data using the language, and thus the
	    program's internal representation can be inferred just by
	    reading the program itself.

	Although whether :lname:`Lisp`\ s are actually homoiconic and
	quite what homoiconic actually means is often a cause for
	debate.

   initialism

        `initialism <https://en.wiktionary.org/wiki/initialism>`_

	A term formed from the initial letters of several words and
	pronounced letter by letter, eg. BBC.

	See also :term:`acronym`.

   marmite

	.. _Marmite: https://www.marmite.co.uk

        As the `Wikipedia <https://en.wikipedia.org/wiki/Marmite>`_
        page on Marmite_ notes:

	    Such is its prominence in British popular culture that the
	    product's name is often used as a metaphor for something
	    that is an acquired taste or tends to polarise opinions.

   metacircular evaluator

        An evaluator that can evaluate itself!  First described in the
        original paper on :lname:`Lisp`, :ref-author:`John McCarthy`'s
        :ref-title:`Recursive Functions of Symbolic Expressions and
        Their Computation by Machine, Part I` :cite:`jmc-recursive`
        where he discusses ``eval`` as a theoretical exercise.

   MOP

	Meta Object Protocol -- see `Meta Object Protocol`_.

   n-ary

	Takes :samp:`{n}` arguments, more than *unary*, *binary* or
	*ternary*!

        See `Arity <https://en.wikipedia.org/wiki/Arity>`_

   reader

	the function that reads input from the user or script and
	determines, based on context, how to represent that input in
	the syntax tree.

   REPL

	Read-Evaluate-Print-Loop

   Tiny-CLOS

	Gregor Kiczales' implementation of a :term:`CLOS` -- see
	`Tiny-CLOS`_.

   UCD

        `Unicode Character Database`_

   VDU

	Visual Display Unit.  The screen and keyboard combo boxes
	pre-dating separate monitor and keyboards.  Usually attached
	by a serial line to a mainframe.  See `Computer terminal`_.

.. _CLOS: http://en.wikipedia.org/wiki/Common_Lisp_Object_System

.. _`Meta Object Protocol`: http://community.schemewiki.org/?meta-object-protocol

.. _`Tiny-CLOS`: http://community.schemewiki.org/?Tiny-CLOS

.. _`Computer terminal`: https://en.wikipedia.org/wiki/Computer_terminal

.. include:: commit.rst

