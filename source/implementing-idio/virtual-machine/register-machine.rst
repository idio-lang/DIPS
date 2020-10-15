.. include:: ../../global.rst

****************
Register Machine
****************

Calling the virtual machine a register machine might inspire visions
of gnarly modern CPUs with complex machinations.  In practice,
registers are used to stash useful *state*.

More important is the *stack*.  This is used to store temporary values
as we evaluate expressions in forms, ultimately to make function
calls.

Opcodes
=======

The compiled program, the byte code, is going to be a big long list of
*opcodes* and their arguments.  What do these look like?

Just before we get there, we're nominally a *byte code* virtual
machine meaning that we really would like everything to by managed in
terms of bytes.  Which doesn't happen but we'll deal with that.

Nominally, we can have up to 265 opcodes -- I've define 150-odd so
far, several of which aren't used.  Go figure.

These are defined in :file:`vm.h` and look like a rather tedious set
of variations on a theme, here's a sample:

.. code-block:: c
   :caption: vm.h

   #define IDIO_A_SHALLOW_ARGUMENT_REF0		1
   #define IDIO_A_SHALLOW_ARGUMENT_REF1		2
   #define IDIO_A_SHALLOW_ARGUMENT_REF2		3
   #define IDIO_A_SHALLOW_ARGUMENT_REF3		4
   #define IDIO_A_SHALLOW_ARGUMENT_REF		5
   #define IDIO_A_DEEP_ARGUMENT_REF		6

   #define IDIO_A_SHALLOW_ARGUMENT_SET0		10
   #define IDIO_A_SHALLOW_ARGUMENT_SET1		11
   #define IDIO_A_SHALLOW_ARGUMENT_SET2		12
   #define IDIO_A_SHALLOW_ARGUMENT_SET3		13
   #define IDIO_A_SHALLOW_ARGUMENT_SET		14
   #define IDIO_A_DEEP_ARGUMENT_SET		15

   #define IDIO_A_GLOBAL_SYM_REF		20
   #define IDIO_A_CHECKED_GLOBAL_SYM_REF	21
   ...

which they are.

They are implemented in ``idio_vm_run1()`` in :file:`vm.c` which is an
enormous ``switch`` statement where, having read in the byte code
opcode as ``ins`` we can:

