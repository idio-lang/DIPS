.. include:: ../../../global.rst

*********
Rationale
*********

There's a couple of situations we want to be able to handle:

* "simple" truncations of the flow of control

  These come in a couple of variations themselves:

  #. *lexical escapes* in the form of ``return`` from a function and
     ``break`` and ``continue`` in loops

     These allow you to jump around within a lexical block without
     further ado including "to the end" and therein effectively return
     from the function prematurely.

  #. error handling

     These are a subset of the generic conditions and restarts, below,
     in that they usually (but not always) involve the truncation of
     the current state back to some known (and presumably) safe place.

* conditions and restarts

  In the general case conditions and restarts might involve some
  programmatic ping-pong as the code figures out what it wants to do.

We must be able to support lexical escapes and error handling with
full blown conditions and restarts an interesting opportunity.

Considerations
==============

There are a few things to think about, though.

* First of all, can we solve the problem programmatically, without
  having to resort to modifying the core engine?  If we can, then *we*
  are not the limitations on what can be done in :lname:`Idio`.  That
  should be a good thing but might be a bad thing.

* Will the solution behave well with useful features like
  ``unwind-protect``?

* Will it impose a (substantial) cost?

.. _`return`:

``return``
----------

One of the particular bugbears, to my mind, is ``return``.  It sounds
simple enough, leave the current function (with a value).

Starting with the basics, then, what's the current function?  We need
some sort of representation of where the end of the function is in
order that we can go there.

Going there itself can't be the simple invocation of the ``RETURN`` VM
opcode because that assumes that the value on the top of the stack is
the next *PC* (program counter) value.  If we're partway through a
function when we see a ``return`` statement then we need, somehow, to
remove the extraneous guff off of the stack.

So we're looking at some kind of continuation, whose job is to refit
the stack to be correct for the saved *PC*.  Of note, at this point,
is that this *return* continuation will *always* be an unwinding of
the stack because we are not jumping into the middle of some saved
calculation from far away we are simply truncating the current
function to a point equivalent to have run through it completely.
This brings up the idea of a *delimited* continuation where, rather
than save the complete state need only save how much to truncate the
stack by.

How might we capture this return continuation?  We could rewrite the
body of the function:

.. code-block:: idio

   define (foo x) {
     x + 1
   }

might become:

.. code-block:: idio

   define (foo x) {
     call/cc (function (return) {
		x + 1
     })
   }

which, as a side-effect, happens to give us the lexical variable
``return``, a continuation, which we can invoke: ``return 0``.

However, there are several problems here.

In the very first instance, ``call/cc`` is passed a function which,
our rewriting rules will say we should replace with an invocation of
``call/cc`` which is passed a function which our rewriting rules
say...  Hmm, might take a while to compute.

We could be a bit more specific and only do the rewrite for named
functions, which will, as a handy side-effect, also eliminate all of
the implied functions that get created, for example, those ``let``
statements which transform into a closed function call:

.. code-block:: idio

   let ((x 10)) {
     x + 1
   }

would become:

.. code-block:: idio

   ((function (x) {
       x + 1
     }) 10)

That something is a named function can only be picked up in
assignment, rather than, definition, because we rewrote "internal"
functions as ``letrec`` assignments -- ie. we don't see the ``define``
word any more.

