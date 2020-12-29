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

Manipulating the stack becomes like an industrialised form of `Towers
of Hanoi <https://en.wikipedia.org/wiki/Tower_of_Hanoi>`_ so you might
want to get your game face on.

Opcodes
=======

The compiled program, the byte code, is going to be a big long list of
*opcodes* and their arguments.  What do these look like?

Just before we get there, we're nominally a *byte code* virtual
machine, meaning that we really would like everything to by managed in
terms of bytes.  Which doesn't happen for most opcode arguments (as
opposed to :lname:`Idio` arguments) but we'll deal with that.

An opcode describes an operation, often implying the use of one or
more registers, usually in a very simplistic way:

* push the value in the *val* register onto the *stack*

* pop the top-most value on the *stack* into the *func* register

* put the value of constant #\ :samp:`{n}` in the *val* register

  This :samp:`{n}` is an opcode argument where we sped up the run-time
  by only encoding an integer in the byte code instead of the constant
  itself.  We subsequently have to access the constant from an array.

You can get and set top-level variables (between the *val* register
and an array of values), call functions (which leave a value in the
*val* register) and so on.

The byte-nature breaks down if we pass an opcode argument bigger
than 255.  That's pretty common as we pass constant and value table
indices around all the time.  I've followed in the path of SQLite_ and
used `its variable length unsigned integer
<https://sqlite.org/src4/doc/trunk/www/varint.wiki>`_ encoding
algorithm.

That algorithm means one byte can encode up to 240, two bytes up to
2287 and three bytes can encode up to 67823 and thereafter the
encoding is one byte worse than a regular encoding: four bytes
represent up to 2\ :sup:`24`\ -1, five bytes up to 2\ :sup:`32`\ -1
and so on up to nine bytes for 2\ :sup:`64`\ -1.

That's hardly brilliant for small values but, crucially, it is
generic.  We don't need extra opcodes identifying the kind of integer
encoded next ("small", "medium" and "large").  We also don't *always*
use eight bytes to encode single digit integers.

.. rst-class:: center

\*

What we really want is a small-number friendly system -- I'll confess
I stopped thinking too hard when I found *something* that was generic.

.. aside::

   Have I typed all of those in?  Yikes!

You might ask how big the integers get that we need to encode?  Well,
startup uses a couple of thousand constants (on the cusp of tripping
into the three byte encoding!) and the test suite uses about 18,000
constants.  That seems like quite a lot but, maybe, not so much for a
large program.

.. aside::

   Far fewer than I thought!

Jumps in the byte code (``GOTO``\ s) number around 2800 in the test
suite with around 350 "long GOTOs" (over 240 bytes) with the largest a
nearly 6000 byte jump.

I want to avoid the use of a fixed width system, it feels wrong and
artificially constraining let alone mostly inefficient.  Who wants to
discover that you're limited to 65536 constants or values in your
program?  Four billion sounds plenty but is it?  Well, for one thing
it *is* the limit on a 32-bit machine.  Is it a reasonable limit on a
64-bit machine?  (Yes, probably, though there'll always be *that guy*.
Don't be that guy!)

It still feels wrong to be encoding integers in the low tens of
thousands (and the low thousands for most uses) in four bytes.  We've
no control over the byte alignment in the byte code stream so it's not
as if there's any easy way to reconstruct the original 32 bits, you
have to read a byte, shift, read a byte, shift and so on.

Of note, here, is that :lname:`Idio` integers, ``123``, are *not*
encoded in the byte code.  They are (and should be!) regarded as
constants in the :lname:`Idio` program and treated in the same way as
a string, ``"hello"``.  That is, a slot is found for them in the
constants array and all future references to them are made using
indexes into that array.

I wonder if something along the lines of the UTF-8 encoding system
might work?  Ignoring the Unicode constraints, as a run-length
encoding system it appears fairly open-ended, see
`https://en.wikipedia.org/wiki/UTF-8#FSS-UTF
<https://en.wikipedia.org/wiki/UTF-8#FSS-UTF>`_.

.. csv-table::
   :widths: 10, 10, 10, 10
   :header: bytes, first, last, acc. count

   1, 0x0, 0x7f, 128
   2, 0x80, 0x7ff, 2048
   3, 0x800, 0xffff, 65536
   4, 0x10000, 0x1fffff, 2097152
   5, 0x200000, 0x3ffffff, 67108864
   6, 0x4000000, 0x7fffffff, 2147483648

Answer: Yes but it is worse than the SQLite scheme.

.. rst-class:: center

\*

There is a downside in that the varuint system only encodes unsigned
numbers.  So we do need a "negative number" opcode whose job is to
read the upcoming positive number and, uh, negate it.

Nominally, we can have up to 256 opcodes -- I've define 150-odd so
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
   case IDIO_A_SHALLOW_ARGUMENT_REF1:
       ...
   }