.. code-block:: c
   :caption: idio_vm_run1() in :file:`vm.c`

   switch (ins) {
   case IDIO_A_SHALLOW_ARGUMENT_REF0:
       IDIO_VM_RUN_DIS ("SHALLOW-ARGUMENT-REF 0");
       IDIO_THREAD_VAL (thr) = IDIO_FRAME_ARGS (IDIO_THREAD_FRAME (thr), 0);
       break;

where we can optionally drop out some running debug with
``IDIO_VM_RUN_DIS()`` (``DIS`` for disassemble) -- although I don't
recommend doing so as you'll get "quite a lot" of output -- before
updating the *val* register with the value in the 0\ :sup:`th` slot in
the current argument *frame*.

(Yes, there are quite a lot of :lname:`C` helper macros involved!)

Note that the opcode is likely to be referred to with a more
:lname:`Idio` friendly name, ``SHALLOW_ARGUMENT-REF0``.

Some opcodes are more involved than others although the general idea
of resolving everything down to simple opcodes is that they don't
individually do much.

Dedicated Opcodes
-----------------

Some opcodes are dedicated to specific tasks.  We could do some
analysis (I suppose I ought to!) from which we might discern that some
things happen more often than others.

``IDIO_A_SHALLOW_ARGUMENT_REF0`` is a good example of that.  *Most*
functions will access their first argument (not all, of course) and so
we have a dedicated opcode for that rather than the generic
``IDIO_A_SHALLOW_ARGUMENT_REF``:

.. code-block:: c
   :caption: idio_vm_run1() in :file:`vm.c`

   case IDIO_A_SHALLOW_ARGUMENT_REF:
       {
           uint64_t j = idio_vm_fetch_varuint (thr);
	   IDIO_VM_RUN_DIS ("SHALLOW-ARGUMENT-REF %" PRId64 "", j);
	   IDIO_THREAD_VAL (thr) = IDIO_FRAME_ARGS (IDIO_THREAD_FRAME (thr), j);
       }
       break;

which has to read an integer argument from the byte code thus allowing
it to access the (less often accessed) :samp:`{j}`\ :sup:`th` argument
to the function.

Reading that "varuint" (variable length unsigned integer) is
relatively expensive, slowing the whole flow down, so if there's any
quick wins to be had by dedicating opcodes to specific tasks then we
should consider taking them.

Another kind of dedicated opcode is for a specific function call.  We
use pairs a lot so maybe ``pair?`` will give us a quick win if we
avoid the rigmarole of creating an argument frame for it to be picked
apart not long after to call the primitive function.

.. code-block:: c
   :caption: idio_vm_run1() in :file:`vm.c`

   case IDIO_A_PRIMCALL1_PAIRP:
       {
           IDIO_VM_RUN_DIS ("PRIMITIVE1 pair?");
	   if (idio_isa_pair (IDIO_THREAD_VAL (thr))) {
	       IDIO_THREAD_VAL (thr) = idio_S_true;
	   } else {
	       IDIO_THREAD_VAL (thr) = idio_S_false;
	   }
       }
       break;

*Boom!*  Go straight to the :lname:`C` function.

(I've chopped out some function tracing code for brevity.)

Obviously, in both cases, the code generator and VM need to be in sync
as to the set of dedicated opcodes!

Program Counter
===============

So, the bye compiled program is a big long list of opcodes and their
arguments and to help execute the program we need a program counter,
aka. the "register" *PC*, to keep track of where we're up to.  It's
not really a register as it's an index into a byte array (and not an
``IDIO`` value).

We don't quite start at the beginning and run to the end.  Partly as
we've not actually defined an end.  When we drop off the byte code
array, I guess, but that sounds a little uncontrolled.

.. aside:: `Luxury!  When I were a lad ...
           <http://www.montypython.net/scripts/4york.php>`_

We don't even have the luxury of a start, *per se*, as we're
constantly in "read a bit, compile and run a bit, read a bit, compile
and run a bit" mode.

Stopping
--------

We need to think about stopping, first, as it's a little bit more
complicated than just "falling off the end of the array."

What we really want is a *controlled* exit from the chunk of code
we're about to run.  An obvious way to do that is have an opcode
dedicated to stopping, when we hit that we're OK to "return" to what
ever we were doing before we started running this bit of code.
Probably to read a bit more source code.

So, let's have a ``FINISH`` opcode.

OK, where do we put it?  We could tack it on the end of every bit of
code we generate.  That's OK, but there's a slightly smarter solution,
we could have a fixed bit of byte code, common to everything, with
``FINISH`` in it.  What we need to do is have our snippet of byte code
jump to it.

Here we can take advantage of what we expect every function to do when
we're called it which is to ``RETURN`` to the PC stored on the top of
the stack.

So to make our ``FINISH`` trick work, we need to put the PC of the
``FINISH`` opcode on the top of the stack, and ensure that the bit of
code we're about to run has ``RETURN`` at the end.  All things being
equal, the code should trundle through, pushing values onto the stack
and popping them off again until it gets to the end where it sees
``RETURN`` which will pop the PC of ``FINISH`` off the stack and start
running from there.  The opcode at that place *is* ``FINISH`` (that
was the whole point) and *ta da!* we're done.

Prologue
^^^^^^^^

Now, that might seem like a whole load of jumping around for nothing
but it turns out that a small collection of well-defined instructions
in well-known places (the start) are very handy for coping with
several situations, not just stopping.

So we have a *prologue* generated just the once, available for all
future byte code sequences to use that encodes standard special case
situations.  Like stopping!

Starting
--------

Starting is a bit easier.  Each time we read in and compile a chunk of
(source) code we'll generate a new bit of byte code to run.  We'll
have added that to our "big long list of byte coded program" and so
our start can just set *PC* to the start of that chunk and let
everything run.

We should have pushed the PC for ``FINISH`` in the prologue onto the
stack and generated the trailing ``RETURN`` for the byte code and we
should come to a controlled halt.

Position Independent Code
-------------------------

*All* the code we're going to generate is going to be forward-looking
and position independent.  That is to say, that there'll be no
absolute references to PCs and *jumps*, in particular, will only be
forwards into the byte stream.

Registers
=========

*val*
-----

"Everything returns a value" was our *cri de cœur* so let's have a
register for that value calling it, uh, *val*.

*val* becomes the action point for virtually everything:

* the access of a value (lexical or free) updates *val* and when we're
  setting a value it is given the value in *val*

* the reference to a constant updates *val*

* conditional statements test the value of *val*

* the result of a function call updates *val*

* many operations (eg. testing arity) check against *val* on the
  assumption that the code has put the number of arguments in *val*

* many dedicated opcodes (eg. ``pair?``) use *val* as an argument then
  set *val* with their result

There are special opcodes to push the value in *val* onto the stack
and to pop the value off the top of the stack into *val*.

You get the picture, *val* is where it's happening.

*reg1* & *reg2*
^^^^^^^^^^^^^^^

There are several dedicated opcodes which take more than one argument
so there are similar stack pop commands to update *reg1* and *reg2*
depending on how many arguments are required.

(Actually, there are no dedicated 3-argument opcodes so *reg2* is
wasting space....)

Arguably, these could have been called *val2* and *val3* or something
else that suggests they are supplementary to *val* and exist for
dedicated function calls.

*stack*
-------

*val* can't do it all.  If we're generating several values on the trot
-- think of passing lots of arguments to a function -- then we need to
stash those values somewhere whilst we calculate the next, commonly a
stack.

Thus the stack represents the current state of the computation -- a
sort of "how far we've got" -- which is what we need to know when we
look to implement continuations.

The stack also becomes a handy place to stash things as computation
progresses.  Transient values such as traps, dynamic and environment
variables, are ideally suited to live on the stack.

*func*
------

The expression in functional position (whether a symbol or an actual
expression) is still something that needs evaluating to get an actual
function value (a closure or a primitive) and we need to store that
value somewhere before we get to one of the function invocation
opcodes.

We could have stored it in *val* -- indeed it would have been there
transiently as part of its evaluation -- but then we'd need somewhere
else to store arguments and it becomes a bit hard to follow when your
function is in *val*.

Obviously there is an opcodes to pop a value off the stack and into
*func*.

*frame*
-------

The idea of a frame of arguments to the current function comes from
:ref-title:`LiSP` (:cite:`LiSP`) although I'm not happy with it.

The basic premise is that as you make a nested set of function calls
(normal behaviour!) then you get a corresponding stack of argument
frames (actually a linked list but who's counting?).  Consider that
:samp:`foo a b` calls :samp:`bar x y` then we have two frames,
:samp:`{a} {b}` and :samp:`{x} {y}` with the values for each of the
arguments supplied.

These are just simple :lname:`C` arrays (they were originally but are
no longer :lname:`Idio` arrays) indexed 0, 1, 2, ... and therefore

* in ``bar`` we can access

  - our own first argument, :samp:`{x}`, as index 0 of the top frame
    on the stack

    This is the ``SHALLOW-ARGUMENT-REF0`` we saw earlier.

  - our own second argument, :samp:`{y}`, as index 1 of the top frame
    on the stack

    This will be ``SHALLOW-ARGUMENT-REF1``.

  - ``foo``'s first argument, :samp:`{a}`, as index 0 of the next
    frame down the stack

    This is now a "deep argument reference", :samp:`DEEP-ARGUMENT-REF
    {1} {0}`, where the first argument, :samp:`{1}`, says go one frame
    backwards and the second argument, :samp:`{0}`, says take the
    first index of that frame.

    Technically, ``SHALLOW-ARGUMENT-REF0`` would be
    :samp:`DEEP-ARGUMENT-REF {0} {0}` but we save encoding two
    integers into the byte code by using a dedicated opcode.

* in ``foo``, before and after the call the ``bar`` we can access

  - our own first argument, :samp:`{a}`, as index 0 of the top frame
    on the stack

    This is the ``SHALLOW-ARGUMENT-REF0`` we saw earlier.

  - our own second argument, :samp:`{b}`, as index 1 of the top frame
    on the stack

    This will be ``SHALLOW-ARGUMENT-REF1``.

  - these are *the same* opcodes as we had in ``bar`` except in
    ``foo`` the top-most frame is our own argument frame -- the
    argument frame for ``bar`` either hasn't existed yet or has been
    removed on return

  - no arguments to ``bar`` exist

You can imagine the mechanics of that as the arguments to each
function call are evaluated then they are pushed onto the stack.  An
argument frame is constructed (and put in *val*) and the evaluated
arguments are popped back off the stack and into the slots of the
argument frame.

.. sidebox::

   A non-committal approach to evaluation order or arguments can lead
   to people exploiting unexpected behaviour from side-effects.  If my
   arguments are constructed from a function call:

   .. code-block:: idio

      foo (g) (g)

   where ``(g)`` returns an incremented number, say, that means on a
   left-to-right evaluation system you'd be calling ``foo 1 2`` and on
   a right-to-left evaluation system you'd be calling ``foo 2 1``.

   Without committing either way, evaluation order probably *should*
   include the evaluation of functional position too.

It doesn't matter whether they are evaluated left to right, right to
left or in some more complicated order so long as they are plucked
back off the stack and into the argument frame in the correct order.

However, there is almost certainly something to be said for
prescribing an evaluation order if only to assert some consistency.  I
say... *left to right*.  There, done!

The generated code is going to look something like:

* evaluate the expression in functional position (here, the symbol
  ``foo``) and push the value :samp:`{func}` onto the stack

* iterate over the arguments:

  * evaluate the expression corresponding to argument 1 and push the
    value :samp:`{a}` onto the stack

  * evaluate the expression corresponding to argument 2 and push the
    value :samp:`{b}` onto the stack

  We've run out of arguments, now, so know we have two.

      That's not quite how it works -- as improper lists, ie. varargs
      need to be handled -- but broadly the code is organic for fixed
      formal parameters.

      This recursive "functional" flow is somewhat unnatural to the
      imperative style most of us are used to!  

* create an argument frame of size 2 (the above two arguments) --
  leaving it in *val*

* iterate over the stacked argument values:
  
  * pop the top argument off the stack and into index 1 of the frame
    *in val*

  * pop the top argument off the stack and into index 0 of the frame
    *in val*

* pop the function value off the stack and into *func*

* invoke a function call!

Of course, we don't stop there, in order to make the call to ``bar``
we need to repeat the above process for each of ``bar``'s arguments.

But wait, what if, like the sidebox, the arguments are function calls
themselves?  For example, :samp:`+ 1 (2 * 3)`.  Why, we just get
recursive!

A Flat Frame
^^^^^^^^^^^^

For some reason this linked list of frames sits uneasily with me
although I've not considered too deeply an alternative.

I don't like the constant creation and (eventual) destruction of so
many frames (knowing that every ``let`` has been reworked into a
function call).  Starting up and shutting down immediately will
generate tens of thousands of frames!

I'm thinking that the frame should be a single (dynamic) array that is
extended with each function call and left unused when a call returns.
The ``SHALLOW-ARGUMENT-REF0`` opcodes could then be replaced with a
:samp:`ARGUMENT-REF{i}` for the :samp:`{i}`\ :sup:`th` value from the
end.  For some :samp:`{i}` there is a dedicated opcode otherwise a
generic ``ARGUMENT-REF`` which requires a single integer index.

Eventually, the function call hierarchy will unwind to the "top" (with
a call to ``FINISH``) and the frame can be garbage collected.

Dynamic Registers
=================

There are several values and behaviours that have a dynamic extent.
When we create a trap handler, say, we expect to run for the lifetime
of the encapsulated code and if another trap handler is registered
within that encapsulated code then it is the first port of call and
then us.

This becomes a chain of handlers and the obvious place for them to
live is on the stack with opcodes embedded in the byte code to push
them onto the stack and pop them off as the encapsulated code comes to
be run and then completes.

Of course, something needs to point to the start of the chain, the
dynamic registers: *dynamic*, *environ* and *trap*.

Albeit they actually called ``dynamic_sp``, ``environ_sp`` and
``trap_sp`` in :lname:`C`.

Caches
======

As noted previously, there are some values that we keep handy in case
someone asks for them.

Handles
-------

Following :lname:`Scheme` we retain the concept of the current input,
output and error handles -- rather than the Unix assumption of (file
descriptors) 0, 1 and 2.

Module
------

We retain the idea of the current module.  This is the result of the
last instruction to change module.

Environment
-----------

We also retain the concept of the current environment for evaluating
symbols in.  This is a little more squirrelly.

Normally the environment will follow the module.  However, when we
call a function we switch to the environment that the function was
defined in.  This (replacement value) gets used when we have to
resolve a symbol in the function and now points at the environment
(module!) from when it was defined.

Normally symbols will have been resolved to a value index (which
thereafter needs no concept of an environment) but where there was a
forward lookup in a function then we'll be dealing with a symbol index
and we need to ask questions of the current environment -- or, rather,
the environment the function was defined in.

Expression
----------

Experimental

For help with debugging we should have noted the source code
expression (including source handle and line number) and be updating
this value as we run through the code.

A single small expression in the source can balloon out to hundreds of
lines of code if it was a template which does leave some mysterious
debug.

Continuation
============

To help with the implementation of continuations we use :lname:`C`'s
:manpage:`sigsetjmp(3)` and friends.  For that we need somewhere to
store the ``sigjmp_buf``.


.. include:: ../../commit.rst

