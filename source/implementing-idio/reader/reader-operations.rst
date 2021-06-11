.. include:: ../../global.rst

*****************
Reader Operations
*****************

In the old days they were called "reader macros" as they transform the
program structure that was being read in.

You used to get (maybe in :lname:`Common Lisp` rather than
:lname:`Scheme`) little tricks like:

.. parsed-literal::

   #+\ *feature* *form*

Such that :samp:`{form}` would only be included from the input stream
if :samp:`{feature}` was true.  ``#-`` was the inverse.

There's a wall of :lname:`Common Lisp` reader macros `here
<https://www.cs.cmu.edu/Groups/AI/html/cltl/clm/node191.html>`_.

The ``#+`` functionality is reworked into the ``cond-expand`` function
from SRFI-0_.

One thing to recognise is that the reader macro is, in essence, in
functional position, ie. we read it in first, before the actual
expression it was about to "transform."

Quoting
=======

The reader macros left in :lname:`Scheme` are basically a form of
shorthand for lazy programmers (*woo!*).  The canonical reader macro
is quote, ``'``:

.. parsed-literal::

   '\ *thing*

is transformed by the reader into

.. parsed-literal::

   (quote *thing*)

such that the evaluator is now getting a normalised form.

Similarly, the other quasi-quoting characters are used in the same
way:

.. csv-table:: Reader expansions of quasi-quoting characters
   :widths: auto
   :align: left

   :samp:`${thing}`, :samp:`(unquote {thing})`
   :samp:`$@{thing}`, :samp:`(unquote-splicing {thing})`

Slightly differently, the *escape* character is used to suppress the
reader macro behaviour:

.. csv-table:: Reader escape character uses
   :widths: auto
   :align: left

   :samp:`\\${thing}`, :samp:`${thing}`

In :lname:`Idio` we don't have the :lname:`Scheme` quasi-quoting
character, :literal:`\``, itself.  We've replaced :samp:`\`{thing}`
with :samp:`#T\\{ {thing} }`.

Operators
=========

That doesn't help us much with infix (and postfix) operators which is
something we want for pipelines and arithmetic.

Also, I don't want to have to write these in :lname:`C` -- a total
pain.

We need something akin to the templates model used by the evaluator.
We need something to define an implementation of an operator and to
tag it in the reader such that when the reader has read in a complete
line-oriented expression it can scan along looking for operators and
apply their implementation to the expression.

So, we want to define an *operator*, ``+``, that can transform the
expression ``1 + 2`` into ``+ 1 2`` where the symbol ``+`` in
functional position will be evaluated into the arithmetic addition
primitive (hopefully).

But before we dive in we need to think a little bit more carefully.

.. parsed-literal::

   *this* | *that* | *the-other* or *something-else*

where there are different operators in the same expression.  ``or`` is
less tightly binding than ``|`` so you sense the first transform would
be into:

.. parsed-literal::

   (or (*this* | *that* | *the-other*)
       *something-else*)

which implies there is a priority or ordering associated with each
operator.

Having performed the first, the second transformation would give us:

.. parsed-literal::

   (or (| *this*
          *that*
	  *the-other*)
       *something-else*)

That's fairly easy.  Although we've already taken two ideas on board:

#. there's a precedence between operators

#. recursion is required to apply transformations on the
   sub-expressions the first transformation generated

It's more complicated with some operators like arithmetic ones which
are *binary*, ie. take two arguments -- at least in their infix
operator form.  ``+``, the function, takes any number of arguments.
In an effort to speed things up a tiny amount, the infix arithmetic
operators call :samp:`binary-{op}` rather than :samp:`{op}`.

:samp:`{x} + {y}` is easily transformed into :samp:`(+ {x} {y})` and
leading to the semantically questionable :samp:`{f} {x} + {y}`
becoming :samp:`{f} (+ {x} {y})`.  Is that what we expect?

What about :samp:`{x} + {y} + {z}`?  Ideally that would become
:samp:`(+ {x} {y} {z})` but in practice we're likely to have a
*left-associative* formulation like :samp:`(+ {x} {y}) + {z}` then
:samp:`(+ (+ {x} {y}) {z})`.

The left-association helps us with :samp:`{x} + {y} - {z}` which
becomes :samp:`(- (+ {x} {y}) {z})`.

Having defined the operator, ``+``, say, I don't then want to repeat
the implementation for the essentially identical ``-`` operator.  I
could do with some means to re-use the implementation of ``+`` for
``-``.

