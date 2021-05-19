.. include:: ../../../global.rst

.. _`error handling`:

**************
Error Handling
**************

Basic traps
===========

.. aside::

   I confess, as a `yoof <https://en.wiktionary.org/wiki/yoof>`_, I
   was unaccountably confused by ``trap``.  *It's a trap!*  Wait, what?

   Obviously(?) I'm over it now though I sometimes am left pondering
   about the word "door".  Where did *that* come from?

I've noted before that the error handling is a spin on
:ref-author:`Queinnec`'s :cite:`LiSP`'s ``monitor`` extended to take
one or more *conditions* and called ``trap``.

Ostensibly, as the code runs it picks up a series of ``trap``\ s, each
interested in their own set of conditions.  Each trap has a link to
its parent handler with the bottom-most trap linking to itself.
(Which we assume is coded well enough to cope with any error!)

.. graphviz::

   digraph lower {
       node [ shape=box; fontsize=12; ]

       t4 [label="trap *this*"];
       t3 [label="trap *that*"];
       t2 [label="trap *next*"];
       t1 [label="trap *...*"];
       t0 [label="trap *reset*"];

       t4 -> t3;
       t3 -> t2;
       t2 -> t1;
       t1 -> t0;
       t0 -> t0;
   }

When a condition arises, we can trot through the set of established
traps and look to run the handler associated with the first one
prepared to handle this kind of condition and then we play a little
trick.  In case this handler itself fails (or decides that, in fact,
it can't handle the condition and wants to `pass the buck
<https://en.wiktionary.org/wiki/pass_the_buck>`_) we run the handler
in the context of its own parent handler.

To make that work we *copy* the parent handler and stick it on the top
of the stack.  So, suppose a ``*that*`` condition occurred.  We would
skip ``*this*`` (assuming it wasn't an ancestor of ``*that*``!), find
the trap for ``*that*`` and put a copy of ``*that*``'s parent,
``*next*``, on the top of the stack:

.. graphviz::

   digraph lower {
       node [ shape=box; fontsize=12; ]

       t5 [label="trap *next* (copy)"];
       t4 [label="trap *this*"];
       t3 [label="trap *that* (handler being run)"];
       t2 [label="trap *next*"];
       t1 [label="trap *...*"];
       t0 [label="trap *reset*"];

       t5 -> t1;
       t4 -> t3;
       t3 -> t2;
       t2 -> t1;
       t1 -> t0;
       t0 -> t0;

       {
       edge[style=invis];
       t5 -> t4;
       }

   }

Now, should this handler raise a condition itself (by design or foul
play) then the standard mechanism for finding a handler will start at
the top of the stack and find... this trap's parent, which as we
copied it, points at its own parent skipping all the unwanted (and
doomed to fail?) traps set up in the meanwhile.

In Extremis
-----------

Sadly, it's not traps all the way down.  Almost but not quite.
Something needs to do some *serious* error handling when all else
fails.

The last (first?) two traps (automatically installed) are less
inclined to play nicely and will attempt to reset the system.  That
doesn't mean they will always succeed, mind!

In the first instance, the *restart condition handler* will invoke a
continuation quietly wrapped around every top level form.  Nominally
called ``ABORT`` in the code generator and VM, its continuation is the
next top level form.

This is prone to issues with (global) state where we've crashed out of
some complicated processing leaving (global) variables in an unhelpful
state.

In the second instance, the *reset condition handler* should be trying
to restart the VM in a safe manner, hence the name, except that I'm
not particularly clear on what safe state is.  Arguably, there are
only two known safe states, the start of the program and the end.  And
given that we ran through the program and got into a mess that only
leaves us with the end of the program as a safe state, hence the reset
condition handler invokes the "exit" continuation.

To be fair it could actually just call :manpage:`exit(3)` but I want
it to stagger onto attempting to shutting the program down (cleanly).
Part of that will be to drop out some VM state (if requested) which is
useful for debugging.

That said, the internal state is quite often messed up -- not helped
by my debugging trying to print out values that have been garbage
collected -- and so it quite often fails.  More work required.

.. rst-class:: center

\*

Neither of these fallback trap handlers satisfy one of my own
favourite shell settings, *exit on error*, though.  As :lname:`Idio`
matures, exit on error will migrate towards the fore!

Implementation
--------------

Pushing extra *stuff* on the stack as we process traps needs some
careful management.  We can't just leave it there for the next guy
along to trip over.

First of all, what do we know has happened?  Well, we were called from
somewhere so we need to remember where to go back to, some *PC*.  We
ought to save the current machine state (although as we are notionally
running *in place of* the code raising the condition then it's a bit
moot.  Plus, of course, we're pushing another trap on the stack.

All things being well, then, the "repair" should be to pop the trap
off the stack, restore the machine state and return to said *PC*.
What's more, we'll be doing that for *every* invocation of a trap
handler.

Well, the same thing being run every time has the whiff of a snippet
of code in the :ref:`prologue` and so that's what we'll have.  We'll
call it "condition handler return" or CHR.

Finally, we need to convince the trap handler code to run through our
CHR snippet.  Of course, all bits of handler code will call ``RETURN``
to whatever is on the top of the stack.  So the obvious thing is for
us to push the *PC* of the CHR code on the stack.

So, for the following bit of code:

.. code-block:: idio

   trap ^rt-divide-by-zero-error (function (c) {
				    ;; {HERE}
				    3
   }) {
     display* "1: 1 / 0 =" (1 / 0)
   }

then at the point ``{HERE}`` we'll have pushed the *next* trap onto
the stack (in case we mess up) as well as the *PC* for where we were
called from:

.. graphviz::

   digraph lower {
       graph [ rankdir="LR" ];
       node [ shape=box; fontsize=12; ]

       body [
		shape="record"
		label="(body)|<f0> ...|<f1>1 / 0|<f2>..."
       ];

       handler [
		shape="record"
		label="(handler)|<f0> ;; HERE|<f1>3|<f2>RETURN"
       ];

       stack [
		shape="record"
		label="(stack)|<f0>*CHR* PC|<f1>TRAP (next is ?)|<f2>STATE|<f3>*body* PC|..."
       ];

       CHR [
		shape="record"
		label="(prologue)|...|<f0> POP-TRAP|<f1>RESTORE-STATE|<f2>RETURN|..."
       ];

       body:f1 -> handler:f0
       handler:f2 -> stack:f0 [style="dashed"]
       stack:f0 -> CHR:f0
       CHR:f2 -> stack:f3 [style="dashed"]
       stack:f3 -> body:f2
   }

.. aside::

   And I can't control `Graphviz <https://graphviz.org/>`_.

(Obviously, the handler doesn't call anything on the stack, I'm just
trying to represent the linkages between bits of code and the *PC*
they jump to.)

The trap information on the stack has:

* the condition the trap will handle

* the trap handler function

* the (stack position) of the *next* handler

Hence, in this case, we don't know what the next handler is as it's
not in this snippet.  Quite possibly one of the default handlers.  The
point being, though, that whatever this next trap is, it has been
pushed onto the stack in readiness for this handler going awry.

Operational Behaviour
^^^^^^^^^^^^^^^^^^^^^

The expression ``1 / 0`` will get a little way into some piece of code
before something realises that the denominator is zero.  That code
will raise an ``^rt-divide-by-zero-error`` condition and call
``idio_raise_condition()`` in :file:`vm.c`.

That code will rummage about on the stack looking down the list of
traps on the stack looking for one which will handle
``^rt-divide-by-zero-error`` or one of its ancestors.

Having found such a trap it will then push onto the stack:

* the current *PC* -- ie. where to return to

* the program state

* the trap details for this (just found) trap's parent so that if this
  handler fails and the code circles around,
  ``idio_raise_condition()`` will invoke its parent (and not itself).

* the *PC* for CHR in the prologue

We then run the handler.

In this case the handler sets *val* to ``3`` and ends, ie. calls
``RETURN``.

``RETURN`` finds the *PC* for CHR on the top of the stack which will
pop a trap off the stack (our handler's parent), restore the program
state and call ``RETURN``.

This ``RETURN`` (in CHR) will find the *PC* for the original body code
and the invocation of ``1 / 0`` will return with the value... ``3``.

OK, OK, possibly not the best way to handle a divide by zero error!

Double-stacking
---------------

:socrates:`What if my handler reverts to another handler?` Whelp,
steady on.

.. code-block:: idio

   trap ^idio-error (function (c) {
		       ;; {HERE}
		       3
   }) {
     trap ^rt-divide-by-zero-error (function (c) {
				      raise c
     }) {
       display* "1: 1 / 0 =" (1 / 0)
     }
   }

Now we'll have had two (protecting?) traps pushed onto the stack.  In
invoking the inner ``^rt-divide-by-zero-error`` handler,
``idio_raise_condition()`` will have pushed the next trap handler onto
the stack (*irrespective* of whether it handles
``^rt-divide-by-zero-error`` because we don't know what the handler is
going to do!).

As we can see, that handler passes the buck and
``idio_raise_condition()`` finds that, as it happens, the next trap
handler does handle ``^rt-divide-by-zero-error`` (as ``^idio-error``
is an ancestor of all :lname:`Idio` errors) and so it has to push the
parent of *that* handler onto the stack.  Again, like before, we don't
know who that parent is.

That gives us the slightly messy graph:

.. graphviz::

   digraph lower {
       graph [ rankdir="LR" ];
       node [ shape=box; fontsize=12; ]

       body [
		shape="record"
		label="(body)|<f0> ...|<f1>1 / 0|<f2>..."
       ];

       handler_c1 [
		shape="record"
		label="(handler c1)|<f0> raise condition|<f21>RETURN"
       ];

       handler_c2 [
		shape="record"
		label="(handler c2)|<f0> ;; HERE|<f1>3|<f2>RETURN"
       ];

       stack [
		shape="record"
		label="(stack)|<f0>*CHR* PC|<f1>TRAP (next is ?)|<f2>STATE|<f3>*handler_c1* PC|<f4> *CHR* PC|<f5>TRAP (next is ^idio-error)|<f6>STATE|<f7>*body* PC|..."
       ];

       CHR [
		shape="record"
		label="(prologue)|...|<f0> POP-TRAP|<f1>RESTORE-STATE|<f2>RETURN|..."
       ];

       body:f1 -> handler_c1:f0
       handler_c1:f0 -> handler_c2:f0
       handler_c2:f2 -> stack:f0 [style="dashed"]
       stack:f0 -> CHR:f0
       CHR:f2 -> stack:f3 [style="dashed"]
       stack:f3 -> handler_c1:f21

       handler_c1:f21 -> stack:f4 [color="blue";style="dashed"]
       stack:f4 -> CHR:f0 [color="blue"]
       CHR:f2 -> stack:f7 [color="blue";style="dashed"]
       stack:f7 -> body:f2 [color="blue"]
   }

Where, ultimately, we bounce through the two handlers returning ``3``.

.. note::

   It's important to note here that ``raise`` returned with a value.

   An awful lot of the time, errors are unexpected and the engine will
   eventually engage the default handlers which will try to cope.

   Indeed, *we* might go further and only be intending to use
   ``raise`` when we can't cope and want the main engine to bail out
   for us.  In this case we're not expecting ``raise`` to return.  But
   as you can see it is entirely possible for it to return which may
   very well come as "a surprise" to some.

   The same problem exists in the underlying :lname:`C` code.

reraise
-------

Handling conditions like that works a treat although there's a corner
case (isn't there always?)  where you might want to deliberately throw
up a different condition in response to a first and allow all of the
user-created traps to kick in.

My go-to example (seeing as I had to implement it for this) is
handling child processes exiting.  We, being the parent, will get an
operating system signal, ``SIGCHLD``.  We don't want the user to be
handling ``SIGCHLD`` (as *we're* the shell and it becomes very messy,
very quickly) but we do want to alert them *if the process failed*
that their (child) process has failed -- if it exits with ``0`` then
all is well and we don't need to say anything.  So, when a child
process fails we want to raise a "command status error" condition.

Now, the problem lies in that the (default) job control ``SIGCHLD``
handler is way down the list of traps.  In fact it's not much above
``*reset*`` in the graphs, at the top of the page, which means we've
bypassed all of the user-created traps which are the ones looking to
handle ``^rt-command-status-error``.  *Oops!*

So, rather than ``raise`` the "rcse" condition, we ``reraise`` it
which, rather than look for the *first* trap in the stack, looks for
the trap with the highest "next" pointer.  Given that all traps have a
next pointer pointing further down the stack then the one with the
highest next pointer must be at the top of the (original) trap tree.

Advanced traps
==============

In the previous chapter we went to a lot of trouble (possibly far too
much) to investigate and handle conditions and then delimited
conditions and dance around the problem of unwinding.  With traps we
can get into a similar position.

trap-return
-----------

Most people who have used exceptions are used to the
``try``/``except`` form where the extant state of the machine is
trancated when the handler kicks in:

.. code-block:: python

   try:
       something_risky()
   except ThisException:
       ...
   except ThatException:
       ...

where we aren't *handling* the exception in any way, we are simply
acknowledging that the exception occurred, somewhere, and maybe we'll
get a stringified clue in the exception object.


.. aside::

   and, thankfully, ``1 / 0`` hasn't returned ``3`` this time!

Which is perfectly fine!  Let's make that clear.  The code "dun
goofed" and we're still running, able to acknowledge the exception and
move on.

It is a paradigm for handling exceptions, it's one people are used to.
Can we do the same?  Just to re-iterate, we want ``trap-return`` to
continue processing at the continuation of the ``trap``.

In the first instance, a trap's handler can only do one of two things:

#. return a value

#. raise a condition (quite often the one we were run to handle!)

Neither of those seem to give us much leeway to truncate the state of
the machine.

Of course, the whole of the last chapter was about (slightly bonkers)
ways to jump around in the code.  We should be able to do something
there.

We can, of course, but it requires a bit of tinkering.  The obvious
and main thrust is going to be to rewrite ``trap`` to use a delimited
continuation with ``prompt-at``.

But wait!  ``trap`` (at the time of writing) was a special form and we
saw how those are not amenable to...er, anything.

OK, job #1, rename the special form ``%trap`` and write a ``trap``
template that is a simple wrapper around ``%trap``.  Done!

Next job, make the simple wrapper use ``prompt-at`` and a standard
``trap-return`` prompt tag.  With that, introduce a new expression,
``trap-return`` which can use that prompt-tag.  OK:

.. code-block:: idio
   :caption: :file:`delim-control.idio`

   trap-return-tag := make-prompt-tag 'trap-return
   (define-syntax trap-return
     (syntax-rules ()
       ((trap-return)   (trap-return (void)))
       ((trap-return v) (control-at trap-return-tag k v))))

   (define-syntax trap
     (syntax-rules ()
      ((trap conds handler body ...)  {
	prompt-at trap-return-tag {
	  %trap conds handler {
	    (begin body ...)
	  }
	}
      })))

and now we can write:

.. code-block:: idio

   trap ^rt-divide-by-zero-error (function (c) {
				    display "trapping ^rt-divide-by-zero-error"
				    trap-return 3
   }) {
     display* "1: 1 / 0 =" (1 / 0)
   }
   display* "done"

which gets us:

.. code-block:: console

   trapping ^rt-divide-by-zero-error
   done

which seems promising enough until we introduce our old friend...

unwind-protect
--------------

*\*shakes fist\**

.. sidebox::

   At this point I should note that I'm using ``display*`` as it is
   just about the lowest level primitive for printing.  ``printf``
   (and friends) use ``unwind-protect`` internally so it becomes
   "quite" confusing to figure out what's happening.

Now, this is a bit subtle (and took me a while to spot) so I've added
a few more helpful prints.

.. code-block:: idio

   trap ^rt-divide-by-zero-error (function (c) {
				    display* "trapping ^rt-divide-by-zero-error"
				    trap-return 3
   }) {
     unwind-protect {
       display* "1: 1 / 0 =" (1 / 0)
       display* "not run"
     } {
       display* "cleaning up!"
     }
     display* "post unwind"
   }
   display* "done"

from which we get:

.. code-block:: console

   trapping ^rt-divide-by-zero-error
   cleaning up!
   post unwind
   done

which is mostly what we'd expect apart from the ``post unwind`` bit.
What is our nominal ``trap-return`` doing continuing to run the body
of the trap?

Here's the problem with ``dynamic-wind``: ultimately, when it is run,
it captures its own continuation (here, the ``post unwind`` expression
and, essentially, the rest of the trap's body) and then mixes it up
with the cleanup code thunk.

When we invoke ``trap-return`` which, as a thin shim around
``control-at``, will start unwinding holes.  The holes (and their
continuations) are for the cleanup code and ``unwind-protect``'s
continuation.  This means we'll have the cleanup code run which will
*automatically* (and out of our control) run the continuation of
``unwind-protect``.

*Bah!*  That's a bit annoying.

We've a couple of choices.  We could simply throw all the intermediary
holes between us and our ``trap-return`` prompt-tag away.  Which is an
option although it seems a bit...unfriendly.

Otherwise we could try to see if we can pick apart these holes and
just run the cleanup clauses.

Hmm, in the first instance we can't actually tell them apart as
they're all (default tagged) ``reset``/``shift`` tuples.

What we really want to do is capture the continuation that is the
cleanup clause in order that we can find it and call it.  For that we
need to revisit ``dyn-wind-yield``.

dynamic-wind III
^^^^^^^^^^^^^^^^

Here, we're creating an ``unwind-protect`` prompt-tag and jiggling
``dyn-wind-yield`` around a bit so that the ``after-thunk`` can be
invoked in a separate clause:

.. code-block:: idio

   unwind-protect-tag := make-prompt-tag 'unwind-protect

   define (dyn-wind-yield before-thunk thunk after-thunk) {
     dwy-loop :+ function (th) {
		   prompt-at unwind-protect-tag {
		     (function (res) {
			(after-thunk)
			res
		     }) (control-at unwind-protect-tag dwy-k {
		       (before-thunk)
		       res := (th)
		       dwy-k res
		       (try-yield res
				  (r r)				; return the result
				  (v k {
				    reenter := yield v
				    dwy-loop (function () {
						k reenter
				    })
				  }))
		     })
		   }
     }

     dwy-loop (function () {
		 reset (thunk)
     })
   }

   dynamic-wind := dyn-wind-yield

There's a couple of things hiding in there:

* in order that we can do more than the most trivial operation in the
  unwind clause we need to do the :ref:`closed function trick <closed
  function trick>` we mentioned previously with the ``control-at``
  clause being the argument to it

* in place of invoking ``after-thunk`` in ``control-at``'s body we
  call the continuation, here, ``dwy-k``, to do it for us.

  The argument we're passing is the result of ``(th)`` (ie. the
  original ``(thunk)``) thus allowing the unwinding clause to return
  it (or something else, if called directly).

We're not done yet, though.  Every ``unwind-protect`` expression is
going to drop two holes onto the list: a ``default-reset`` tagged
hole and an ``unwind-protect`` tagged hole.

:socrates:`So we call the continuation in the unwind-protect tagged
hole, right?` No, where did you get that idea from?

We have to remind ourselves of the holes and continuations being
created.  ``reset`` will create a hole, tagged with ``default-reset``
and with a continuation of :samp:`{[outer-k]}`, that of ``reset``
itself.

``reset`` then runs ``(thunk)``, its own body.

In the case of our improved ``dyn-wind-yield``, above, that body has a
``prompt-at unwind-protect`` with a body of a closed function
expression with an argument that is the ``control-at unwind-protect``
expression.  So the hole that is being created there is tagged with
``unwind-protect`` and whose continuation is the closed function
expression.

But wait.  That *continuation* (pointing at the closed function
expression) is not the substance of closed function expression but
merely a future intention.  The substance of the closed function
expression is still embedded in that first hole, tagged
``default-reset`` with a continuation of after the ``reset``, itself
embedded in a thunk.

Where does that leave us?  Confused for a start, if you're me!  The
upshot is, though, that our holes doing things are (arguably)
mis-labelled.  The one tagged ``unwind-protect`` contains the code for
the ``before-thunk`` and ``th``/``thunk`` and the hole, rather
generically, tagged ``default-reset`` has the code for running the
``after-thunk``.

Knowing that we can identify the holes that do the cleanup code we can
now write an alternate unwinding procedure and change ``trap-return``
to use it:

.. code-block:: idio

   define (unwind-to* tag v) {
     holes-prefix := unwind-till-tagged! tag

     loop :+ function (h*) {
	       if (null? h*) #n {
		 if (and (hole-tagged? (ph h*) unwind-protect-tag)
			 (pair? (pt h*))) {
			   vm/hole-push! (pht h*)
			   loop (ptt h*)
		 } {
		   loop (pt h*)
		 }
	       }
     }

     loop (reverse holes-prefix)

     abort-top! v
   }

   (define-syntax trap-return
     (syntax-rules ()
       ((trap-return)   (trap-return (void)))
       ((trap-return v) (unwind-to* trap-return-tag v))))

So ``unwind-to*`` is a bit like the ``control-shift-at*`` code in that
we get all the holes leading up to the one we're interested in,
``trap-return``.  We now have a `shufti
<https://en.wiktionary.org/wiki/shufti>`_ at those holes.

With the holes reversed, when we've had an ``unwind-protect``
expression we'll get one tagged ``unwind-protect`` then one tagged
``default-reset`` where the ``default-reset`` one is the code we want
to run.

So, let's put those ``default-reset``-after-``unwind-protect`` holes
back on the list and let the normal unwinding behaviour kick in.

.. include:: ../../../commit.rst