where we can optionally drop out some running debug with
``IDIO_VM_RUN_DIS()`` (``DIS`` for disassemble) -- although I don't
recommend doing so as you'll get "quite a lot" of output -- before
updating the *val* register with the value in the 0\ :sup:`th` slot in
the current argument *frame*.

(Yes, there are quite a lot of :lname:`C` helper macros involved!)

Note that the opcode is likely to be referred to with a more
:lname:`Idio` friendly name, ``SHALLOW-ARGUMENT-REF0``.

Some opcodes are more involved than others although the general idea
of resolving everything down to simple opcodes is that they don't
individually do much.

Dedicated Opcodes
-----------------

The evaluator will determine a general sort of functional request,
:samp:`ARGUMENT-REF {i} {j}`, say, to access the :samp:`{j}`\
:sup:`th` argument in the :samp:`{i}`\ :sup:`th` frame back.

In fact, even the evaluator, here, will differentiate between a
:samp:`SHALLOW-ARGUMENT-REF {j}` (for a zero :samp:`{i}`) and a
:samp:`DEEP-ARGUMENT-REF {i} {j}` (for a non-zero :samp:`{i}`).

.. sidebox::

   :ref-title:`LiSP` gets around this information in two places
   "difficulty" by a) being entirely written in :lname:`Scheme` and
   therefore b) is able to call upon more exotic macros through
   ``syntax-rules`` etc. which allow the simultaneous definition of
   the code generator, VM handler (and disassembler).

   Not an option for us dullards writing the parts in :lname:`C`.

The code generator is in cahoots with the VM (not really ideal as the
information about what is possible is in two places) and can decide to
use some specialised opcodes for specific tasks.  We could do some
analysis (I suppose I ought to!) from which we might discern that some
things happen more often than others and could do with being
specialised.

A specialised opcode means that the argument is implied by the opcode
itself rather than being passed in the byte code (and having to be
decoded).

``IDIO_A_SHALLOW_ARGUMENT_REF0``, above, is a good example of that.
*Most* functions will access their first argument (not all, of course)
and so we have a dedicated opcode for that rather than the generic
:samp:`SHALLOW-ARGUMENT-REF {j}` with :samp:`{j}` being zero:

.. code-block:: c
   :caption: idio_vm_run1() in :file:`vm.c`

   case IDIO_A_SHALLOW_ARGUMENT_REF:
       {
           uint64_t j = idio_vm_fetch_varuint (thr);
	   IDIO_VM_RUN_DIS ("SHALLOW-ARGUMENT-REF %" PRId64 "", j);
	   IDIO_THREAD_VAL (thr) = IDIO_FRAME_ARGS (IDIO_THREAD_FRAME (thr), j);
       }
       break;

which has to decode a (variable length) integer argument from the byte
code thus allowing it to access the (less often accessed) :samp:`{j}`\
:sup:`th` argument to the function.

Reading that "varuint" is relatively expensive, slowing the whole flow
down, so if there's any quick wins to be had by dedicating opcodes to
specific tasks then we should consider taking them.

Just to get a feel for those numbers, the current test suite produces
the following numbers (run a debug build with ``--vm-reports`` and
look in :file:`vm-perf.log`):

.. csv-table::
   :widths: auto

   instruction, count, cnt%, time, time%, ns/cal
   SHALLOW-ARGUMENT-REF0, 969776, 5.6, 0.027938377, 0.0, 28
   SHALLOW-ARGUMENT-REF1, 397200, 2.3, 0.011514698, 0.0, 28
   SHALLOW-ARGUMENT-REF2, 92822, 0.5, 0.002792880, 0.0, 30
   SHALLOW-ARGUMENT-REF3, 97571, 0.6, 0.002966939, 0.0, 30
   SHALLOW-ARGUMENT-REF, 93391, 0.5, 0.004358618, 0.0, 46
   DEEP-ARGUMENT-REF, 546688, 3.2, 0.050494580, 0.1, 92

