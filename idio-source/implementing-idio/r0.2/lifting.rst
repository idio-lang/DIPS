.. include:: ../../global.rst

**************
Lambda Lifting
**************

Technically, we're looking at both *closure conversion* and *lambda
lifting* but the title captures the overall goal.

It turns out we're (accidentally) pretty close but there's still some
hard yards ahead.

The Problem
===========

Yet another problem noted when debugging is that some functions seem
to be called repeatedly but not a lot of times.  For example, ``map2``
appears several thousand times after running the test suite but each
``map2`` is only called a few times -- and, for about two-thirds of
those, is called only once.  What's going on?

``map2`` is a recursive function defined inside the function assigned
to ``map`` in :file:`lib/bootstrap/s9-syntax.idio`.  In essence it is:

.. code-block:: idio

   map := {
     ...

     function (f & a*) {
       map2 :+ function (a* r) {
          if (null? (ph a*)) {
	    reverse! r
	  } {
	    map2 (pt-of a*) (pair (apply f (ph-of a*))
	                          r)
          }
       }

       map2 a* #n
     }
   }

Hmm.  ``map2`` is called at the end of the (to-be-assigned) map
function and for the recursive loops of ``map2`` inside itself.

But we also get to see the reason why we see so many instances of
``map2``.  The (to-be-assigned) map function's body looks like:

#. create a function called ``map2``

#. invoke it

Every time we call this map function we'll create a *new* closure
called ``map2``.  *Doh!*

The Scale of the Problem
------------------------

As to the scale of the problem, if we look at some late-0.2 VM stats
from a run of the test suite we can observe, with a sprig of debug,
that the evaluator sees around 2200 abstractions (some of these will
be closed applications) and subsequently that the VM creates around
189,000 closures.

.. aside::

   Albeit the time is lost in poorly chosen hashing algorithms which
   required this shocking figure to provoke me into rooting about to
   find out why.

And takes about 10% of the test suite's running time to do so.

The Solution
============

Hence the (overall goal) of lambda lifting, the idea that, if we
satisfy certain conditions, then we could redefine ``map2`` as a
top-level function and call it instead:

.. code-block:: idio

   lifted-map2 := function (a* r) {
      if (null? (ph a*)) {
	reverse! r
      } {
	lifted-map2 (pt-of a*) (pair (apply f (ph-of a*))
	         		      r)
      }
   }

   map := {
     ...

     function (f & a*) {

       lifted-map2 a* #n
     }
   }

which looks cool'n'all but has a slight problem.  ``lifted-map2``
refers to ``f``, the function-to-be-applied, that was passed to the
map function.  If we naïvely evaluate ``lifted-map2``, we will be
looking for an ``f`` in the top-level instead.

The obvious solution is to pass it along in turn:

.. code-block:: idio

   lifted-map2 := function (f a* r) {
      if (null? (ph a*)) {
	reverse! r
      } {
	lifted-map2 f (pt-of a*) (pair (apply f (ph-of a*))
				       r)
      }
   }

   map := {
     ...

     function (f & a*) {

       lifted-map2 f a* #n
     }
   }

Which is easy enough to do in this case but becomes something of a
bore in general.

Closure Conversion
------------------

So we come to the first part of the solution, closure conversion.

If you "read all about it" you'll discover that the key to success is
to replace your function with a combination of a function and
environment, together being called a closure.

At which point *we* say, "hang on, don't we already do that?"  Why,
yes, yes we do.

So it turns out that we're already halfway there thanks to (blindly!)
following :ref-author:`Queinnec` in :cite:`LiSP` with our handling of
functions.

There's a little bit more to it than that, though.

They key aspect of this environment for the lambda lifting trick to
work is the handling of *free variables*.  Here we need to get quite
precise.

* there are global variables which don't count in our analysis because
  they are global and can be gotten by anyone

* there are the parameters to the function we want to lift which also
  don't count because they will be supplied to us as arguments whether
  we're a nested or global function

* that leaves those remaining variables in the function we want to
  lift which are (usually) someone else's parameters (in a strict
  :lname:`Scheme` sense) and/or local variables in :lname:`Idio`

Let's revisit ``map2``:

.. code-block:: idio

   map2 :+ function (a* r) {
      if (null? (ph a*)) {
	reverse! r
      } {
	map2 (pt-of a*) (pair (apply f (ph-of a*))
			      r)
      }
   }

There are several global names, things like ``null?``, ``ph``,
``reverse!`` and so on.  We can ignore all of those.

There are our own parameters, ``a*`` and ``r``, and we can ignore
those as well.

That leaves us with, in this case, just ``f`` which happens to be a
parameter to the (enclosing) map function.

From a closure conversion perspective, then, the environment we need
to pass should contain ``f``.

Hmm.  As it turns out, then, we *can't* do any lambda lifting of
``map2`` because of its use of the free variable ``f``.  Let's carry
on thinking the problem through, though.