The obvious thing to do is use the symbol ``+`` instead of an
implementation suggesting to the operator management code that it
looks up the implementation of the operator ``+`` and uses that.

Pretty straightforward except that a ``+`` anywhere in the line
(except in functional position) is the operator ``+`` and the reader
will head of to do its thing.  *\*Bah!\** The trick is, of course, to
escape the symbol, as in ``\+`` or ``'+`` to avert the reader's gaze.

This doesn't always scan well as running a command with no
environment:

.. code-block:: idio

   env '- ...

shows.  Without the quote you'll probably get a complaint that the
symbol ``env`` is not a number.

Operator Definition
-------------------

The definition of an operator could be simpler -- perhaps it needs a
revisit.

.. parsed-literal::

   define-infix-operator *name* *pri* *body*

where :samp:`{name}` is the symbol for the operator, ``+``, ``and``,
etc., :samp:`{pri}` is the operator's relative priority (higher
numbers are considered/processed first) and :samp:`{body}` is the
operator's implementation's body (or an escaped :samp:`{name}` of a
previously defined operator to re-use the same implementation).

The :samp:`{body}` is the body of a function that will have been
defined as:

.. parsed-literal::

   function (op before after) *body*

You can see the evaluator construct this function in
``idio_meaning_define_infix_operator()`` in :file:`evaluate.c`:

.. code-block:: c

   IDIO def_args = IDIO_LIST3 (idio_S_op, idio_S_before, idio_S_after);

   IDIO fe = IDIO_LIST4 (idio_S_function,
			 def_args,
			 idio_meaning_define_infix_operator_string,
			 e);

where we construct a function ``fe`` for the body ``e`` ("e" for the
expression being processed, currently the operator body) using the
formal parameters: the symbols, ``op``, ``before`` and ``after``.
(:samp:`idio_S_{X}`, knowing the :lname:`C` naming convention, will be
the symbol for :samp:`{X}`.)

The constructed function, ``fe``, will now be thrown at the evaluator
to figure out its meaning.

In other words the symbols ``op``, ``before`` and ``after`` can
(must?) be used in :samp:`{body}`.

As the reader, via ``idio_operator_expand()``, scans the expression
read in it will identify any operators (highest priority first, left
to right) and invoke the implementation with the particular operator
it found (in case the implementation's body is re-used), the part of
the expression it found before the operator and the part of the
expression it found after the operator.

Binary Operators
^^^^^^^^^^^^^^^^

For a putative arithmetic ``+`` operator, given the expression
:samp:`({x} + {y})`, then the operator's implementation will invoked
as:

.. parsed-literal::

   *body* + (*x*) (*y*)

which looks easy enough to rework into :samp:`(+ {x} {y})`.

However, we could have written :samp:`(foo {x} + {y} bar)` in which
case we'd see the operator's implementation invoked as:

.. parsed-literal::

   *body* + (foo *x*) (*y* bar)

and we need to be a bit more careful to get :samp:`(foo (+ {x} {y})
bar)`.

    It might make more sense to reject such an expression as it is
    easy to misinterpret.  Perhaps the operators which are known
    binary operators should call foul if the number of argument in the
    before/after lists are not equal to one.  That would force the
    previous statement to be re-written as :samp:`(foo ({x} + {y})
    bar)` which at least clarifies the user's intent.

    It isn't always that easy, though, as it depends on what the
    ordering of operators is.  As it happens, the ``.`` operator is
    processed before ``+`` so the expression :samp:`{a}.{i} + {b}`
    (adding to an element of an array, say) where the ``.`` is a word
    separator, ie. :samp:`{a} . {i} + {b}`, which *might* have been
    seen by the ``+`` operator with the ``before`` value being
    :samp:`({a} . {i})`, a list of three elements, which would fail
    the single element before test.

    As it happens, ``.`` *is* processed first so that for ``+`` the
    ``before`` value is :samp:`((value-index {a} {i}))` which is a
    list of one element (which itself is a list of three elements).

Logical Operators
^^^^^^^^^^^^^^^^^

The logical operators, ``and`` and ``or`` -- rather than :lname:`C`'s
``&&`` and ``||``, take *single expressions* and combine into a single
operation on adjacent like-operators.

This means that ``1 and 2 and 3 or 4 and 5`` becomes, first, ``(and 1
2 3) or 4 and 5`` then ``(or (and 1 2 3) 4) and 5))`` then, finally,
``(and (or (and 1 2 3) 4) 5)``.