There is a downside, though, in that any genuine anonymous functions
(like the one we're passing to ``call/cc``) cannot use ``return`` if
we only ever cater for named functions.

OK, not ideal, but let's run with this a little more.

We now know we are assigning a function to a symbol.  If we rewrite
the body with a continuation capturing call then we hit another
problem.  We've just rewritten the body.  In and of itself that's not
a bad thing, we rewrite stuff a lot.  However this time the rewrite
includes something that captures the continuation and a continuation
requires some allocation of memory to store it.

One off calls to functions are not going to make a huge difference --
although across tens of thousands of function calls they will make
*some* difference.

The real problem is loops.  Any kind of loop but in particular, fast
light loops now become increasing sluggish and heavy loops.

The problem is subtle.  We've now told the loop to capture a
continuation and then call the associated function.  The continuation
includes a copy of the stack.  No problem.  We now invoke a function
which saves the program state on the stack and then runs its body
forms which are the original loop's body forms.  Somewhere in there it
will recurse, being a loop and all, whereon it starts again.  It'll
capture a continuation including the stack which is now just a little
bit larger than the last time we passed through and invoke a function
which saves the program state on the stack...

Oh dear, we now have some weird factorial copying of the stack going
on and in not very many loops, it turns out, you'll have filled all
available memory with nearly pointless copies of the stack.

We could mitigate this by using delimited continuations but they still
require some space and what was a previously (slow!) loop counting to
a trillion zillion will now run out of memory long before it reaches
its target.

Rewriting the body doesn't seem to be the answer.

Hmm.  But wait, those recursive loop calls are all *tail call*
invocations.  Can we change the code so that we only capture the
continuation for non-tail call invocations?  So, assuming it is not in
tail position, the first time we call ``foo`` we'll save a return
continuation and, somehow, make it available for that and subsequent
tail call invocations.

.. note::

   Of interest at this point, is that if we call a different function
   in tail position then the original return continuation is still
   correct for this different function.  Don't forget that a function
   called in tail position effectively replaces the current function
   and so the callee the new function returns a value to is the
   original callee of the function we captured the return continuation
   for.

   .. code-block:: idio

      define (foo x) (x + 1)

      define (bar x) (foo x)

      define (baz x) (bar x)

      baz 10

   This doesn't generate a hierarchical tree of calls:

   .. parsed-literal::

      baz 10 *calls*
        bar 10 *calls*
	  foo 10 *calls*
	    10 + 1

   because all of the sub-calls are in tail position, the call "tree"
   looks like:

   .. parsed-literal::

      baz 10 *is replaced by*
      bar 10 *is replaced by*
      foo 10 *is replaced by*
      10 + 1

   and ``11`` is returned *directly* to the top-level -- there is no
   unwinding back through ``foo``, ``bar`` and ``baz``, they have all
   been replaced in turn.

The answer is yes, the engine can, and obviously does, make that tail
or non-tail call distinction but that assessment is notionally part of
the evaluator and not part of the semantic evaluation of the code.
This is a little subtle, it's something we can do in the evaluator but
not something that you can do in a template because the template is
only performing a sort of textual manipulation and knows nothing about
the context of the source code it is manipulating.

Further, there becomes a separation of the capture of the continuation
-- which we determine based on the context in which the call to a
function is made, tail or non-tail call -- and the (probable) use of
that continuation -- as we assume the body of the code *might* call
``return``.

.. code-block:: idio
   :linenos:

   define (foo x) {
     if (x lt 0) {
       return 0
     } {
       foo (x - 1)
     }
   }

   foo 10

Here, the non-tail call to ``foo`` on line 9 should establish the
return continuation -- albeit the value returned is going to be
discarded by the looks of things.

The tail call to ``foo`` on line 5 should merely (re-)invoke the body
of ``foo`` without changing the stack.

The call to ``return`` on line 3 needs to be able to access the return
continuation which, given that it hasn't been passed it as a lexical
variable means it must be found dynamically.  The return continuation
must go on the stack (and be cleared off the stack in due course).

Evaluation
----------

Here's another tricky problem.  If we get the evaluator to do
something for us, how does it interact with user-level code?  I mean
that in the sense of the :lname:`C` evaluator (noting there is an
:lname:`Idio` variant of the evaluator but it is easier to distinguish
if one flow of control is in :lname:`C` and the other is user-level
:lname:`Idio` code) interacting with user-level code.

Wait, *should* the evaluator be interacting with user-level code?
Well, maybe.  And what do I mean by interacting?

Many reference implementations of features like ``dynamic-wind`` (and
its derivative, ``unwind-protect``) are implemented in user code,
ie. in :lname:`Idio`.  Ostensibly the code maintains a list of things
to do as you unwind the stack (cleanup operations being the obvious
cases) and the nominal language features, say, ``call/cc``, are
rewritten to call the various unwinding code chunks before invoking,
in this case, their nominal jump.

It's a little bit twisty-turney but very neatly done.  But the
twisting is in user-land and the evaluator isn't.  More importantly,
the evaluator isn't running in sync with the code, it is examining the
code in advance of anything being run in order that it can generate
byte code which will eventually be run by the VM.

In that sense, the evaluator is more like the :lname:`C` compiler
being run to generate a binary executable except that the evaluator
*can be* aware of the code in the "executable" (byte code) it is
generating.  You could imagine a :lname:`C` compiler that doesn't
generate a separate executable but rather accumulates all the object
code it generates so is aware of previously generated functions.
That's more where we are with the evaluator.

If we were being clever and wrote the original twisty :lname:`Idio`
code using private variables, say, with global interfaces then we have
a very tricky problem in that the evaluator won't have a reference to
any of those private variables.

We can have the evaluator rewrite the source code using the global
interfaces and re-evaluate it with all the caveats and complications
that we trip over as seen with :ref:`return`, above.

We could re-write all of the user-land code in :lname:`C` and have the
evaluator generate byte code that invokes the :lname:`C` equivalent
functions.  We'd also have to make all of that :lname:`C` code
available as primitives in :lname:`Idio` in order that any subsequent
(user-level) language features can also take advantage of, in this
case, the unwinding effect.

Having written everything in :lname:`C` we can only expose it all as
globally visible variables and/or primitives -- arguably no worse than
an :lname:`Idio` implementation although there's something nagging at
me that it is worse.

Special Forms
^^^^^^^^^^^^^

The basics of any special form are that they *cannot* be wrappered
because they are not functions they are more like the phenomena of
your language, they simply *are*.

Many rewriting tricks involve wrapping a given function in a new
version of it that does a little bit more calling the original
function.  A simple enter/leave wrapper might look like:

.. code-block:: idio

   define (foo x) {
     x + 1
   }

   foo = {
     orig-foo := foo

     function (x) {
       printf "enter: foo %s\n" x
       r := orig-foo x
       printf "leave: foo %s => %s\n" x r
       r
     }
   }

Someone can further rewrite ``foo`` to perform some other function,
say, creating a database record of calls to ``foo`` or somesuch.

.. sidebox::

   Which will annoy them intensely if they're stuck with your rubbish
   debugging!

Interestingly, this second rewrite cannot access the original ``foo``
as it is no longer referenceable.  The existing symbol ``foo`` is
associated with the first rewrite function which internally has a
reference to the original ``foo`` but otherwise the original is "lost"
to future users.



However, special forms are not functions, they cannot be captured in
the same way:

.. code-block:: idio

   orig-if := if

does not capture the special form ``if``, instead ``orig-if`` is the
symbol ``if``.  ``if``, the special form, does not exist as a
referencable thing, it is simply evaluated when the evaluator sees it
in functional position.  In this case, ``if`` is a standalone word and
will be dereferenced like any other variable.  In this case, I'm
presuming no-one has defined ``if`` as anything and therefore we'll
get the default result of the failure to lookup a variable which is
the variable's name.

.. include:: ../../../commit.rst