Thanks to :ref-author:`Queinnec`, though, when we came to define
``map2`` at the start of the map function all of our
``CREATE-CLOSURE`` code falls into place, including references to
``f`` as index 0 of the current (map function's) frame.

Indeed, the evaluation and code generation for the body of ``map2``
will have correctly identified the reference to ``f`` inside ``map2``
as a ``DEEP-REFERENCE 1 0`` (probably) to find ``f`` in the 0\
:sup:`th` index of the frame above the current (``map2``'s body)
frame.

If you recall, the evaluator builds stacks of variable names as it
processes bodies of code and then supplies the code generator with
diligent dereferences into future linked frames of arguments to
function calls.  Depending on how deep into sections of code you have
gone, your reference to ``f`` will be the 0\ :sup:`th` index of the
current frame, the 0\ :sup:`th` index of the frame beyond that, the 0\
:sup:`th` index...you get the picture.

The VM, when it sees the ``CREATE-CLOSURE`` instruction, will call
``idio_closure()`` with the current *frame* at the time of processing
(and various other relevant parts).

But that's the nub of the issue.  It's the VM calling
``idio_closure()`` with the current *frame*.  We'll come back to this
in :ref:`limitations`, below.

Accidental Design Bonus
^^^^^^^^^^^^^^^^^^^^^^^

The actual code for the map function looks like:

.. code-block:: idio

   map := {
     ph-of := ph-of
     pt-of := pt-of

     function (f & a*) {
       ...
     }
   }

where we kept local copies of (what used to be) two immediately
previously defined functions.  Those two have now become primitives as
part of the earlier efficiency drive but they serve to demonstrate a
handy accident.  Retaining local references to the original global
functions means that this code will always call the primitives even if
someone subsequently redefines ``ph-of`` or ``pt-of``.

The nominal way of handling these local assignments was a set of
nested *closed applications* which, whilst functional\ *[sic]*, were a
little inefficient.

Instead, we introduced the :ref:`function+ <ref:function+ special
form>` special form which handles the local variables by extending the
current frame with extra pseudo-parameters.

In other words, even local variable assignments now appear in the
``CREATE-CLOSURE`` environment and the evaluator and code generator
both do the right thing to extract them.

Nothing special to do here, then.

.. _`limitations`:

Limitations
^^^^^^^^^^^

It's not all plain sailing, though.  That the VM calls
``idio_closure()`` with the current *frame*, at the time of execution,
is what is going to catch us out.

If we made ``map2`` a top-level function it wouldn't have this
time-of-execution *frame* available to it when it was created.

What we *could* do, is replace the ``CREATE-CLOSURE`` inside the map
function with some, say, ``SET-CLOSURE-FRAME``, opcode which would
update the top-level ``map2`` closure with the current *frame* and let
rip.

That seems OK until it becomes possible for ``map2`` to be called more
than once in the same execution stack.  Here, the top-level function
would be given the one *frame*, then given another *frame* and won't
get the original *frame* back before carrying on processing.

As it happens, the calls to ``map2``, in particular, are all in tail
position so we can merrily stamp over the top-level closure's *frame*
with impunity.

Unless there are nested calls to ``map``...  *Drat!*

We get into a similar mess if ``map2`` were passed as an argument to
another function or returned from the map function.  In either case,
there's an expectation that some other processing will occur and the
argument/returned function value will be called, this time with a
completely unrelated *frame*.

However, we're reliant on the top-level ``map2`` closure being
supplied with the right sort of *frame* to be able to extract the
correct ``f``.

Side-Issue
""""""""""

There is a side-issue from a code generation perspective while we're
throwing new ideas about.  To date we've taken a straight-forward,
"print what you see" approach to code generation.  Here, though, we
might take a step back.

The code representing the body part of a closure is self-contained and
position independent.  It could be put anywhere so long as the
dereferences into the stack of *frames* lines up.

The wider ``CREATE-CLOSURE`` code looks, you may :ref:`recall
<function creation>`, like:

#. the ``CREATE-CLOSURE`` opcode plus:

   * the function body's starting *PC*

   * static features such as:

     * name

     * signature string

     * documentation string

#. a jump to the instruction beyond the end of the function body's
   code

#. the function body's code (obviously, the *PC* above is the start of
   this)

#. the rest of the program

.. sidebox::

   The jump always needs to be passed as otherwise the act of defining
   a function would accidentally have it immediately run.  Probably
   not what you want.

Hmm.  In the spirit of lambda lifting, we could put the (jump and) the
function body's code at the top-level and adjust the *PC* passed to
``CREATE-CLOSURE`` accordingly.

That would leave the map function's body looking like:

* the ``CREATE-CLOSURE`` opcode for ``map2``

* a (tail-recursive) function call to ``map2``

rather then having the entirety of the ``map2`` function's body code
embedded in it.

.. _`Lambda Lifting I`:

Lambda Lifting I
----------------

Creating closures is quite involved with various properties to be
associated with the closure as well as the closure itself.  However,
most of that work is essentially static.  The closure body and
properties are unchanged from run to run.  The *only* thing that is
changing is that *frame* that the VM is going to associate with the
closure at run-time.

Maybe we want a two-step shimmy:

#. lift all closure definitions up to the top level and create a top
   level instance of the closure with a ``CREATE-FUNCTION`` opcode

   This is, in principle, a perfectly good closure -- top level
   because at the time it is processed, the VM won't have a frame of
   enclosing environments.  In practice, we don't give it a (lifted)
   name but merely stuff it into a value slot and use the index to
   that value in step 2.

#. at the point where we would have had the ``CREATE-CLOSURE`` with
   the full implementation, simply replace that with a cloning
   ``CREATE-CLOSURE`` opcode which takes a reference to the top level
   instance, cloning most of it, plus the all-important VM *frame*

In doing this, we've shifted the nested function's body code off to
the top leaving the enclosing function's body with the barest minimum
byte code to recreate the effect.

Lambda Lifting II
-----------------

Ideally, we would have the evaluator recognise that a nested closure
definition does not use any free variables and we can replace the
dynamic ``CREATE-CLOSURE`` with a simple function call to the (now
global) lifted closure.

That, however, requires revisiting the evaluator.  TBD.

.. include:: ../../commit.rst