Which doesn't look like the idealised ``(or (and 1 2 3) (and 4 5))``
but I think is functionally correct.  Probably.

Arbitrary Word List Operators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There *are* operators that do take argument lists of arbitrary length,
``|`` is an example, defined in :file:`job-control.idio`.

``|``, the operator, also performs the functionality you would expect
of a ``|``, the function.  I'm not sure why I wrote it that way.
Perhaps, because I could.

Assignment Operators
^^^^^^^^^^^^^^^^^^^^

Assignment operators are slightly different to the other in that they
*are* implemented in :lname:`C` as they are so convenient for all
:lname:`Idio` code right from the off.

They differ slightly in that, having determined the entity to be
assigned to, the right hand size is explicitly operator-expanded.

Standard Operators
------------------

:lname:`Idio` defines some operators by default.

From :file:`operator.idio`:

Infix arithmetic operators: ``+``, ``-``, ``*`` and ``/``.

Infix logical operators: ``and`` and ``or``.

Infix array operators: ``=+`` for :ref:`array-push! <array-push>` and
``+=`` for :ref:`array-unshift! <array-unshift>`.  For a mnemonic,
think of the ``+`` before after or before the ``=``.

Postfix array operators: ``=-`` for :ref:`array-pop! <array-pop>` and
``-=`` for :ref:`array-shift! <array-shift>`.

Infix ``value-index`` operator, ``.`` which will transform
:samp:`{s}.{i}` for some indexable value :samp:`{s}` into
:samp:`(value-index {s} {i})`.

The ``value-index`` operator is fraught with problems as ``.``\s
appear in numbers, ``3.14``, symbols, ``...``, (used in syntax
expansion) and pathnames, ``./bin``.

Numbers and symbols can be handled as we don't allow numbers without a
leading digit and we specifically check for a following ``.`` for
``...``.

Pathnames are more interesting.  In general we would have pathnames
managed distinctly as, say, strings, ``ls "./bin"`` however, in the
case of command names, that would feel wrong: :samp:`"./bin/cmd"
{args}` -- and we can't execute strings.  In this case, we'll
specifically look for a following ``/`` and presume it is a word
beginning ``./`` and not an indexing operation.

If you really wanted to index something by a symbol beginning with
``/`` then add some whitespace:

.. code-block:: idio-console

   Idio> ht := (make-hash)
   #{ }
   Idio> ht . /bin = 3
   #<unspec>
   Idio> ht
   #{ (/bin & 3)}



From :file:`job-control.idio`:

Infix operator ``|`` for pipelines.

Infix operators ``>``, ``<`` and ``2>`` which will redirect *stdin*,
*stdout* or *stderr* to

* a handle (file or string)

  .. code-block:: idio

     osh := (open-output-string)
     ls -l > osh
     str := get-output-string osh

  For that particular example, you feel that:

  .. code-block:: idio

     ls -l > str

  should be enough.  Not yet, though.

* a file (using a string as the file name)

  .. code-block:: idio

     ls -l > "/dev/null"

* :file:`/dev/null` using ``#n``.

  .. code-block:: idio

     ls -l > #n

Infix operators ``>&``, ``<&`` and ``2>&`` which will
:manpage:`dup(2)` *stdin*, *stdout* or *stderr* into the provided
handle (file or string) or :manpage:`dup2(2)` into the provided
:lname:`C` ``int`` (an ``IDIO`` ``C_int`` type) or *fixnum* file
descriptor.

(You will often get a ``C_int`` type returned from a ``libc`` call.)

Operator Functions
------------------

:samp:`infix-operator? {o}`

   test if :samp:`{o}` is an infix operator

:samp:`postfix-operator? {o}` 

   test if :samp:`{o}` is a postfix operator

:samp:`operator? {o}` 

   test if :samp:`{o}` is an operator

:samp:`infix-operator-expand {e}` 

:samp:`postfix-operator-expand {e}` 

:samp:`operator-expand {e}` 

   expand expression :samp:`{e}` for infix/postfix/all operators

   You may need to quote the expression:

   .. code-block:: idio

      Idio> infix-operator-expand '(1 + 2 - 3 + 4)
      (+ (- (+ 1 2) 3) 4)


``infix-operator-precedence-table``

``postfix-operator-precedence-table``

   display the current infix/postfix operator tables

.. include:: ../../commit.rst

