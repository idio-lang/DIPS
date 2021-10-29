.. include:: ../../global.rst

**********
Evaluating
**********

The evaluator is how we find meaning in the source code.

Knowing that the reader has supplied us with lists of lists then it
shouldn't come as huge surprise that the evaluator is quite recursive
in its nature but is relatively straightforward all the same.

There are plenty of complications, of course, for example there are
several situations where the source code is normalised by re-writing
it.

This normalisation is a form of implicit syntax transformation (as in,
the :lname:`Idio` language makes the transformation according to its
built-in rules, which we're about to discuss).  The use of syntax
expanders (via templates aka macros) allows users to make explicit
syntax transformations.

Context
=======

We're not deviating a great deal from the technique outlined in
:ref-title:`LiSP` (:cite:`LiSP`) based on which our search for meaning
is going to involve a few basic repeating variables:

* ``e`` -- the expression we're currently evaluating (not a huge
  surprise)

  As we recursively evaluate the elements of a list, say, then the
  expression to be evaluated will become the, say, head of the list.
  When the evaluation recursion unwinds, the expression "to hand" will
  revert as expected.

  We'll likely have ``eh`` and ``et`` as the head and tail of a
  pair/list and further derivatives.

* ``src`` -- an :lname:`Idio` addition is to maintain the original
  source expression in order that we can pass on any source code
  properties (namely the lexical object defined by the reader) to any
  derived expression we might generate