Here you can see that ``SHALLOW-ARGUMENT-REF0`` accounts for 44% of
all argument references.  Given that on this machine it takes 28ns
versus the 46ns of a generic :samp:`SHALLOW-ARGUMENT-REF {j}` call
(let alone the 92ns for the generic :samp:`DEEP-ARGUMENT-REF {i} {j}`
call) specializing the opcode is a sensible move.  The cumulative
0.028s those almost-a-million instructions took could have been over
three times longer.

OK, maybe we can ignore those as it's a whole heap of nothing.  Except
the equivalent numbers of the "standard unit of computing", the
Raspberry Pi 3B+ are 181ns and 880ns respectively.  Actually, that
really hurts!

.. rst-class:: center

\*

Another kind of dedicated opcode is for a specific (primitive)
function call.  We use pairs a lot so maybe ``pair?`` will give us a
quick win if we avoid the rigmarole of creating an argument frame for
it to be picked apart not long after to call the primitive function.

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

Obviously, in both cases, the code generator and VM need to be in sync
as to the set of dedicated opcodes!

As it happens, I had and then removed these specific primitive
function call opcodes and made all non-varargs primitive calls
half-specialised (half-baked?) with :samp:`PRIMCALL{n}` opcodes for
the number of arguments, :samp:`{n}`, they require.  We only need
encode the value index for the primitive (a *varuint*) in the byte
code.  The arguments are computed and left on the stack (as with all
function calls), then we can pop the arguments off the stack (into
handy registers) and call the primitive directly (which calls the C
function in turn).

So, a couple of steps behind the curve but I think it's OK.

.. aside::

   And :file:`evaluate.idio` couldn't actually test the underlying
   :lname:`C` data structure for a primitive easily anyway but let's
   say it was about the data in three places problem.

   Our little secret.

I partly did this because in writing the :lname:`Idio` version of the
evaluator, :file:`evaluate.idio`, I realised I was now putting the
information about which opcodes were specialised in three places.
That just compounds the problem.

Varargs primitives have to trundle through the whole function call
experience where a frame is created, the arguments are popped off the
stack into the frame, the generic function call mechanism is called
where the (varargs) primitive has to dismember the frame to get hold
of its arguments before calling the primitive directly.

Program Counter
===============

So, the byte compiled program is a big long list of opcodes and their
arguments and to help execute the program we need a program counter,
aka. the "register" *PC*, to keep track of where we're up to.  It's
not really a register as it's an index into a :lname:`C` byte array
(and, unusually, not an ``IDIO`` value).

We don't quite start at the beginning and run to the end.  Partly as
we've not actually defined an end.  When we drop off the byte code
array, I guess, but that sounds a little... uncontrolled.

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
we've called it which is to ``RETURN`` to the PC stored on the top of
the stack.

So to make our ``FINISH`` trick work, we need to put the PC of the
``FINISH`` opcode on the top of the stack, and ensure that the bit of
code we're about to run has ``RETURN`` at the end.  All things being
equal, the code should trundle through, pushing values onto the stack
and popping them off again until it gets to the end where it sees
``RETURN`` which will pop the PC of ``FINISH`` off the stack and start
running from there.  The opcode at that place *is* ``FINISH`` (that
was the whole point) and *ta da!* we're done.

.. rst-class:: center

\*

Eager minds might wonder what happens if the code somehow fails to
remove everything from the stack that it stuck on and we pop the wrong
thing off the stack.

Well, under those circumstances, something has gone wrong.  We're
*reasonably* unlikely to pop something off the stack that looks like a
suitable value for ``RETURN`` -- although it's not impossible --
partly because we have some "stack markers" identifying what's coming
next.  The stack markers are partly there for debugging and partly
there to catch our scenarios like this.

Most unexpected values for ``RETURN`` will result in a VM panic.

I suppose it's not impossible to get a wrong but valid value for
``RETURN`` off the stack and things will stagger along unexpectedly.
I'm not sure it's possible to identify such a situation.

