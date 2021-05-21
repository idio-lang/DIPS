.. include:: ../global.rst

*************
Scheme Basics
*************

.. aside:: Hey, buddy, some of us *aspire* to writing an ad hoc,
           informally-specified, bug-ridden, slow implementation of
           half of Common Lisp!

.. epigraph::

   Any sufficiently complicated C or Fortran program contains an ad
   hoc, informally-specified, bug-ridden, slow implementation of half
   of Common Lisp.

   -- Greenspun's tenth rule

Obligatory, relevant XKCD:

.. image:: https://imgs.xkcd.com/comics/lisp_cycles.png
   :target: https://xkcd.com/297/

Why :lname:`Scheme`?  :lname:`Scheme` is incredibly simple so should
be easy to understand the implementation of (famous last words) but
has a sophistication that rivals any other programming language and
surpasses most *[citation needed]*.

If it's that good, then why haven't :lname:`Scheme` (and any other
Lisp-like language, say, :lname:`Common Lisp`) taken over the world?
Almost certainly the first reason is that it looks too alien for our
ALGOL_ accustomed eyes -- Lisps are *L*\ ots of *I*\ rritating *S*\
tupid *P*\ arentheses, as the old gag goes -- but it might be that it
is too different in other ways.  We shall see.

.. sidebox:: The language's name was :lname:`Schemer` but fell victim
             to the original implementation's file system limits of
             six character entries.

:lname:`Scheme` is *a* :lname:`Lisp` -- there are lots of
:lname:`Lisp`\ s -- with a distinction that the core consists of half a
dozen *forms* which, combined with :lname:`Scheme`'s use of
:term:`homoiconicity`, allows you to build anything else.

.. sidebox:: Whilst lines can be quite long in :lname:`Brainfuck` I
             suspect this is one shout we won't see.

This ease of implementation allows for many shouts of "I've
implemented :lname:`Scheme` in 50 lines of :lname:`Brainfuck`!" and
more general use in academia as a pedagogical tool.

The downside of that small core implementation means that, nominally,
:lname:`Scheme` doesn't have arrays, hash tables, indeed, much of
anything.  People wanted some standard libraries and standardisation,
for that matter, and so a series of :ref-title:`Revised Report on
Scheme` then :ref-title:`Revised Revised Report on Scheme` (becoming
:ref-title:`Revised`:superscript:`2` :ref-title:`Report on Scheme` or,
more commonly, :ref-title:`R2RS`) through to the current
:ref-title:`R7RS small`.  :ref-title:`R6RS` caused something of a
stink by departing from the minimalist feel resulting in the decision
to split :lname:`Scheme` into large and small variants.

Basic Operations
================

:lname:`Scheme` only really has two high level operations: a *reader*
reads in source code and having de-/re-constructed it, much like a
lexer, passes it on to the *evaluator*.  The evaluator does all the
heavy lifting.

These two are generally called in a loop:

#. read an expression

#. evaluate it

#. loop back to the start

There is a variation on this for interactive sessions which looks
like:

#. read an expression

#. evaluate it

#. print the result

#. loop back to the start

Which give us the well-known acronym, :abbr:`REPL (Read Evaluate Print
Loop)`.

Reader
------

The reader isn't quite innocent, it is gifted with a few the power to
do a few re-writes, usually trivial and accommodating the laziness
inherent in all programmers.

Importantly, though, it does no interpretation of the entities it
sees, it really only wants to figure out distinct code blocks through
matching parentheses and bundle them up into lists (of lists (...)).

Evaluator
---------

In the beginning, the evaluator looked at the lists of lists and
figured out some meaning from them.  Particularly the element in
functional position and what kind of an element it is.

For some forms it can apply some special treatment, for others it may
do some syntactic transformations (which may alter the meaning of the
expression!) before finally deciding to actually invoke some behaviour
and do something useful.

More advanced implementations might start performing some combinations
of:

* translation from :lname:`Scheme`-ish forms into intermediate
  representations

* code analysis and subsequent optimisation

* translation into pseudo-machine code for, commonly, a byte compiler.
  Home grown or more widely supported, eg. the JVM_.

* generation of a compilable external language, eg. :lname:`C` (and
  subsequent compilation)

* direct generation of host-specific machine code

Instances running pseudo-machine code in a byte compiler (in a
programming language *virtual machine*) might want to invest in a
:abbr:`JIT (Just In Time)` compilation system.

Syntactic Structure
===================

Forms
-----

Famously, :lname:`Scheme`, like all :lname:`Lisp`\ s, uses
s-expression_\ s and its basic syntactic structure is a *form* which
looks like:

.. parsed-literal::

   (*thing* *thing* *thing* ...)

Where each *thing* can be another *s-exp* or an *atom* which,
basically, is something that is not an *s-exp* (numbers, strings and
so on).

And... that's it.  There is some syntactic sugar for expressions that
are used a lot but, in essence, the syntactic structure of
:lname:`Scheme` is a list (of lists (of lists (of lists
(:socrates:`can you see what I'm doing, here?`)))).



That said, *technically*, *lists* don't exist in :lname:`Scheme`.
*Wait, what?* In truth, a *list*, such as ``(1 2 3)``, is syntactic
sugar for a chained series of :ref:`pair <pair>`\ s.  We'll get onto
that.

Atoms
-----

Atoms are those things that are not *s-exp*\ s meaning they're
numbers, strings and so on.  The likes of:

- booleans: ``#t`` and ``#f``