* ``nametree`` -- a "name tree"

  As we walk through the lists of lists and determine that new
  *lexical* variables are introduced then they push in front of
  previous lexical variables giving us a hierarchy of known names.
  This name tree is then available for us to check down when a
  variable is referenced.

  As the lists of lists recursion unwinds then the nametree unwinds
  with it.

  It is a list of lists where the inner lists are of the variables
  introduced by a given variable-introducing statement.

  A name tree is slightly more obvious in :lname:`Scheme` where
  multiple variables can be introduced in a single ``let`` (or
  variant) statement but the effect is still true in :lname:`Idio`
  where an assignment operator introduces variables one ``let*`` at a
  time.

  .. code-block:: idio

     {
       a := 1

       ;; nametree ~ ((a))

       ;; => a is first list, first slot ~> SHALLOW-ARGUMENT-REF0

       b := 2

       ;; nametree ~ ((b) (a))

       ;; => a is second list, first slot ~> DEEP-ARGUMENT-REF 1 0

     }

  Hmm, not the most clear example but our list of names in the name
  tree has:

  * after the first variable assignment a variable ``a`` in scope

  * after the second variable assignment it then has a ``b`` in scope
    and then the ``a``, now a level out

  The reason this is important goes back to the :ref-title:`LiSP`
  mechanism for accessing lexical variables through a linked list of
  *frames*.  The opcodes go one level back,
  :samp:`SHALLOW-ARGUMENT-REF{n}`, or multiple levels back,
  :samp:`DEEP-ARGUMENT-REF {d} {n}` (for some depth :samp:`{d}` and
  index within the frame :samp:`{i}`).

  The nested frame mechanism is required because when we call a
  closure we'll create a frame here for the arguments to go into
  *then* invoke the closure.  The first thing the closure mechanism
  does is reset the frame hierarchy to that which the closure had when
  it was created.  The frame we just created is linked into that
  "historic" frame hierarchy and the closure runs.

  From the closure's perspective, it sees the arguments to itself in
  front of the original set of lexical variables when the closure was
  created.

  ``let`` is still legal syntax so we can make it a bit more
  obvious:

  .. code-block:: idio

     {
       let ((a 1)
            (b 2)
	    (c 3)) {
	    
       ;; nametree ~ ((a b c))

       ;; => c is first list, third slot ~> SHALLOW-ARGUMENT-REF2

       x := 2

       ;; nametree ~ ((x) (a b c))

       ;; => c is second list, third slot ~> DEEP-ARGUMENT-REF 1 2

     }

  Here, now, after the ``x`` assignment, we have an ``x`` in scope and
  then all three of ``a``, ``b`` and ``c`` are known names another
  level out.  All three were created with the same
  variable-introducing statement, ``let``

* ``flags`` -- we'll need some flags to indicate whether:

  - the expression is in tail position

    This is very important -- and surprisingly easy to maintain -- to
    give us the power of `tail call optimisation
    <https://en.wikipedia.org/wiki/Tail_call>`_.

  - an :lname:`Idio` addition is the nature of variables being created

    Here, we're looking at whether the variable is being created:

    * lexically, because we found it in the name tree

    * at top-level, because we couldn't find it in the lexical name
      tree

    * in a dynamic or environmental or computed context -- which is
      effectively top-level but managed in a different way

* ``cs`` -- a set of known constants

  Nominally, this can be used as a "known top-level names" list
  (amongst other things) but in :lname:`Idio` it is used to map a
  constant of any kind (symbol, list, array, etc.) into a unique
  integer for embedding in the byte code.

* ``cm`` -- an :lname:`Idio` addition is the current module

  As the source code switches between modules the expectation is that
  the evaluator can find the correct variable (ie. *my* ``v`` not the
  other guy's ``v``) and to effect that we need to track any changes
  to the sense of the current module by latching onto any module
  changing statements in the source code.

All of which are :lname:`C` lexical variables used throughout
:file:`src/evaluate.c` (and :lname:`Idio` lexical variables in the
:lname:`Idio` variant :file:`lib/evaluate.idio`, the
:term:`metacircular evaluator`).

In effect, all of the above become formal parameters to almost every
function in the evaluator.

    In case anyone is still reading the ``s`` in ``cs`` for the
    constants is for "star" as in a more :lname:`Lisp`\ y or EBNF-y
    ``c*`` meaning zero or more.

    There is also use of the likes of ``ep`` with the ``p`` for "plus"
    as the :lname:`C` equivalent of ``e+`` meaning one or more.

evaluate
--------

Kicking it all off is ``idio_evaluate()`` which looks like this:

.. code-block:: c

   IDIO idio_evaluate (IDIO src, IDIO cs)
   {
       ...
       
       IDIO m = idio_meaning (src,
			      src,
			      idio_S_nil,	/* name tree */
			      IDIO_MEANING_FLAG_NONE,
			      cs,
			      idio_thread_current_module ());

       ...
       
       return IDIO_LIST2 (..., m);
   }

It'll take some source code, ``src``, and a list of known constants,
``cs``.  The source code bit is obvious and most invocations will pass
the virtual machine's constants array for constants.


Fundamental Meaning
===================

As noted elsewhere, we rely on the evaluator distinguishing between
*special forms*, *templates* and anything left over is a *derived
form* or a constant.

It is *hugely* tempting to add to the list of special forms.  Of
course, the magic works but it will become a bind it is hard to
extract yourself from.

However, even :lname:`Scheme` has a minimal set of special forms to
let you bootstrap everything else:

* ``define`` and ``set!`` allow you to bind a name to a value and to
  change that binding

* ``quote`` prevents the evaluator evaluating an expression

* ``if`` provides the conditional *consequent* / *alternative*
  **without** the evaluator evaluating either

* ``lambda`` (or ``function`` in :lname:`Idio`) lets you define
  abstractions which you can subsequently invoke -- these are the
  derived forms

* ``define-macro`` (or ``define-template`` in :lname:`Idio`) lets you
  define your own "special form" -- special in that the arguments are
  not evaluated -- albeit all you can do is return more code for the
  evaluator to evaluate.

There are other special forms which have a genuine need to be handled
specially -- think of anything that needs to manipulate internal
:lname:`C` state -- and, of course, some that have snuck in because it
is convenient etc..

So, the premise of the main evaluation loop is simply to look at the
expression to hand and determine if it is special, a template or
otherwise treat it as a derived form or constant.

:lname:`Lisp`\ y languages always have the functional part in the
first position of a list so, if the expression is a list we simply
need to look at what the first element is.

``idio_meaning()`` in :file:`src/evaluate.c` (a debatably poor name as
it *is* the evaluator but almost everything is called
:samp:`idio_meaning_{something}`!) has a big test:

.. code-block:: c

   IDIO idio_meaning (IDIO src, IDIO e, IDIO nametree, int flags, IDIO cs, IDIO cm)
   {

       if (idio_isa_pair (e)) {
           IDIO eh = IDIO_PAIR_H (e);
           IDIO et = IDIO_PAIR_T (e);

	   /* e is (eh ...) */

           if (...) {
               ...
	   } else if (idio_S_quote == eh) {
	       ...
	   } else if (idio_S_function == eh) {
               ...
	   } else if (idio_S_if == eh) {
	       ...
	   } else if (idio_S_set == eh) {
	       ...
	   } else if (idio_S_define_template == eh) {
	       ...
	   } else if (idio_S_define == eh) {
	       ...
	   } else {
	       /* could be a template */
	       if (idio_isa_symbol (eh)) {
	           if (idio_expanderp (eh)) {
		       return idio_meaning_expander (e, e, nametree, flags, cs, cm);
		   }
	       }

	       /* default is a function call */
	       return idio_meaning_application (src, eh, et, nametree, flags, cs, cm);
	   }
       } else {
	   /*
	    * do something with:
	    *
	    * symbols: (de-)reference them
	    *
	    * constants: quote them -- evaluate (12) -> 12
	    */
       }
   }

and, without suggesting that that is everything, in fact, that single
(large) conditional clause is the guts of a :lname:`Lisp` evaluator.

The ``idio_meaning()`` function is physically large because it also
embeds the initial syntactic checking.

For example, ``quote`` takes a single argument to be quoted.  Which
means that no argument, ``(qoute)``, or more than one argument,
``(quote 1 2)``, must be caught and flagged as errors.

These are slightly obscure and might not happen in practice -- as most
use of ``quote`` is through :samp:`'{expr}` where the reader ensures
that there is only one expression passed to ``quote`` -- but we should
flag up the error to catch wayward typing.

This testing could be devolved to the specific special form handler,
``idio_meaning_quotation()``, in this case.  Yeah, maybe, but `I've
started so I'll finish
<https://wordhistories.net/2020/03/28/started-so-finish/>`_.

The Result of the Meaning
-------------------------

Not yet defined is what ``idio_meaning()`` is meant to return.  What
is it meant to *do*?

Our goal, from inferring some meaning from the lists of lists the
reader gave us, will be to head off to the code generator so we
probably want something amenable to that.

In our case, we're going to have the evaluator generate some
"intermediate code."  By this we mean to have reduced the source code
expressions down to some high level statements of intent with a vague
eye on how the virtual machine works.  I confess, that's not a
terribly clear description as, for me, it's a bit hard to describe
without showing examples (coming in the next section).

You can imagine, though, in our `highfalutin
<https://en.wiktionary.org/wiki/highfalutin>`_ source language we
*bind* variables to values whereas in the grubby world of machine code
we're going to "set" something.

The intermediate language has a group of constants,
:samp:`IDIO_I_{some_thing}` -- with the ``_I_`` for intermediate,
which, when we're finished doing whatever we intend to do with
intermediate code, will be translated reasonably straightforwardly
into our virtual machine's machine code, another group of constants,
:samp:`IDIO_A_{some_thing}` -- with the ``_A_`` for assembler.

Often, though, I'll refer to :samp:`SOME-THING {arg}` meaning the
corresponding assembly code written in a more
:lname:`Idio`-sympathetic way.

The structure of the intermediate code is... you guessed it, a list of
lists of lists.  The code generator is expecting that, of course, but
as it descends the tree of intermediate code statements it will
eventually reach the point where it has to emit a stream of byte code,
one intermediate instruction at a time.

In that sense the list of lists of lists becomes a depth-first
sequence of instructions for the virtual machine.

Specific Meaning
================

I don't want to go through all of the special forms but we can look at
a few to get the general gist.

quote
-----

``idio_meaning()`` invokes a slightly truncated argument list with:

.. code-block:: c

   return idio_meaning_quotation (IDIO_PAIR_H (et),
				  IDIO_PAIR_H (et),
				  nametree,
				  flags);

which, on reflection, could be even shorter still as
``idio_meaning_quotation()`` is the straightforward:

.. code-block:: c

   static IDIO idio_meaning_quotation (IDIO src, IDIO v, IDIO nametree, int flags)
   {
       ...

       return IDIO_LIST2 (IDIO_I_CONSTANT_SYM_REF, v);
   }

in other words, only the argument to ``quote``, the head-of-the-tail
of the original ``e``, is used.

What we're doing is returning an intermediate instruction to create a
"symbolic reference" to a constant from :samp:`{v}`.

*We* haven't created the constant -- the code generator will do that
-- but that is our intent.

What we imagine, then, is that the code generator will add :samp:`{v}`
to the virtual machine's array of constants and get back the integer
index into the array.  The code generator will then encode a
corresponding ``IDIO_A_CONSTANT_SYM_REF`` and then the integer into
the byte code.

When the VM runs it'll hit the ``IDIO_A_CONSTANT_SYM_REF`` instruction
which will prompt it to read an integer from the byte code and then
set the *val* register to the element in the constants array (indexed
by the integer it just read).

So, slightly indirectly, the current value being processed will be
:samp:`{v}`.

The code generator is much more complicated as is tries to make a few
educated guesses about how to speed things up.  For example, the
integer 1 is used "a bit" so it might make some sense to have a
special ``IDIO_A_CONSTANT_1`` opcode that simply deposits 1 in the
*val* register and avoids a lengthy indirection via the constants
array.

.. _if:

if
--

``if`` is the canonical special form in the sense that it **must not**
have its arguments evaluated before calling the "function" ``if`` --
there is no function ``if``, of course, its behaviour is encoded in
the byte code generated from the special form's behaviour.

The other :lname:`Scheme`\ ly aspect to ``if`` is that *everything* is
"true" except ``#f``.

.. sidebox::

   And we use it as the standard "not ``#f``" value.

As a side-effect, that means that ``#t``'s existence is very nearly
pointless as *any* value other than ``#f`` is true.  However, people
like a solid two values to choose from in a boolean set so we need to
keep ``#t`` around.

First, of course, there's a bit of argument checking.  ``if`` takes
two or three arguments: :samp:`(if {condition} {consequent}
{alternate})` and a variant for when there's no "else" clause,
:samp:`(if {condition} {consequent})`.

The latter causes us a problem when some wise-guy rumbles: :samp:`(if
#f {consequent})`.  Um, ``if`` **must** return a value -- *everything*
returns a value -- yet there is no :samp:`{alternate}` clause... what
gives?  The :lname:`Scheme` answer appears to be: "void".  A special
value suggesting "no computed answer."  The "void" value has no
printed representation -- well, it'll come out as ``#<void>`` which
the reader will reject -- although you can test for it with the
primitive predicate ``void?``.

For the most part, you suspect it is used in situations where the
result from the ``if`` clause is thrown away anyway.  In the
meanwhile, we have a shoo-in value for non-existent
:samp:`{alternate}` clause, ``idio_S_void`` -- another magic
constant-symbol.

``idio_meaning()`` invokes:

.. code-block:: c

   return idio_meaning_alternative (src,
				    IDIO_PAIR_H (et),	/* condition */
				    IDIO_PAIR_H (ett),	/* consequent */
				    ehttt,	/* alternate -- could be <void> */
				    nametree,
				    flags,
				    cs,
				    cm);

In other words the full set of lexical state.  This is because *any*
of :samp:`{condition}`, :samp:`{consequent}` or :samp:`{alternate}`
could be of arbitrary complexity.

``idio_meaning_alternative()`` is the surprisingly concise:

.. code-block:: c

   static IDIO idio_meaning_alternative (IDIO src, IDIO e1, IDIO e2, IDIO e3, ...)
   {
       ...
       
       IDIO m1 = idio_meaning (e1, e1, nametree, IDIO_MEANING_NOT_TAILP (flags), cs, cm);
       IDIO m2 = idio_meaning (e2, e2, nametree, flags, cs, cm);
       IDIO m3 = idio_meaning (e3, e3, nametree, flags, cs, cm);

       return IDIO_LIST4 (IDIO_I_ALTERNATIVE, m1, m2, m3);
   }

where we recursively figure out the meanings of the three arguments
and return them in a list with the ``IDIO_I_ALTERNATIVE`` intermediate
code.

So, nothing interesting at all.  The code generator for ``if`` is
quite cunning, mind.

.. _tailp:

tailp
^^^^^

The only thing that will catch your eye is the use of
:samp:`IDIO_MEANING_NOT_TAILP ({flags})` which unsets the "in tail
position" bit in :samp:`{flags}`.  What's going on here?

Let's have a quick think about things in tail position.  If your
alternate expression is in the middle of a sequence:

.. parsed-literal::

   define (foo) {
     *this*
     if *condition* *consequent* *alternate*
     *that*
   }

then you assume that whatever is processing the sequence will have
handled that this ``if`` is not in tail position so us unsetting the
"tailp" flag is neither here nor there.

What if we *are* in tail position?

.. parsed-literal::

   define (foo) {
     *this*
     *that*
     if *condition* *consequent* *alternate*
   }

We know that one of two possible code sequences will apply: either the
evaluation of the :samp:`{condition}` results in "true" and then we'll
run the code for the :samp:`{consequent}`:

.. parsed-literal::

   define (foo) {
     *this*
     *that*
     *condition*
     *consequent*
   }

or the evaluation of the :samp:`{condition}` results in "false" and
then we'll run the code for the :samp:`{alternate}`:

.. parsed-literal::

   define (foo) {
     *this*
     *that*
     *condition*
     *alternate*
   }

In *both cases*, though, the evaluation of the :samp:`{condition}` is
**not** the last thing to be run.  It is *never* in tail position
hence we can scrub the flag when processing it.

Either of the of the :samp:`{consequent}` or :samp:`{alternate}`
*could* be in tail position so we'll leave the flag alone.

But notice that we don't *set* the flag.  We only ever disable it.

:socrates:`How does it ever get set, then?` Well, it's only ever set
for the body clause of a function *definition*.  The reason
is slightly back-to-front.

The whole reason to have tail call optimisation is to avoid "blowing
up the stack" by making too many nested function calls.  Every
function call tacks a bit more *stuff* on the stack -- we save a bit
of state in case the thing we call overwrites it -- and that
accumulated *stuff* will, eventually, add up.

If we know that we're *in* a function call and the *last* thing we do
in this function call is make a function call to someone else then we
can skip any state preservation nonsense because whatever the guy
we're about to call is going to return is what *we* would be returning
ourselves in turn.  So this guy might as well return direct to our
caller.

The details for returning to our caller are on the stack ready for us
to use so instead of the full function invocation palaver we effect a
sort of function "goto."  This next guy *replaces* me and, instead of
returning a value to me, will non-the-wiser be returning the value to
*my* caller.

So, this "tailp" trickery **must** require that we're *in* a function
call -- otherwise the replacement and expectation about a function
return won't be on the stack -- for us to enact it.  Hence the "tailp"
flag is only set during the evaluation of a function definition.

A function's body, however, is usually a sequence -- as in a block --
in which case the "tailp" flag is suppressed for all but the last
statement in the sequence.

Thereafter, whenever a function is invoked, when it reaches the last
statement in the body, "tailp" would have been enabled during the
evaluation of the meaning of that statement and if that statement
resulted, ultimately, in a function call at the end, then the function
call will be a function "goto."

.. _define:

define
------

``define`` introduces a variable at "top level" and then assigns a
value to it, or, more properly, *binds* it to a value.

The English language expression, "assign to", suggests that the
variable might be a container for the value.  In practice, most
:lname:`Idio` values are allocated on the :lname:`C` heap and the
underlying :lname:`C` ``IDIO`` values refer/point to the allocated
heap memory -- unless it's a constant or fixnum in which case we
squeeze it into the upper bits of the ``IDIO`` "pointer".

So, correctly (most of the time), the :lname:`C` ``IDIO`` variable
refers/points to some splodge of memory and, by extension, the
:lname:`Idio` variable is *bound* to that splodge of memory (value).

If we subsequently "assign" a different value to the variable then in
practice we are simply changing the reference in the ``IDIO`` entity
to point at a different splodge of memory and the :lname:`Idio`
variable is now bound to a different value.

The phrase "assigning a value to a variable" is endemic and mostly
incorrect.  However, it's what we say.

"Top level" could mean a global table of known names or, as in the
case for :lname:`Idio`, a module-specific table of known names.

This "top level" is usually described as the *environment* during
:lname:`Lisp` language processing.  Of course "environment" has an
alternative meaning to us shell-people so I'm slightly loathe to use
it.  The virtual machine's register is still *env*, though, as a
throwback to our :lname:`Scheme`-ly origins.

You might ask why we want to *define* things rather than simply assign
to them, auto-creating the name in the top level as we go?  Well, I
suppose we could (and, indeed, we can) but there's an air of
organisation and clarity if we're defining things.

In addition, if a variable is defined before it is (otherwise) used --
ie. there are no forward lookups of variables -- then we don't have to
employ extra checks to ensure a variable was eventually defined and
we've not just been left hanging in the wind, here.

``define`` itself has a couple of forms it can be used in:

#. :samp:`define {name} {expression}` -- for the straightforward
   assignment/binding of :samp:`{name}`, a symbol, to some value
   resulting from the evaluation of :samp:`{expression}`

#. :samp:`define ({name} {formals*}) {expression}` -- for the
   definition of a function with the reultant function value assigned
   to :samp:`{name}`

   :samp:`{expression}` will most likely be a block:

   .. parsed-literal::

      define (*name* *formals\**) {
        ...
      }

   This second form is the equivalent of:

   .. parsed-literal::

      define *name* (function (*formals\**) {
        ...
      })

   and this rewrite is exactly what the evaluator does.

   You'll note the extra parentheses around the function definition
   which, in the first instance, mean that ``define`` isn't given an
   arbitrary number of arguments but just two, the *name* and
   *expression*, and secondly give the impression (realised in
   practice) that like any other argument, say, ``(+ 1 2)``, the
   anonymous function definition is instantiated into a function value
   and it is the function value that is passed to ``define``.

   We'll see this rewrite in a second.

.. sidebox::

   Though maybe not as lazy as that *other* guy...

I'm as lazy as the next guy so the ``:=`` operator has been co-opted
into use as a synonym for the first form of ``define``: :samp:`{name}
:= {expression}`.

Of course, if it's the second form, ie. the second argument is a list,
and we're implicitly constructing a function from it then we need to
re-tag the newly created function with the source code properties of
the original.

``idio_meaning()`` invokes:

.. code-block:: c

   idio_meaning_define (src, IDIO_PAIR_H (et), ett, nametree, flags, cs, cm);

where ``idio_meaning_define()`` looks like:

.. code-block:: c

   static IDIO idio_meaning_define (IDIO src, IDIO name, IDIO e, ...)

Here, :samp:`{name}` might be a symbol or a list -- depending of which
form of ``define`` was in use.

If :samp:`{name}` is a list then we know it is :samp:`({name}
{formals*})` so we can extract both :samp:`{name}` and
:samp:`{formals*}` (the head and tail of the incoming :samp:`{name}`)
to construct a new function, rewriting both :samp:`{name}` and
:samp:`{e}` in the process:
   
.. code-block:: c

       if (idio_isa_pair (name)) {
	   /*
	    * (define (func arg) ...) => (define func (function (arg) ...))
	    *
	    * NB e is already a list
	    */
	   e = idio_list_append2 (IDIO_LIST2 (idio_S_function,
					      IDIO_PAIR_T (name)),
				  e);
	   name = IDIO_PAIR_H (name);

	   idio_meaning_copy_src_properties (src, e);
       }

If :samp:`{name}` *wasn't* a list then this is a simple
assignment/binding and we can do a quick check on :samp:`{e}` as
*that* should just be a simple expression.

.. code-block:: c

       if (idio_isa_pair (name)) {
	   ...
       } else {
	   if (idio_isa_pair (e)) {
	       e = IDIO_PAIR_H (e);
	       idio_meaning_copy_src_properties (src, e);
	   }
       }

this means that :samp:`define {name} {expr1} {expr2} ...` is quietly
reduced to just :samp:`define {name} {expr1}`.  Perhaps we should
complain more?

Next we need to look :samp:`{name}` up.  It *might* already exist.  In
fact, it might be a *lexical* variable!  In both of those cases, we'll
simply be reverting to assignment of the existing variable -- **not**
creating a new one.

.. code-block:: c

       IDIO sk = idio_meaning_variable_kind (src,
					     nametree,
					     name,
					     IDIO_MEANING_TOPLEVEL_SCOPE (flags),
					     cs,
					     cm);

       /* some top level variable creation hocus-pocus if required */

:samp:`IDIO_MEANING_TOPLEVEL_SCOPE ({flags})` is used to indicate what
sort of variable should be created if an existing variable is not
found (hint: a toplevel variable).

The "hocus-pocus" is important -- though the details aren't as it's a
bit bespoke -- in that if the result of the variable lookup does not
have a VM variable array index associated with it then we generate one
right now.  We *are* defining the variable, it definitely exists.

Almost done.  We now have an existing or new (top level) variable in
our hands so we can do the real action, the assignment which, given
that assignment, ``=`` or the :lname:`Scheme`-ish ``set!``, needs to
be handled in its own right simply means we can jump on the back of
it:

.. code-block:: c

       return idio_meaning_assignment (src,
				       name,
				       e,
				       nametree,
				       IDIO_MEANING_DEFINE (IDIO_MEANING_TOPLEVEL_SCOPE (flags)),
				       cs,
				       cm);


We pass in a "define" flag with :samp:`IDIO_MEANING_DEFINE ({flags})`
which adds a prefix to what the assignment function will generate.

We could pull the prefix code the assignment function adds back here
but two other places (defining dynamic and environment variables) also
do the same.  So, put the prefix code in three places or one?  

Assignment
----------

Assignment *is* a lot more interesting.  Remember it's called directly
as well as from :ref:`define`.

A quick recap on the various ways we might stumble over the assignment
of, in particular, a free variable.  If we have previously defined a
variable (or are in the act of defining one) then we should have an
index into the VM's variable array to hand, :samp:`{vi}`, and can
perform the assignment directly with a :samp:`GLOBAL-VAL-SET {vi}`
instruction.

On the other hand, if we're mid-function assigning to a variable we
haven't seen defined yet, ie. a forward reference, then we ought to
complain if, come the time of assignment when the code is run, the
variable had never been defined.  That's poor form on the part of the
coder (*bad user!*).

This is where it gets a little tricky.  We know the variable is used
-- we're about to assign to it -- but we need to know *separately*
whether the variable was defined.  So the variable lookup also returns
the extra information -- in particular it returns 0 (zero) for the VM
variable array index.

Under these circumstances we need to have the VM perform a check,
which means a different opcode, :samp:`GLOBAL-SYM-SET {ci}`, where we
require to pass in an index into the VM's constants array in order
that we can dig out the symbol and perform the necessary lookups
(through the module's top-level and the exports of its imported
modules) to find out if its been defined yet.

Clearly, this isn't as lean a process as simply assigning to a known
variable.  What is worse is that we cannot change the opcodes (it's
been a while since you've been able to modify assembler mid-run --
think: read-only ``.TEXT`` segments -- and we should not be bucking
any trends here) so this assignment will *always* have to perform this
relatively convoluted lookup to get the variable array index it
ultimately needs to do the real assignment.

    When I get round to :ref:`pre-compilation` which will require a
    double dereference for pre-compiled byte code brought in "from the
    cold" then I suspect that *all* the generated byte code will fall
    into line -- for consistency if nothing else.

    The only thing that will lose out are any known direct variable
    assignments, :samp:`GLOBAL-VAL-SET {vi}`, which would be replaced
    with a double dereference.

    Unless it's left in as an option.

Anyway, back to assignment in ``idio_meaning_assignment()``.

We'll skip the bit about :ref:`setters` (too advanced) and syntax
checking (too dull).

We'll figure out the meaning of the expression passed in:

.. code-block:: c

   IDIO m = idio_meaning (e,
			  e,
			  nametree,
			  IDIO_MEANING_NO_DEFINE (IDIO_MEANING_NOT_TAILP (flags)),
			  cs,
			  cm);

which handles two things:

#. the expression is not being evaluated in tail position

   This is the expression on the right hand side of an assignment.  It
   will be evaluated before the assignment itself and therefore cannot
   be in tail position.

#. we turn off the "define" flag (if it was turned on)

We'll then lookup what *kind* of a variable :samp:`{name}` is.  If the
variable didn't exist previously then it will now, as a top level one,
except it'll have no value index associated with it.

The kind of variable is now important as it affects the code we want
generated:

* if it is a lexical variable then we can generate
  :samp:`SHALLOW-ARGUMENT-SET{i}` or :samp:`DEEP-ARGUMENT-SET {d} {i}`
  code as appropriate where the variable lookup will have informed us
  of the relevant values for :samp:`{d}` and :samp:`{i}` (and it's a
  "shallow" reference if :samp:`{d}` is zero)

  These can be return immediately, there's nothing more to do.

* if it is a top-level variable then:

  * if we haven't seen a definition yet then we can generate a
    :samp:`GLOBAL-SYM-SET {ci}` assignment

    .. code-block:: c

       assign = IDIO_LIST3 (IDIO_I_GLOBAL_SYM_SET, fmci, m);

  * otherwise we can generate a :samp:`GLOBAL-VAL-SET {vi}` assignment

    .. code-block:: c

       assign = IDIO_LIST3 (IDIO_I_GLOBAL_VAL_SET, fgvi, m);

* if it is a dynamic or environment variable we generate a
  :samp:`GLOBAL-SYM-SET {ci}` assignment

* if it is a computed variable we generate a :samp:`COMPUTED-SYM-SET
  {ci}` with or without a definition tag and return immediately

* if it is a predefined variable -- ie. a primitive -- then there's a
  bit of a dance regarding *templates* which might get run between now
  (when we've just created a new toplevel variable overriding the
  predefined variable) and when the byte code is run to (re-)define
  this new toplevel variable.

  So we temporarily set the new toplevel to the old predefined value.

  In this sense, there is a general assumption that if you intend to
  redefine ``map``, say, then your intention is to create a new
  function to iterate over lists, applying a function and collecting a
  result and not, say, go off on some `cartographic odyssey
  <https://mapdragons.com/all-over-the-map-book/>`_.

  Maintaining the old functionality until the new functionality is
  defined seems sensible enough.

Finally, then, we can return either the assignment or the assignment
with a "define" prefix:

.. code-block:: c

   if (IDIO_MEANING_IS_DEFINE (flags)) {
       return IDIO_LIST2 (IDIO_LIST4 (IDIO_I_GLOBAL_SYM_DEF, name, kind, fmci),
			  assign);
   } else {
       return assign;
   }

sequence
--------

For a sequence of statements it is quite important to squash the
:ref:`tailp` flag for all but the final statement.

Otherwise the three sequence functions, ``begin``, ``and`` and ``or``,
only really differ by:

#. their default value if they are not passed any arguments:

   * ``(begin)`` is "void" (see :ref:`if <if>`)

   * ``(and)`` is ``#t``

   * ``(or)`` is ``#f``

#. how they decide to stop processing the sequence and what value to
   return

   * ``begin`` -- stop when it gets to the end of the sequence and
     return the value of the last expression

   * ``and`` -- stop if any value is ``#f`` and return the last value
     computed

   * ``or`` -- stop when any value is not ``#f`` and return the last
     value computed

    Remember, these are the sequence functions not the ``and`` and
    ``or`` *operators*.

They are processed identically, though, at this stage.

Assuming they *do* have some arguments ``idio_meaning()`` calls:

.. code-block:: c

   return idio_meaning_sequence (et, et, nametree, flags, eh, cs, cm);

where ``eh`` will be ``begin``, ``and`` or ``or`` and ``et`` will be
the argument expressions.

``idio_meaning_sequence()`` does a quick test:

* if the arguments are, in fact, a single argument then we call
  ``idio_meanings_single_sequence()`` which (recursively) returns the
  meaning of the head of the list of argument expressions.

* otherwise we *would* have followed in the footsteps of
  :ref-title:`LiSP` in calling a function
  ``idio_meanings_multiple_sequence()`` except :ref-title:`LiSP`,
  using the underlying :lname:`Scheme` implementation can recurse to
  its heart's content whereas we will eventually blow up our
  :lname:`C` stack if the sequence is too large.

  The exemplar "large sequence" is that sequence of statements in a
  large source file.

  In practice, then, we convert the :lname:`Scheme`\ ly recursion into
  a :lname:`C`-friendly iterative loop and walk down the list of
  arguments converting each one in turn into some meaning and tacking
  it onto a list.

  Technically, we push it onto the front of a now reversed list of
  meanings which, come the end of the loop, we reverse.

  However we have managed it, we have a correctly ordered list of
  meanings onto the front of which we tack the
  :samp:`IDIO_I_{sequence}` intermediate code -- ``IDIO_I_BEGIN``
  etc..

In other words:

* :samp:`(and {e1})` becomes just :samp:`{m1}` (converting an
  expression into a meaning)

* :samp:`(and {e1} {e2} {e3})` becomes :samp:`(IDIO_I_AND {m1} {m2}
  {m3})`

.. _module:

module
------

As mentioned previously, the evaluator cares about the current module
and the virtual machine... not so much.  The virtual machine does
retain the value for the current module if only to have a value to
return for ``(current-module)``.

The evaluator, of course, needs to keep track of the current module so
it can figure out which ``v`` you are referring to.

Today it all just works but back when I was loading files a little
differently, ``module`` and friends, required some evaluator support.
This section gives a little history you might learn from.

First, a quick diversion.

.. aside::

   I thought that *concomitant* was along the lines of "co-committed"
   -- albeit with a funny spelling (so what's new in English?)

   However, it is derived from *con* (together with) and *comes*
   (companion) ultimately giving you the meaning "accompanying."

   Here it is used to mean "must be defined with reference to each
   other."

In the source code you'll be using :samp:`module {m}` to change
module.  ``module`` is a template, though, partly because it needs to
be *concomitant* with ``load``.

We have a semantic problem in that if you load in a file which, at the
top, says ``module foo`` then when do you stop being in module
``foo``?  Naturally, you will say, *at the end of the file*.  When is
that, given that you are reading a sequence of statements from the
file?

There needs to be a hook into ``load`` to handle this -- but not the
hook you necessarily expect.  ``load`` could also fail and quit early
because of any kind of error when reading and evaluating the file.
You would expect it to "unwind" the ``module`` statement then too.

For handling modules I've taken an idea from STklos_, that of a module
"stack" and lets you nested :samp:`(define-module {name} & {body})`
statements.  ``define-module`` will catch any conditions an unwind the
module stack.

I don't actually use ``define-module`` but rather have a simple
:samp:`module {name}` statement which flips the rest of the file (or
to the next ``module`` statement) into module :samp:`{name}`.

I did add an :samp:`(in-module {name} & {body})` which functions
identically to ``define-module`` but just feels better purposed.  Not
that I use *it* much but it can come in handy.

OK, when we run ``load`` it needs to be module-aware -- and condition
aware! -- and reset the current module back to whatever it was when
``load`` started.  And remember to return the result of the actual
(original) ``load`` call -- not that many people will look at it.

Back to the evaluator.  In fact, back to when I was entertaining
myself with the idea of reading all the expressions in from the
source, evaluating them all then running the generated code from them
all.  (Rather than, read, evaluate and run one expression, read,
evaluate and run the next expression, etc..)

The ``module`` statement -- as the evaluator sees it -- isn't going to
change the sense of the current module until we actually get round to
running the code which is going to be ages away after we've evaluated
the rest of the statements in the file.  The very statements that want
to know they're in a different module.  Hmm.

The above diversion tells us that ``module`` is a template -- which
ultimately calls the primitive :samp:`%set-current-module! {name}`.
It seems we have a choice, we could replace the primitive
``%set-current-module!`` with a special form (which makes a single
function call to set the *mod* register in the VM) or we could have
the evaluator spot ``module`` as a special form and then run the
expander code for ``module`` anyway.

For some reason I did the latter.  I think it's because
``%set-current-module!`` can be given a parameter rather than a symbol
and therefore the evaluator won't know the value of it until the code
is run.  ``module``, on the other hand, is forced to be passed a
symbol (because it's a template).

Anyway, for the evaluator, when we see the ``module`` statement, we'll
steal the argument (which must be a symbol because ``module`` is a
template and so won't have had any arguments evaluated) and set the
current module directly here and now.  This immediately affects all
future variable lookups which will use the current module as its
starting point.

This *feels* slightly wrong.  We're changing the state of the
currently running process whilst evaluating and therefore before any
code is run.  However, it does mean that the evaluator has the correct
sense of the current module and subsequent variable lookups do the
right thing.

Also note that nothing has set the module back to its original value.
We *rely* on the improved concomitant ``load`` to do that work for us.

There is a similar knock-on effect on module imports and, arguably,
exports, as, in particular, module imports need updating immediately
in order that the rest of the statements can successfully use
variables exported from other modules.  We can't wait until the code
is run before knowing what we've imported from other modules.

So, the problem here is *entirely* the "all in one" loading method.
If we read, evaluate and run a statement at a time then everything
just falls into place.

.. include:: ../../commit.rst