Prologue
^^^^^^^^

Now, that work pushing the PC for ``FINISH`` on the stack and
appending ``RETURN`` to code segments might seem like a whole load of
jumping around for nothing but it turns out that a small collection of
well-defined instructions in well-known places (hint: the start) are
very handy for coping with several situations, not just stopping.

So we have a *prologue* generated just the once, available for all
future byte code sequences to use, that encodes standard special case
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

Running
-------

That brings us to running.  We need something to loop, running
instructions until we ``FINISH``.

OK, step back, re-jig things a little, and:

.. code-block:: c
   :caption: idio_vm_run() in :file:`vm.c`

   for (;;) {
       if (idio_vm_run1 (thr)) {
           ...
       }
   }

.. aside::

   It could just work!

If ``idio_vm_run1()`` returns 1 unless the opcode was ``FINISH`` in
which case it returns 0 then we get our loop.

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

* the last action of a function call is to update *val* (and thus it
  becomes the function's "return" value)

* many operations (eg. testing arity) check against *val* on the
  assumption that the code has put the arguments in a frame in *val*

There are special opcodes to push the value in *val* onto the stack
and to pop the value off the top of the stack into *val*.

You get the picture, *val* is where it's happening.

*reg1* & *reg2*
^^^^^^^^^^^^^^^

The specialised primitive opcodes which take more than one argument
have similar stack popping commands to update *reg1* and *reg2*
depending on how many arguments are required.

(Actually, there are no 3-fixed-argument primitives so *reg2* is
wasting space....)

Arguably, these could have been called *val2* and *val3* or something
else that suggests they are supplementary to *val* and exist for
dedicated function calls.

Closures do not use these registers as all the arguments to a closure
will be in the supplied frame (in *val*).

*stack*
-------

*val* can't do it all.  If we're generating several values on the trot
-- think of passing lots of arguments to a function -- then we need to
stash those values somewhere whilst we calculate the next, commonly a
stack.

``PUSH-VALUE`` and ``POP-VALUE`` transfer values between the stack and
*val*.  For example, the byte code for ``(+ a 1)`` will:

* evaluate ``+`` (here a symbolic reference leaving the value in *val*)

* ``PUSH-VALUE`` *val* onto the stack

* evaluate ``a`` (here a symbolic reference leaving the value in *val*)

* ``PUSH-VALUE`` *val* onto the stack

* evaluate ``1`` (here a specialised constant reference putting the
  value 1 in *val*)

* ``PUSH-VALUE`` *val* onto the stack

More complicated expressions will result in more work but ultimately a
value will be computed and the result left in *val* which will then be
pushed onto the stack.

In this case, the code will continue to:

* ``ALLOCATE-FRAME 3`` (two fixed arguments plus a varargs
  placeholder) leaving a frame in *val*

* ``POP-FRAME 1`` popping the top of the stack (the value 1) into slot #1 of the
  frame in *val*

* ``POP-FRAME 0`` popping the top of the stack (the value of ``a``)
  into slot #0 of the frame in *val*

The stack represents the current state of the computation -- a sort of
"how far we've got" -- which is what we need to know when we look to
implement continuations.

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

We could have stored it in *val* -- indeed it will have been there
transiently as part of its evaluation, see the example above -- but
then we'd need somewhere else to store arguments and it becomes a bit
hard to follow when your function is in *val*.

Obviously there is an opcode to pop a value off the stack and into
*func*.

The example above would have continued:

* ``POP-FUNCTION`` popping the top of the stack (the value of ``+``)
  into *func*

All we've done so far is spread the computed values for ``+``, ``a``
and ``1`` across *func* and the frame in *val*.  We don't invoke the
function yet because we (the VM) don't know if it is a tail-recursive
call or not and therefore whether we need to save the current state.
The next opcodes will determine that.

*frame*
-------

The idea of a frame of arguments to the current function comes from
:ref-title:`LiSP` (:cite:`LiSP`).

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
    integers into the byte code by using a dedicated opcode -- and a
    lot of time (181ns versus 880ns on the standard unit of
    computing).

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

  We've run out of arguments, now, so we know we have two.

      That's not quite how it works -- as improper lists, ie. varargs
      need to be handled -- but broadly the code is elegant for fixed
      formal parameters.

      This recursive "functional" flow is somewhat unnatural to the
      imperative style most of us are used to!  

* create an argument frame of size *three* (the above two arguments
  plus a varargs placeholder) -- leaving it in *val*

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
themselves?  For example, :samp:`+ 1 (* 2 3)`.  Why, we just get
recursive!

In practice, ``+`` and ``1`` are evaluated and pushed onto the stack.
Our third argument is itself an entire expression but we just
methodically plod on.  We evaluate ``*``, ``2`` and ``3`` pushing them
onto the stack (which now has ``+``, ``1``, ``*``, ``2`` and ``3`` on
it).

The function call protocol will pop ``3`` then ``2`` into an argument
frame and ``*`` into *func*.  The function will be invoked (not in
tail position -- an argument can never be in tail position as it is a
sub-element of a wider piece of work) and leave a value, *probably*
``6`` in *val*.

This has now evaluated the second argument to ``+``.  The next action
after evaluating an argument is to push *val* onto the stack.  How
very handy that the function call to ``*`` left the value in *val*!
Our stack now has ``+``, ``1`` and ``6``.

Finally, we can start the function protocol for ``+`` where ``6`` and
``1`` are popped off the stack and into an argument frame, ``+`` is
popped off and into *func* and the function is invoked.  (*Maybe* in
tail-position -- hard to tell from that snippet.)

Dynamic Registers
=================

There are several values and behaviours that have a dynamic extent.
When we create a trap handler, say, we expect to run for the lifetime
of the encapsulated code and if another trap handler is registered
within that encapsulated code then it is the first port of call and
then us.

At the end of the encapsulated code we expect the handler to be
unwound.

This becomes a chain of handlers and the obvious place for them to
live is on the stack with opcodes embedded in the byte code to push
them onto the stack and pop them off as the encapsulated code comes to
be run and then completes.

    The original wording continued:

    Of course, something needs to point to the start of the chain, the
    dynamic registers: *dynamic*, *environ* and *trap*.

    Albeit they actually called ``dynamic_sp``, ``environ_sp`` and
    ``trap_sp`` in :lname:`C`.

In the early versions of :lname:`Idio` I added these dynamic registers
-- partly because there's a suggestion about them in :ref-title:`LiSP`
-- but there's a cost.  Any (non-tail-recursive) function call needs
to preserve these dynamic registers as well.

That might not seem a bad thing but there's orders of magnitude more
function calls than there are traps let alone dynamic or environ
variables.  That's an awful lot of pushing onto and popping off the
stack for no return.

So the code now reverts to the original :ref-title:`LiSP` mechanism of
placing the traps/variables onto the stack as normal and when it comes
time to look for a trap/handler we search down the stack for the
appropriate stack marker.

That doesn't seem like *Art* but the stack markers are unique and so
long as no-one can trample on our stack then we should be safe.  Of
course, if, like anything else, someone tramples on our stack then all
bets are off.

In the case of traps we can run "in the context of the next handler"
by pushing the next handler (and its own next handler) on the top of
the stack.  Therefore, if required, it is now the handler on the top
of the stack and still points at its own next handler in turn (beyond
the original top-of-stack handler).

This mechanism also gives an ability to revert handlers mid-flow,
``reraise``, by searching the stack for the highest ranking handler,
that is the one with the highest "next" pointer and now pushing *it*
(and its next handler) onto the top of the stack.

Fortunately, it does all get unwound correctly!

Cached Values
=============

As noted previously, there are some values that we keep handy in case
someone asks for them.

Handles
-------

Following :lname:`Scheme` we retain the concept of the current input,
output and error handles -- rather than the Unix assumption of (file
descriptors) 0, 1 and 2.

So long as all the :lname:`Idio` code remembers to ask for the current
input/output/error handle then everything just works.

That's not quite true, today.  Large parts of the error handling and
debug code assume ``stderr`` is good to go.

Module
------

We retain the idea of the current module.  This is the result of the
last instruction to change module.

There is some standard(-ish) but suitably head-scratchingly
complicated :lname:`Idio` code mixed across :file:`module.idio` and
:lname:`call-cc.idio` which handles the automatic reversion of the
sense of the "current module" when the reader hits end of file
(technically, when the ``load`` function completes).

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