- numbers: ``-1``, ``23``, ``3.14`` etc.

  Let's take a moment to think about implementation.

  Numbers in the source code, like, ``-1`` and ``23``, should be
  looked as constructors for *values* representing the numbers -1
  and 23.

  That they are constructors should be obvious (or distracting or
  confusing) as we don't know what a *value* is in the memory of our
  :lname:`Scheme` instance.  They enter :lname:`Scheme` as a sequence
  of digits in the source code and emerge as a sequence of digits when
  printed out.  What happened in between?

  A number could be represented by a :lname:`C` ``int``, say (hint: it
  almost certainly isn't).  That doesn't tell us much about how big a
  number we can create (an 8, 16, 32, 64 or 128 bit integer?) and
  doesn't look like it'll hold a floating point number so something is
  going to have to make a decision on what *kind* of a number we are
  storing with the implication that there are going to be more than
  one.  Unless we only deal with (small) integers.

  .. sidebox:: If only the clouds would keep still!

  :lname:`Scheme` also handles "large" numbers in the form of
  *bignums*.  So, if you fancy counting all the atoms in the
  universe...

  So, all we can really say is that :lname:`Scheme` will consume the
  sequence of characters ``-`` and ``1`` or ``2`` and ``3`` or ``3``
  and ``.`` and ``1`` and ``4`` and construct a value in memory such
  that various arithmetic operations can be performed using it and
  that that value can be printed out.

- strings: ``"foo"`` etc. 

  Again, a constructor for a value in memory representing the
  characters in between the double quotes.

  What implementation here?  :lname:`C`-like ``NUL``-terminated
  strings?  UTF-8?  UTF-32?  We don't know and shouldn't care so long
  as :lname:`Scheme` allows us to manipulate them with the usual
  string functions.

- symbols: ``a``, ``foo``, ``user-name``, ``*ENV*``, ``arity+1`` etc. 

  Names, if you like, used as both identifiers (which are used to
  refer to values or, in the :lname:`Scheme` nomenclature, they are
  *bound* to the value) and as symbolic (hah!) flags.

  There is a little curiosity with symbols, they are unique across the
  program in the sense that when you use the symbol ``x`` in one
  function and the symbol ``x`` in another function then the *symbol*
  is the same.  There is only one symbol, ``x``, in the program.

  Clearly (hopefully!) they refer to different values as the functions
  are being evaluated but the symbol is the same.  This means that
  comparing symbols -- though the circumstances when you might do that
  might not be obvious right now -- is as fast as any equality can be
  in the underlying implementation.  In :lname:`C` that is going to be
  a pointer comparison.

  .. note:: Many punctuation characters are allowed in symbols which,
            depending on taste, allows for a more readable style.  I,
            for one, like a hyphen instead of an underscore.

	    :lname:`Scheme` is largely delimited by whitespace and
            parentheses which frees up a lot of characters to add
            meaning and colour to identifiers.

	    There's no hard and fast rules but there are conventions,
	    for example:

	    * a predicate will usually have a ``?`` character appended
              so :lname:`Scheme` might have a function ``number?``
              rather than ``isa-number`` (which itself is using
              punctuation, a hyphen, in its name).

	    * a memory-modifying function will usually have a ``!``
              character appended to make it clear you're up to no
              good: ``set!`` (for assignment) is the canonical
              example.

	    Of course, that means that statements like the shell's
	    assignment:

	    .. code-block:: bash

	       a=2

	    with no whitespace is a single symbol in :lname:`Scheme`.
	    If :lname:`Scheme` had infix notation then we would be
	    obliged to type:

	    .. code-block:: bash

	       a = 2

	    for an assignment.

	    Of course, the shell demands that there is *no* whitespace
	    in an assignment -- the very opposite!

There are other data types: chars, vectors etc. which we'll come to
when necessary.

.. _pair:

Pairs
-----

A *pair* is ``(1 . 2)`` or ``(a . b)`` etc..

A simple tuple of any two other objects -- including other pairs --
where the source code and printed output representation contains a
dot/period, hence the common name, a *dotted-pair*.

A pair can be constructed with ``cons`` (short for, uh, *construct*):

``(cons 1 2)`` results in ``(1 . 2)``.

``(cons 1 (cons 2 3))`` results in ``(1 . (2 . 3))``.

 
If the second element is another pair and the final element is (the
well-known symbol) ``nil``, eg. ``(1 . (2 . (3 . nil)))``, then the
source/printed representation can be reduced to a (more traditional
looking) list: ``(1 2 3)``.

This is such a common idiom that you can save some typing as the
constructor for a list, say, ``(cons 1 (cons 2 (cons 3 nil)))`` can be
simplified to ``(list 1 2 3)``.

.. sidebox:: This form isn't used often but does show up to handle
             arguments for a variable-arity function, for example.

If the final element is not ``nil`` then the collapsed format retains
the final dot and becomes an *improper* list: ``(1 . (2 . 3))``
becomes ``(1 2 . 3)``.

``(1 . nil)`` will be a list containing a single element: ``(1)``.

``()``, the empty list is equivalent to ``nil``, so ``(1 . ())`` is
also ``(1)``.

 

The first element of a pair can be retrieved with ``car`` (CAR means
*Contents of the Address part of the Register* from the IBM 704 that
:lname:`Lisp` was first developed on):

``(car (cons 1 2))`` results in ``1``.

``(car (list 1 2 3))`` also results in ``1``.

``(car (list (list 1 2) 3))`` results in ``(1 2)``.

 

The second element of a pair can be retrieved with ``cdr`` (*Contents
of the Decrement Register*):

``(cdr (cons 1 2))`` results in ``2``.  

.. note::

   The ``cdr`` of a list (not a pair) will be a list: 

   ``(cdr (list 1 2 3))``, results in ``(2 3)``

   or ``nil``:

   ``(cdr (list 1))`` results in ``nil`` (because ``(list 1)`` is
   really ``(cons 1 nil)``).

 
Of course either element of a pair can be a pair (or a list) which
allow us to build arbitrarily complex data structures, essentially,
lists of lists (of lists (...)).

``((1 . 2) . (3 . 4))`` is not the same as ``((1 2) . (3 4))`` as in
the latter case each of the sub-elements of the outermost pair is a
proper list whereas it is a simple dotted-pair in the first.

Delving into the depths of complex data structures then requires
liberal use of ``car`` and ``cdr`` for which the ever efficient folk
in :lname:`Scheme`-land have some shorthand: ``cadr`` is equivalent to
calling ``car`` on the result of calling ``cdr`` on some value.  Given
the symbol ``value`` bound to the data structure ``((1 2) . (3 4
5))``:

``(car value)`` results in ``(1 2)``

``(caar value)`` results in ``1``
   
``(cdar value)`` results in ``(2)``

``(cadar value)`` results in ``2``

``(cdr value)`` results in ``(3 4 5)``

``(cadr value)`` results in ``3``

``(cddr value)`` results in ``(4 5)``

``(caddr value)`` results in ``4``

Remember the ``cd*`` functions return a list if their argument is a
list, not the first element of that list even if it is the only thing
left -- of course, it isn't, there's a unwritten ``nil`` hiding at the
end -- hence you require an extra ``car`` to get the element itself.

Much of the interpretation of :lname:`Scheme` involves walking around
such list data structures, you'll be pleased to know.  Although when
you see how neatly a recursive implementation makes it happen you'll
nod sagely in appreciation.

Mental Model
^^^^^^^^^^^^

In the above description for *pair* I wrote:

``(cons 1 2)`` results in ``(1 . 2)``.

which is slightly disingenuous.  ``(cons 1 2)`` *results* in a value
in memory which, you can probably imagine, is going to be some data
structure that ultimately has two pointers off to other things, here,
things that represent the numbers 1 and 2.

``(1 . 2)`` is the *printed* form of that value but I think we are
happy enough to use it as our mental model of that value in memory
hence we can say that ``(cons 1 2)`` results in ``(1 . 2)``.  Much
like, however numbers are stored internally, we represent that
implementation in our heads as 1.

Homoiconicity Again
^^^^^^^^^^^^^^^^^^^

Back to ``(cons 1 2)``, that is *itself* a list, right?  It's got that

.. parsed-literal::

   (*thing* *thing* *thing* ...)

vibe going where the first value is the symbol ``cons``, the second
value is the number 1 and the third value is the number 2.

So, hang on.  I can get the symbol ``cons`` by calling ``car`` on that
list and the number 1 by calling ``cadr`` and...  *Whoa!* ...the
syntactic form of the language can be manipulated by the language
itself.

.. sidebox:: Wait, I think I can implement :lname:`Scheme` in 50 lines
             of :lname:`Scheme`!

That's what they mean by :term:`homoiconic <homoiconicity>`.



Etc.
----

Interestingly, :lname:`Scheme`, being quite old, is missing what many modern
languages have an expectation of being normal.  Hash tables, for
example, are not a default :lname:`Scheme` data type.  That leads many, if
not most, :lname:`Scheme` examples to work without them, which they do quite
well.

In the meanwhile, things like hash tables are nice to have so a suite
of "implemented in :lname:`Scheme`" examples have been created under
the banner of *Scheme Requests For Implementations*, aka. SRFI_\ s.

Evaluation Model
================

The evaluation model is equally simple: boolean, number and string
values evaluate to themselves, symbols evaluate to the value they are
bound to in memory and lists are treated as function calls where the
first element is the function to invoke (often a symbol, ie. by name)
and the remaining elements in the list are arguments to the function.

.. note:: *Everything* returns a value.

Some examples:

.. code-block:: scheme

   12

This will be interpreted as the constructor for a number value.
Evaluation of the constructor returns a number value.  Not much use as
it stands!

.. code-block:: scheme

   (number-add a 1)

A list.  The first element of the list is expected to be a function.
In this case it is the symbol ``number-add``.  Symbols, when evaluated
return the value they are *bound* (ie. refer) to.  

.. note:: In :lname:`Scheme` it is assumed that the value returned by a
          symbol in the first position of a list being evaluated is a
          function, no particular type checking is done while the
          symbol is evaluated!  Obviously, when :lname:`Scheme` tries to
          apply the function to the arguments then it will quickly
          discover whether the value is a function or not.

The remaining elements are the arguments to the function, in this case
another symbol, ``a``, and ``1``, a number (constructor).  For these,
the symbol will be evaluated and the bound value returned and the
number will be constructed and the value returned.

Finally, the function value (the result of evaluating ``number-add``
to get its bound value) will be applied to the argument values
(whatever the value was that ``a`` was bound to and the number value
of ``1``).  Which is a slightly roundabout way of saying we're going
to add 1 to the value being referenced by ``a``.

Except that it isn't particularly roundabout.  We've made assumption
after assumption about how things work, or rather, you've just
followed what been's said and accepted it as true.  What happens if
``number-add`` is not a function, ``a`` is not a number,
``number-add`` doesn't take two arguments let alone two numbers,
``number-add`` (or ``a`` for that matter) is not defined anywhere (and
whether we have any rights to know about it if it has been defined
elsewhere)?  Should we have evaluated the arguments before calling the
function?  Should we have evaluated the element in the functional
position before or after the arguments?  Should we have evaluated the
arguments left to right, vice versa or in parallel (if we could)?

Does any of that lot matter?  Yes, of course.  If a language is not
well defined then implementers are at liberty to make decisions which
means users will see different behaviour if they run their programs
using different implementations.  Evaluating arguments left to right
(or vice versa) may have different side-effects and make or break the
user's program.  Not good.

That said, ``number-add`` is not a standard function, ``+`` is:

.. code-block:: scheme

   (+ a 1)

Now, a famous bane of :lname:`Scheme` is that the function is *always*
the first element of the list -- there are no infix or postfix
operators.  We are very used to seeing arithmetic written with infix
operators, ie. ``a + 1``, and, for many people, there is a natural
cognitive pause when reading prefix notation for arithmetic (and
assignment).

But that's bizarre, every other function call we make in the vast
majority of programming languages uses prefix notation:

.. code-block:: c
   :caption: C

   number_add (a, 1);

.. code-block:: perl
   :caption: Perl

   number_add ($a, 1);

.. code-block:: tcl
   :caption: Tcl

   [number_add $a 1]

.. code-block:: scheme
   :caption: Scheme

   (number-add a 1)

We don't skip a beat when reading those yet have a mental hiccup with
regular arithmetic functions in prefix notation:

.. code-block:: scheme

   (+ a 1)

There's no particular answer to that.  Other than to enable infix
notation -- which is messy in :lname:`Scheme` and so *Lisp* language
programmers just get used to prefix notation of arithmetic.

As an aside, prefix notation has a benefit in that ``+`` isn't limited
to 2 arguments: ``(+ 1 2 3 4 5)`` is just fine.  As, indeed, is ``(+
1)``.

.. rst-class:: center

---

Extending our trivial example, now a list of lists:

.. code-block:: scheme

   (+ 1 (* 2 3))
		
Aha!  We've got this.  The outer list is really ``(+ 1 X)`` where
``X`` is the result of evaluating the inner list, the expression ``(*
2 3)``, so we would expect that ``+`` will we called with the
arguments ``1`` and ``6``.  Easy.

Indeed, so.  Notice that there was no arithmetic precedence rules,
eg. ``1 + 2 * 3``, we had to explicitly state the multiplication
expression.  In fact, we have to explicitly delimit every expression
in :lname:`Scheme` -- there are no shortcuts!  This leads to another bane of
:lname:`Scheme`, parentheses overload, there's a lot of them floating about.
That said, if you took away arithmetic precedence and used regular
prefix function calls, every other language would look similar:

.. code-block:: c

   add (1, mul (2, 3))

which, if you remove commas:

.. code-block:: c

   add (1 mul (2 3))

and pull the function names inside the parentheses:

.. code-block:: scheme

   (add 1 (mul 2 3))

and replace arithmetic function names with symbols:

.. code-block:: scheme

   (+ 1 (* 2 3))

then we're back to :lname:`Scheme` -- we've only changed the syntactic sugar,
not the substance of the expression.  Arithmetic precedence rules and
infix operators, that's really the only difference.

Incidentally, given that everything is going to be wrapped in
parentheses and that we're going to have lists of lists of lists as we
delimit every expression, :lname:`Scheme` calls these lists of lists (of
lists ...) *forms*.

Special Forms
-------------

Wait, though, there some special cases where we can't just perform
evaluation like the above.  ``if`` is a case in point:

.. code-block:: scheme

   (if #t (carry-on) (sleep-forever))

The ``if`` form takes three arguments: a *condition* expression which
should result in a boolean value, a *consequent* expression to be
evaluated if the boolean result was true and an *alternate* expression
to be evaluated if the boolean expression was false.

Notice the careful wording there: to be evaluated *if*.... ``if``
cannot have had its arguments evaluated before it is applied to the
arguments otherwise we would have tried evaluating ``(sleep-forever)``
(and the other arguments) to find out their values.  We might surmise
that ``(sleep-forever)`` is going to take a while to complete and
since the *condition* was ``#t`` then logically we shouldn't have been
running it anyway.

So ``if`` must be being treated specially and indeed it is called a
*special form*.  Special forms do not have their arguments evaluated
before the function value is applied to the arguments.

To handle this, the evaluation engine will have compared the ``car``
of the form to the symbol ``if`` and if it matches then starts to run
the behaviour of the special form.  The arguments remain unevaluated
and are passed as is (atoms or lists) to the ``if`` behaviour code.

OK, let's think this through.  Inside the function that implements
``if`` there must be something that evaluates the *condition*
expression and then if the result was true then evaluates the
*consequent* expression otherwise evaluates the *alternate*
expression.  Who implements this ``if`` inside ``if``?

Well, here we get into the murky meta world of language implementation
and the implementing language.  In the pedagogical examples of SICP
(:cite:`SICP`) and LiSP (:cite:`LiSP`), the implementation of ``if``
(the ``if`` of our proto-:lname:`Scheme`, :lname:`Scheme`\ :sub:`0`,
say) will be written in some existing :lname:`Scheme`,
:lname:`Scheme`\ :sub:`1`, say.

.. sidebox:: :lname:`Scheme`\ :sub:`2`, of course.  :socrates:`And
             it?` Why, it's :lname:`Scheme`\ s all the way down.

OK, so what is :lname:`Scheme`\ :sub:`1`’s ``if`` written in?  Well,
you'll have to go and look at the source code but you can imagine that
you'll eventually find an implementation of :lname:`Scheme`\ :sub:`n`
in :lname:`C` and therefore ``if`` will have been implemented using
:lname:`C`’s ``if``.  :lname:`C`’s ``if`` is, in turn, (probably)
implemented with a machine code instruction to test and branch, itself
written in processor microcode and eventually into transistor NAND
gates where, um, ...  *Look!* A squirrel!

In the meanwhile, glossing over the detail, most functions are
*derived* forms and their arguments are evaluated before the function
value is applied to them but some *names* (in function position) are
identified as special and the behaviour code is given the arguments as
is.

The term *derived* is from that idea that there are a few *core*
forms, usually special forms, from which everything else can
be... derived.  We'll also have the distinction between *primitive*
and (I don't think there is a special name for them so let's use)
regular functions.  A regular function is one we write in
:lname:`Scheme`.  A primitive function is one written in the
underlying implementation language, say, :lname:`C`, whose interface
is exposed such that it can be invoked as if it were a regular
function.

You create primitive functions as a combination of:

* elementary memory management functions -- think of ``cons`` to
  create some, say, :lname:`C` structure on the heap, and ``car`` and
  ``cdr`` to poke about in it

* bootstrap functions -- you might want a simple ``map`` function
  before it can be re-written into all of its glory

* plain old expediency and efficiency functions -- some things just
  want a fast, tight loop.

.. sidebox:: Local forms, for local people!

Special forms sounds great for system-defined functions and people who
want to hack away at the source code but what if **I** want one?
Well, in many languages you're clean out of luck.  Want to add a new
syntax operator alongside ``if``, ``while`` etc. to :lname:`C`?
That's not going to happen.  However, the folks in
:lname:`Scheme`-land are more generous and have blessed us with
*macros*.

And arguably cursed us with macros.  A double-edged sword.

Bindings
--------

How do we bind symbols to values?  We had ``(+ a 1)`` before.  What is
``a`` referring to, how did ``a`` get bound to a value?

There are a number of *binding forms*.

.. _let:

let
^^^

.. parsed-literal::

   (let *bindings* *body+*)

where ``bindings`` is a list of bindings and each binding is a list of
a symbol and an expression and ``body+`` is one or more forms (hence
the ``+`` in ``body+``) to be evaluated in the context of the
bindings.

Visually, ``bindings`` is potentially confusing.  If we go over that a
step at a time:

#. ``bindings`` is a *list* of bindings:

   .. parsed-literal::

      (let (*binding1* *binding2* *binding3*) *body+*)

   although your more likely to see it written (and write it) as:

   .. parsed-literal::

      (let (*binding1*
            *binding2*
	    *binding3*)
	*body+*)

#. each binding is a *list* of a symbol and an expression:

   .. parsed-literal::

      (let ((a 2)
            (b 1)
	    (c (* 3 4)))
	*body+*)

For each binding, the expression is evaluated and the symbol is bound
to the resultant value then the remaining ``body+`` forms are
evaluated in sequence with the symbols available for use.

After the ``body+`` forms have been evaluated then the symbols are no
longer available -- in other words, the *extent* of the symbols is
limited to the lifetime of ``body+``.

The result of the ``let`` form is the value of the last form in the
``body+`` forms.

.. code-block:: scheme

   (let ((a 2))
     (+ a 1))

Here, ``bindings`` is ``((a 2))``, ie. a list of a single binding,
``(a 2)``, and the ``body+`` forms is just a single form, ``(+ a 1)``.

For our single binding, ``(a 2)``, recall that it is a list of a
symbol and an expression.  Here, the symbol is ``a``, the ``car``, and
the expression is ``2``, the ``cadr``.  The expression, ``2``, a
number constructor, is evaluated resulting in a number value and ``a``
is *bound* to that value.

If any of the forms in ``body+`` requires the evaluation of the symbol
``a`` then the result will be the number value 2.

Of course, we *do* want to use ``a`` in ``body+`` where the expression
``(+ a 1)`` can now have its arguments successfully evaluated
resulting in ``(+ 2 1)``.

The function name, ``+``, can be looked up and (we presume) results in
a function value that will add two numbers together for us.  The
result of applying the function value of ``+`` to the argument values
*1* and *2* should be a number value (representing 3) and as it is the
only form in ``body+`` then it is also the last and therefore the
result of ``let`` itself.

Wait a minute, ``let`` returns a value?  Yes, as noted earlier,
*everything* returns a value (albeit that some of them are
*unspecified*).  In fact, that ``let`` returns a value is used
innumerable times to create closures.  More of that later.

A fractionally more complex example:

.. code-block:: scheme

   (let ((a 1)
	 (b 2))
     (+ a b)
     (- a b))

we've now bound two symbols, ``a`` and ``b``, to two numbers, ``1``
and ``2`` and we have two forms in ``body+``.  The first form adds the
two numbers together and returns that result.

Wait, returns it to whom?  Well, we did say that the ``body+`` forms
were going to be evaluated in sequence which means there must be some
entity iterating over each form and it is to that entity that we've
returned the number value.

:lname:`Scheme` has been a little underhand here and rewrites forms
from time to time.  For a ``let``, the ``body+`` is re-written to
``(begin body+)`` where the sequencing function, ``begin`` will
iterate through the individual forms in ``body+`` discarding all
results except the last which it returns as its own result.

This means the original multiple-body form variant of ``let`` with
``body+`` has been transformed into a pure single body form: ``(let
bindings body)``.  This sort of transformation (from an impure to a
pure(r) format) is at the heart of syntactic transformations,
aka. macros.

So :lname:`Scheme` re-wrote our little snippet of code to:

.. code-block:: scheme

   (let ((a 1)
	 (b 2))
     (begin
      (+ a b)
      (- a b)))

and ``begin`` has consumed the result of the addition and will now
evaluate the next form, a subtraction.  This is the last (original)
``body+`` form and so the result of the subtraction, the number value
-1, becomes the result of the ``begin`` function -- everything returns
a value, remember -- and as the ``begin`` function has inserted itself
as the only and therefore last body form of ``let``, it will be the
result of the ``let`` too.

Lexical Scope
"""""""""""""

Let's get busy:

.. code-block:: scheme

   (let ((a 1))
     (let ((b 2))
	a))

has an outer ``let`` binding ``a`` to 1 and its body is another
``let``.

This inner ``let`` binds ``b`` to 2 and evaluates its body which is
the simple symbol, ``a``.  The extent of the outer ``let``'s binding
is still valid -- we're still in the outer ``let``'s body -- so ``a``
is bound to 1.  The inner ``let`` has finished processing its body
which has returned a value, 1, which it returns itself.

The inner ``let``'s body has now returned a value and as it was the
only body form so the outer ``let`` also returns 1.

Some visual gymnastics, now.

.. code-block:: scheme

   (let ((a 1))
     (let ((a 2))
	a))

has an outer ``let`` binding ``a`` to 1 and its body is another
``let``.

This inner ``let`` binds a *new* ``a`` to 2 and evaluates its body
which is the simple symbol, ``a``.  In this inner ``let`` ``a`` is 2
-- it is the first ``a`` found when walking outwards across lexical
bindings.  The inner ``let`` has a value, 2, from its body which it
returns.

The inner ``let``'s body has now returned a value and so the outer
``let`` also returns 2.

What if the outer ``let``'s body did a bit more?

.. code-block:: scheme

   (let ((a 1))
     (let ((a 2))
	a)
     a)

The inner ``let`` continues to create a new ``a`` bound to the number
value 2 and returns it.  However, the inner ``let`` is the first of
two body forms in the outer ``let`` and therefore its result is
ignored by the implicit ``begin``.  All of the bindings of the inner
``let`` are now irrelevant and when ``begin`` evaluates the final
form, ``a`` the only binding for ``a`` in scope is that of the outer
``let`` meaning ``a`` evaluates to 1.

``let`` has its limits, though, for a very specific reason:

.. code-block:: scheme

   (let ((a 1)
	 (b (+ a 1)))
     (+ a b))

This seems reasonable enough, ``a`` is bound to the number ``1``
and ``b`` is going to be the result of adding ``1`` to ``a``.  

Except it is an error.  ``let`` won't allow you to use a symbol being
defined in the bindings in the expression used to bind another symbol.
We'll see why in the advanced section.

Functions
---------

Function *definitions* are likely to look something like a list of
formal parameters and a body.  The formal parameters are bound to the
values of some expressions passed as arguments when the function is
called and the formal arguments are available for use for the lifetime
of the body.  It's sounding quite similar to the :ref:`let`, above.

Functions are first-class values in :lname:`Scheme`, this is to say
you can pass them around like numbers or strings.  All you have to do
to use a function value is to put it in the first slot of a form.

In :lname:`Scheme` function *values* are created with the special form
``lambda`` (which you might think of as a ``function`` keyword):

.. parsed-literal::

   (lambda *formals* *body+*)

Where ``formals`` is a list of formal parameters (possibly the empty
list!) followed by a list of one or more body forms, evaluated in
sequence -- sounds familiar again! Hence we might expect a similar
syntactic transformation to a more pure form:

.. parsed-literal::

   (lambda *formals* (begin *body+*))

Hmm, notice we haven't given the function a *name*.  What we have is a
function constructor -- like the constructors for numbers and strings
-- the result of which is a function value.  Unless we bind it to a
variable we're going to lose it.

Noting that it is without a name this might be called an *anonymous
function* -- though that's not a term you particularly see in
:lname:`Lisp` languages as it's just a function (value).

let* and letrec
---------------

The pedantry in defining things continues with a couple of variations
on a theme!

.. code-block:: scheme

   (let* ((a 1)
	  (b (+ a 1)))
     (+ a b))

Finally, we can have variables dependent on previous ones!

But what's happening here?  ``let*``, "let iteratively", iterates over
the bindings, one at a time, placing each parameter in the scope of
later ones.  It has transformed:

.. parsed-literal::

   (let* ((*formal1* *arg1*)
	  (*formal2* *arg2*))
     *body+*)

into:

.. parsed-literal::

   (let ((*formal1* *arg1*))
     (let ((*formal2* *arg2*))
       *body+*))

Where each ``let`` only handles a single binding and the remaining
bindings are performed in the body form of that binding, hence the
earlier parameters are available for use in subsequent argument
expressions.

``letrec``, "let recursively," is a slightly different idea, it
handles the situation where two or more function definitions are
mutually dependent.  The usual example is these rather inefficient
``odd?``/``even?`` predicates:

.. code-block:: scheme

   (letrec ((odd? (lambda (n) (if (= n 0)
				  #f
				  (even? (- n 1)))))
	    (even? (lambda (n) (if (= n 0)
				   #t
				   (odd? (- n 1))))))
     (even? 4))

Here, each predicate will call the definition of the other, so who do
we define first?  Does it matter, though, as these are function
definitions and not invocations?

Yes, it does, as the interpreter, when it is analysing the function
definition for ``odd?`` will see a reference to ``even?``.  It now has
to look that up.  In the best case there isn't an ``even?`` in scope
and you get a error.  In the worse case it'll find some dubious
binding to ``even?`` hanging about and good luck to everyone when it
gets called.  Clearly these two definitions are meant to go together
-- they are :term:`concomitant`.

``letrec`` performs a little trick, rather than define one before the
other, it creates placeholder bindings for the symbols and then
redefines the values in the placeholders in turn to their proper
definition -- it doesn't matter in which order, now, as references to
``even?``/``odd?`` will find either the proper definition or the
placeholder (to be filled in with the definition in a moment's time).
As whichever is found will be the locally defined placeholder
``even?``/``odd?`` then we won't be unearthing some dubious code from
elsewhere.  So ``letrec`` might be transformed from:

.. parsed-literal::

   (letrec ((*formal1* *arg1*)
	    (*formal2* *arg2*))
     *body+*)

into:

.. parsed-literal::

   (let ((*formal1* #<undefined>)
	 (*formal2* #<undefined>))
       (let ((tmp1 *arg1*)
	     (tmp2 *arg2*))
	  (set! *formal1* tmp1)
	  (set! *formal2* tmp2)
	  *body+*))

which itself introduces a few issues: the idea of an *undefined* value
(perhaps an internal implementation thing?); temporary variables (we
don't want to conflict with the user's code); and ``set!``, the
destroyer of things!

Define
------

With the various forms of ``let`` we can introduce new variables and
override them but sometimes, to much gnashing of teeth from the
purists, we need to change the value a symbol is bound to.  By and
large in :lname:`Scheme`, where something is going to change something
then its name has an exclamation mark at the end signifying the danger
of mutation!

In our putative transformation of ``letrec``, above, we use ``set!``
to modify the values that the formal parameters were bound to.  That's
fine inside the ``let`` that introduces those formal parameters but
what do we do at the top level (outside of any binding form) or
anywhere else where a symbol has not yet been introduced?

.. code-block:: scheme

   (set! a 1)

is an error in :lname:`Scheme` as ``a`` does not exist -- we can't change the
value a symbol is bound to if the symbol doesn't have a binding yet.
This may appear as another bout of pedantry as ``set!`` could create
the binding if it didn't already exist.  

You might well ask, then, *where* ``set!`` should create the binding.
In the current scope (``let``/``lambda`` level)?  At the top level
(whatever that is)?

Whilst we ponder the possibilities, :lname:`Scheme` says that you should use
``define`` to introduce a symbol binding at the current level -- a
binding you can subsequently ``set!``.

.. code-block:: scheme

   (define a 1)

Introduces the binding of the symbol ``a`` to the number ``1`` after
which anything can use it:

.. code-block:: scheme

   (let ((b 2))
     (+ a b))

should return the number value 3 even though ``a`` was not introduced
by the ``let``, the ``define`` at the top level has meant it is in
scope.

We could have written:

.. code-block:: scheme

   (let ((b 2))
     (define c 3)
     (+ b c))

which would return the number value 5.  The ``define``, here, *inside*
the ``let`` seems slightly wasteful -- as you could have simply had
``let`` introduced a new binding for ``c`` itself -- however the
technique is used frequently for defining ancillary functions within
another function.

Yes, of course, functions within functions.  What's not to like?

Defining Functions
------------------

Associating a name with a function value -- we know how to create
function *value* with ``lambda`` and we now have ``define`` so it is
obviously:

.. code-block:: scheme

   (define +1 (lambda (n) (+ 1 n)))

(a function called ``+1``?  *Outrageous!*)

This is such a common idiom that ``define`` has an alternate syntax:

.. parsed-literal::

   (define (*name* *formals*) *body+*)

to be re-arranged as:

.. parsed-literal::

   (define *name* (lambda (*formals*) *body+*))

ie. for our ``+1`` function:

.. code-block:: scheme

   (define (+1 n) (+ 1 n))

or

.. code-block:: scheme

   (define (+1 n)
    (+ 1 n))

That's a bit cleaner!

Notice that ``define`` (without an exclamation mark) is *introducing a
new* binding whereas ``set!`` is *modifying an existing* one (hence
``define`` and ``let`` rather than ``define!`` and ``let!``).

It's not quite that simple as the number of formal arguments cause a
twist.

No Arguments
^^^^^^^^^^^^

For the ``define`` form that's easy, just don't specify any when you
define the function -- and obviously don't pass any when you call it!

.. code-block:: scheme

   (define (hi-string)
    "hi!")

   (hi-string)

For the ``lambda`` form it's not dissimilar, we just have an empty
list:

.. code-block:: scheme

   (lambda nil "hi!")

although you must explicitly write ``nil`` otherwise the evaluator
will be left with an incoherent set of arguments for ``lambda``, just
a string in this case.

Varargs
^^^^^^^

What if you have a variable number of arguments?  Remember, improper
lists, ``(a b . c)``?  There's two variants here:

Some Formal Parameters
""""""""""""""""""""""

.. code-block:: scheme

   (define (foo a b . c)
    ...)

I must call ``foo`` with at least two arguments, for the formal
parameters, ``a`` and ``b``, and any remaining arguments are bundled
up into a list and bound to ``c``.

``c`` could be an empty list, ``nil``, or a list of one or more
values, ``(...)``.

No Formal Parameters
""""""""""""""""""""

Here, *all* arguments are bundled up into a list and passed as the
formal parameter.

For define, this is OK:

.. code-block:: scheme

   (define (foo . c)
    ...)

and works like above.  In fact the function ``list`` itself -- whose
purpose is to bundle up its arguments into a list -- is usually rather
cheekily defined as:

.. code-block:: scheme

   (define (list . ls)
    ls)

where it has had the evaluator do the hard word of bundling the
arguments into a list and passes it off as its own work.  Clever.

For the ``lambda`` form it is visually different:

.. code-block:: scheme

   (lambda c
    ...)

where ``c`` is now a standalone symbol, not in a list of formal
parameters, to capture all the arguments as a list.

Closures
--------

All functions are closures_, that is they can use variables in scope
in their bodies.  That's probably not a huge shock until you note that
a lot of the time a function is returned from an expression and will
continue to be able to use the variables that were in the lexical
scope of it's *definition* from far far away.

.. code-block:: scheme

   (define a 1)

   (define (a+ n) 
     (+ a n))

   (a+ 5)

You'll expect to get the number value 6 -- which you do.  However,
there's a couple of variations on a theme here:

.. code-block:: scheme

   (set! a 2)
   (a+ 5)

will result in the number value 7 but

.. code-block:: scheme

   (let ((a 3)) 
     (a+ 5))

will give you the number value 7 again.  Why?

We're back to bindings.  When the interpreter analysed the definition
of ``a+`` it saw that the variable ``a`` was not bound by the
parameters of the function (nor by any bindings introduced within its
body) and was therefore a *free identifier*.

Rummaging about it will have found the top level ``a``, introduced by
``define``, and will have used that binding in the implementation of
``a+``. Even though the binding was modified by ``set!`` the function
body would still be referring to that binding irrespective of any
subsequently introduced bindings.

In the terminology, ``a+`` was *closed over* ``a`` and therefore
``a+`` is a *closure*.

What if we wanted to use the locally current binding of ``a`` (to the
number value 3) at the time we evaluated the function call?  That
would then be using *dynamic scope*.  :lname:`Scheme` does use dynamic scope
but prefers *lexical scope* in the definition of functions.  It could
have chosen to do differently but it didn't.

The shell, on the other hand, is quite the reverse.  Dynamic scope is
used unless a variable is declared with lexical scope (with
``typeset``).

.. _quoting:

Quoting
^^^^^^^

There's a few *reader macros* to help us.  Reader macros aren't true
macros we will describe later but rather allow for some cheap
syntactic tricks to save typing.

If the evaluation engine sees a list it will assume the first element
is a function and the remaining elements are arguments to that
function.  What if we want to create an actual list and not have it
evaluated?  We need to *quote* the list:

.. code-block:: scheme

   (quote (1 2 3))

``quote`` stops the evaluation engine from trying to find a function
associated with the number constructor ``1``.  Typing ``(quote
thing)`` gets tiresome so we can use a single quote, ie. ``'thing`` as
shorthand:

.. code-block:: scheme

   '(1 2 3)

The reader macro associated with ``'`` will read the next expression,
``thing``, say, and return the longwinded ``(quote thing)`` for the
evaluation engine to process.

Types
-----

Values have types (boolean, number, string etc.) in :lname:`Scheme` but
identifiers do not.  You can freely rebind a symbol to any value --
though you're only likely to confuse yourself.

This contrasts with strongly-typed languages where a type is
associated with an identifier:

.. code-block:: c

   int i = 3;

so that the compiler can keep track of things and call out any obvious
errors:

.. code-block:: c

   char *s = strlen (i);

Common :lname:`Scheme` Functions
--------------------------------

Equivalence Predicates
^^^^^^^^^^^^^^^^^^^^^^

What does "the same" really mean?

``eq?`` is most exacting in that, where appropriate, the comparison is
on the (internal) pointer into memory where the value is stored.  A
pointer test can be very quick.

This leads to the slightly odd:

.. code-block:: scheme

   (eq? 1 1)

returning ``#f``.

``eqv?`` is the same as ``eq?`` except that the values of numbers and
chars are compared.  :socrates:`Thank goodness for that!`

``equal?`` will recursively descend into pairs, vectors and strings
applying ``eqv?`` to their contents.  Broadly, does the printed
representation look the same?

:lname:`C`, by way of comparison, can only perform integer
comparisons, ``==``, ``<`` and the like.  Any complex data type like a
string or a struct requires that you delve inside and compare the
constituent parts "int by int".

Conditional Expressions
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: scheme

   (if c1 s1
       (if c2 s2
	   (if c3 s3
	       ...)))

Cascading ``if`` clauses aren't easy on the eye.  ``cond`` is the
alternative:

.. code-block:: scheme

   (cond
     (c1 s1+)
     (c2 s2+)
     (c3 s3+))

where, more than likely, each of the ``cX`` and ``sX+`` clauses are
themselves lists:

.. code-block:: scheme

   (cond
     ((boolean? exp)	"boolean")
     ((number? exp)	"number")
     ((string? exp)	(string-append "string-" exp)))

``cond`` is slightly different to ``if`` in that multiple expressions,
the ``sX+``, are allowed if the condition is true.

It has an ``else`` form, of course, and a very different creature, an
``=>`` clause:

.. code-block:: scheme

   (cond
     ((string-match str "foo")	=> func)
     (else			(string-append "string-" exp)))

.. sidebox:: My example is rather poor in that you might presume that
             ``string-match`` produces an index into a string but,
             seemingly, ``func`` has no reference to ``str``.  Maybe
             ``func`` was closed over ``str``, maybe it's just
             accumulating a list of matches, maybe I should think
             harder about my examples....

For ``=>`` the ``cX`` expression is evaluated resulting in some
:samp:`{value}`.  If the :samp:`{value}` is not false then ``func`` is
applied to the :samp:`{value}`, ie.  :samp:`(func {value})`, or
``(func (string-match str "foo"))`` if and only if ``(string-match str
"foo")`` is not false.

``case`` is more like :lname:`C`’s ``switch`` or the shell's ``case``
statements:

.. code-block:: scheme

   (case key 
     ((o1+)	e1+)
     ((o2+)	e2+)
     ((o3+)	e3+))

where ``key`` is evaluated and then compared to each of the ``on+``
objects with ``eqv?``.  If any object matches ``key`` then the
expressions ``en+`` are evaluated in sequence with the result being
that of the last expression.

Sequences
^^^^^^^^^

``and``, ``or`` and ``begin`` are all logical sequencing instructions
which only differ in their initial premise (``#t``, ``#f`` and
*unspecified* respectively) and when they stop processing the sequence
(when an expression returns false, when an expression returns true and
to the end, respectively).  They all return the value the last
expression they evaluated returned (or the initial premise if there
were no expressions!).

Common :lname:`Scheme` Idioms
-----------------------------

Result List
^^^^^^^^^^^

A very common idiom is for a function to construct a result list by
``cons``\ ing together the putative calculation on the ``car`` of the
list of arguments and then calling itself on the remaining arguments.
So to add 1 to every element of a list:

.. code-block:: scheme

   (define (inc-list lis)
     (cons (+ (car lis) 1)
	   (inc-list (cdr lis))))

Here we are ``cons``\ ing together the per-element calculation ``(+ X
1)`` where ``X`` is the first element of the list and a recursive call
to itself on the rest of the list, ``(inc-list (cdr lis))``.

Calling the argument list ``lis`` is a common enough idiom itself as
calling the argument list ``list`` would conflict with the function
``list`` and calling it ``l`` as ever risks visual confusion with
``1``.

Actually, that's not quite correct as there's nothing identifying the
end of the list!

.. code-block:: scheme

   (define (inc-list lis)
     (if (pair? lis)
	 (cons (+ (car lis) 1)
	       (inc-list (cdr lis))))
	 nil)

When we reach the last pair in the list, where the ``cdr`` is ``nil``
and call ``inc-list`` on that ``nil`` then the ``if``’s condition is
false and that invocation of ``inc-list`` returns ``nil`` which is
just what we want in the caller's ``cons``, ``(cons thing nil)``.  As
the recursive calls unwind we get a neatly constructed set of nested
``cons`` calls resulting in the list we want.

Indeed, applying a function to each element of a list is the work of
``map``:

.. parsed-literal::

   (map *func* *list*)

and in our "add 1" case, an anonymous function is suitable:

.. code-block:: scheme

   (map (lambda (n) (+ n 1))
	list)

``map`` itself will follow the result list idiom -- constructing the
result list as the list is descended.

That's similar to ``map`` in most languages but :lname:`Lisp`\ ers
like a list so the real ``map`` will iterate down multiple lists at
once calling ``func`` with multiple args (one per list).

Safe Bootstrap
^^^^^^^^^^^^^^

Particularly in bootstrap code you might see the peculiar:

.. code-block:: scheme

   (define (foo args) ...)

   (define bar
     (let ((foo foo))
       (lambda (args)
	       ...use foo...
	       )))

What's the point of defining ``foo`` as ``foo`` in the ``let`` in
``bar``?

The problem is that we don't know when ``bar`` is going to be called
and, if ``foo`` is something that may be redefined with slightly
different behaviour then we need to be sure that the ``foo`` that
``bar`` uses is this one, the one defined immediately before it.  In
other words, we've bound ourselves to the local definition of ``foo``
so that we don't get any unexpected behaviour.

Anonymous Closures
^^^^^^^^^^^^^^^^^^

Anonymous closures returned from function calls are very common:

.. code-block:: scheme

   (define (adder-factory arg)
     (lambda (a)
       (+ arg a)))

   (define add3 (adder-factory 3))
   (add3 5)

should get us the number 8 as a result.

.. _thunk:

Thunks
^^^^^^

A thunk is a zero parameter function which doesn't sound much use in
itself but following on from anonymous closures is a useful trick to
delay the evaluation of some code.

.. code-block:: scheme

   (define a (+ 3 5))
   (+ a 1)

will perform the calculation ``(+ 3 5)`` and bind ``a`` to the result.
No biggie.  But:

.. code-block:: scheme

   (define a (lambda () (+ 3 5)))
   (+ (a) 1)

Notice that ``a`` is a now a zero-argument function and therefore
requires a zero-argument function invocation, ``(a)``, in the final
expression!

Here, the calculation, ``(+ 3 5)``, will only be performed when ``a``
is invoked as a function.  

This is a trivial case but preparing a body of code to be evaluated on
demand will come in very useful.

Recall, that ``if`` is a special form, ``(if condition consequent
alternative)``?  Perhaps we could have transformed it into

.. parsed-literal::

   (if *condition* *consequent-thunk* *alternative-thunk*)

by replacing, say, ``consequent`` with ``(lambda () consequent)``,
then neither of the consequent nor alternative expressions would be
evaluated until their respective thunks were invoked when ``if``
decided what to do with the result of condition.

OK, using a macro to skip the special form-ness of ``if`` seems a bit
pointless but the principle remains:

.. code-block:: scheme

   (define (preparer args)
     (lambda () 
	... args ...
	))

we can prepare some functionality to be evaluated on demand -- perhaps
never, of course.


.. include:: ../commit.rst

