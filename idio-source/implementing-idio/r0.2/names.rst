.. include:: ../../global.rst

**************
Function Names
**************

Closure Nemo
============

As noted in the previous section, the profiling reports an awful lot
of closures with a name of ``#n``.  Hmm, tricky.

It turns out you can reverse engineer which closure is which because
the first numeric column is the *PC* (program counter) of the closure
in question.  Now you can look in :file:`vm-dasm` and search for some
clues around that *PC*.  There'll usually be some reference to a line
of source code which makes it fairly obvious.

Evidently, whatever it was we thought we were doing to ensure that all
closures get named isn't working terribly well.  A lot of that code
was relying on the VM identifying that if it was about to bind a
closure value with a symbol then it should update the closure's
properties, if necessary, such that the closure's name would be the
symbol.

Clearly not working.

Part of my research for IOS included rummaging through
:ref-author:`Eli Barzilay`'s :lname:`Swindle` which includes
``named-lambda`` -- perhaps all :lname:`Scheme`'s have such a
function?  -- somewhat incongruously associating a name with an
otherwise anonymous function.

However that's probably the way to go.  Here we might use a base
special form, ``function/name``, which always takes a name and have
the syntax (or keep as a special form), ``function``, which is now a
simple wrapper to ``function/name`` but passes a gensym (prefixed with
``anon``, say).

Evaluator
---------

define
^^^^^^

We can change ``define (foo a b) ...`` to:

.. code-block:: idio

   define foo (function/name foo (a b) ...)

ie. pass the (otherwise anonymous) function-to-be's name as another
argument.  That in turn can be passed through to the
``FIX-CLOSURE``/``NARY-CLOSURE`` code in :file:`src/codegen.c` where a
reference to it can be added to the function construction as an extra
feature -- similar features include the signature string and
documentation string.  The VM can then reconstruct the name from the
reference when it sees the ``CREATE-CLOSURE`` opcode and calls
``idio_closure()``.

``idio_closure()`` is already creating the closure properties for the
signature string and documentation string so adding ``:name`` to the
properties isn't a problem -- other than slowing it down further, of
course.

define-template
^^^^^^^^^^^^^^^

We can do something similar for ``define-template`` noting that we
will want to do the same for the associated expander.

Body Rewrites
^^^^^^^^^^^^^

Elsewhere, the "rewrite body" and "rewrite body letrec" functions can
both take advantage of similar tricks.

Where we see what will become a "local" assignment -- where we extend
the current function's parameter list with some extra locals -- we can
use the binding symbol as a function name:

.. code-block:: idio

   define (foo a b) {

     local := function (x y) {
       ...
     }

   }

can become:

.. code-block:: idio

   define (foo a b) {

     local := function/name local (x y) {
       ...
     }

   }

Similarly, nested functions, using ``define`` or ``:+`` can be
reworked in a similar way.

Blocks Returning Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^

One area where we can't easily get the evaluator to do the hard work
for us is when a function is returning from a block, usually because
the function -- or functions -- are closing over some
local-to-the-block variables:

.. code-block:: idio

   add-1 := {
     n := 1

     function (x) {
       x + n
     }
   }

Here, it's hard for the evaluator to reason that the block is
returning a function.  Even harder is if there is more than one
function closing over the same variables:

.. code-block:: idio

   add-1 := #f
   sub-1 := #f

   {
     n := 1

     add-1 = function (x) {
       x + n
     }

     sub-1 = function (x) {
       x - n
     }
   }

In these situations we can change the code to call ``function/name``
directly:

.. code-block:: idio

   add-1 := #f
   sub-1 := #f

   {
     n := 1

     add-1 = function/name add-1 (x) {
       x + n
     }

     sub-1 = function/name sub-1 (x) {
       x - n
     }
   }

Which isn't *Art* but it's not awful, either.

Unchanging Functions
--------------------

There will be some places where there's no particular interest or
(current) advantage in naming what would be an anonymous function.
For example, the one-shot arguments to ``map`` or ``fold-left`` or
other higher-order functions (functions taking functions).

Here, if we're debugging, we're probably aware that we're in ``map``
and that it is calling its function argument.  If you're not aware, or
fancy a change, give it a name!  It will have a name already,
:samp:`anon/{nnn}`, just not a distinguished one that is easier for
you to identify.

Unchanging Names
----------------

There is a peculiarity of this behaviour of associating a name with a
function value -- the name sticks.

:socrates:`Wait, that was the idea, right?`

Mmm, maybe.  Suppose we had a function that was going to be passed a
function and a list and it was to apply the function to the list:

.. code-block:: idio

   define (my-ph l) {
     ph l
   }

   define (my-apply f l*) {
     f l*
   }

   my-apply my-ph '(1 2 3)

If we debug this, then *inside* ``my-apply`` we'll be applying the
parameter ``f`` to the parameter ``l*``.  However, the tracer/debugger
will report that ``my-ph`` is being applied to ``(1 2 3)``.

This is as much because the VM has no immediate visibility of the
parameter names -- only the parameter indices into the current
argument *frame*.

However, this also rears its head if you rename functions as part of,
say, increasing the complexity of a function:

.. code-block:: idio

   define (foo a) {
     ...
   }

   foo = {
     orig-foo := foo

     function/name foo (a) {
       ...
       orig-foo a
     }
   }

Even though we re-used the original ``foo`` under the guise of
``orig-foo``, the name associated with the function value (in its
properties) is still ``foo``.  So you'll have two ``foo``\ s running
with not much to distinguish them.

.. include:: ../../commit.rst

