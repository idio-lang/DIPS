.. include:: ../../global.rst

********************
Evaluating Functions
********************

Function Calls
--------------

Function definitions are called function *abstractions* (in the
:lname:`Scheme`\ ly way) and function calls are called function
*applications* -- we're applying the function to some arguments.

Function calls are the far most interesting because there's a
combinatorial explosion of possibilities.  (Just kidding.  There's not
*that* many!)  The main culprits are:

* "closed" or regular applications

  A closed application is one where the expression in function
  position is not a symbol (variable name) but an expression where
  we're creating the function "on the fly":

  .. code-block:: idio
		  
     (function (a b) (+ a b)) 1 2

  will return ``3``.

  Clearly *that* was a pointless example but you may recall the
  discussion around :ref:`scheme-let` which transformed every ``let``
  statement into an "on the fly" function call.  The very sort of
  thing we're now calling a closed application of a function.

  .. sidebox::

     This was true.  Now, thanks to local assignments which can append
     themselves to a function's formal parameters, the ``:=``/``let``
     transformation only occurs for the first assignment in a
     non-function-definition block.

  In other words, every time you use ``:=`` in a block you
  automatically transform the rest of the block into the body of a
  closed function.

* some arguments or no arguments

A function abstraction (definition) cares about whether the formal
parameter list of the function is a proper list, :samp:`({a} {b})`, or
an improper list, :samp:`({a} & {b})`, implying varargs.  We have to
worry about improper lists for a closed application too (as it
contains an anonymous function definition).

In general we're calling the main function application with the
function expression and the argument expressions:
``idio_meaning_application (src, eh, et, ...)``.

Primitive Functions
^^^^^^^^^^^^^^^^^^^

In the first instance, we can look at the expression in functional
position and if it is a symbol then we can look it up.

If that lookup tells us it is a predefined function (ie. a primitive)
then we can do a quick argument check and assuming we're OK call
``idio_meaning_primitive_application()``.  In this function we can
look to use some specialised opcodes.

The idea here, is that we can avoid the general function call
invocation procedure -- which means creating an argument frame and
then in the general function invocation code pulling the arguments off
again -- and instead simply evaluate the arguments, pushing them on
the stack in the normal fashion, then pop them off the stack and call
the (primitive) function directly.

.. sidebox::

   If they're not in sync then I guess you'll find out pretty quick.

This doesn't work for varargs (despite the code currently wasting time
trying to do so) and you need this function and the VM to be in sync
as to which primitives get the special treatment.

If the primitive doesn't get the special treatment then it falls back
into a regular function call.

Regular Function Calls
^^^^^^^^^^^^^^^^^^^^^^

Regular function calls are reasonably straightforward.  We call
``idio_meaning_regular_application (src, fe, aes, ...)`` with the
function expression and argument expressions again.

Careful, though, a regular function call could still have an actual
function call in functional position.  This isn't the case of a closed
function call -- where the expression is *defining* a function
abstraction -- but just a regular function call.  Imagine that you
stashed away a bunch of functions in a lookup table and you're
accessing them now with a function call, :samp:`((hash-ref {my-funcs}
{key}) {arg1} {arg2})`.

It's often a symbol, though, so we just (de-)reference it.

So there's a quick check to establish the right way to figure out the
value in functional position:

.. code-block:: c

       IDIO fm;
       if (idio_isa_symbol (fe)) {
	   fm = idio_meaning_function_reference (fe, fe, nametree, flags, cs, cm);
       } else {
	   fm = idio_meaning (fe, fe, nametree, IDIO_MEANING_NOT_TAILP (flags), cs, cm);
       }

The expression in functional position isn't in tail position, of
course.

Then we need to walk down the list of arguments figuring out the
meaning of each one in turn:

.. code-block:: c

       IDIO ams = idio_meaning_arguments (aes, aes, nametree, idio_list_length (aes), ams_flags, cs, cm);

(The ``ams_flags`` (argument-meaning flags) are "not in tailp.")

``idio_meaning_arguments()`` is just going to recurse down the
argument list in an obvious fashion.  However, it does do it in a very
:lname:`Scheme`\ ly way.

As it walks down the list it calculates the meaning for the current
head of the list and figures out the current slot in the future
*frame* of arguments.

Before it issues it's "store" instruction it recurses on the rest of
the arguments.

That's fine until it reaches zero arguments left at which point it
generates a frame allocation instruction, ``ALLOCATE-FRAME``, with the
original length of the argument list.

Now, as the argument list recursion unwinds, we'll have seen the frame
allocation, then a (reversed) sequence of expression meanings and then
store in a slot instructions.

The argument meanings is now a nested list of instructions which the
code generator knows to walk into in order that it emit the final
opcodes from the inside out.

Each "meaning" argument-instruction list is the tuple:

* ``STORE-ARGUMENT``

* the meaning of this arg

* slot #

* the meaning of the remaining args

from which the code generator will:

* generate the code for this arg (leaving the result in the *val* register)

* ``PUSH-VALUE`` the *val* register onto the stack

* recurse into the other args which will repeat the above until

* we get the ``ALLOCATE-FRAME`` instruction, leaving the frame in the
  *val* register.

Then, as the recursion unwinds, we use the slot argument to
``POP-VALUE`` a value off the stack and into a slot in the frame.
This means that the arguments are evaluated left to right (even if
they're slotted into the frame, right to left).

Finally, we actually get to use the "tailp" flag we've been carefully
avoiding all this time:

.. code-block:: c

       if (IDIO_MEANING_IS_TAILP (flags)) {
	   return IDIO_LIST4 (IDIO_I_TR_REGULAR_CALL, src, fm, ams);
       } else {
	   return IDIO_LIST4 (IDIO_I_REGULAR_CALL, src, fm, ams);
       }

where ``TR`` is "tail-recursive."

Notice we pass in ``src`` which is placed in the *expr* register after
the arguments are evaluated and just before invoking the function.

Closed Function Calls
^^^^^^^^^^^^^^^^^^^^^

Closed function calls are complicated by us requiring to evaluate the
function *abstraction* as well as the immediate function *application*
(exactly as above).

``idio_meaning_closed_application()`` runs through the list of formal
parameters of the function definition and checks that the list of
arguments matches.  Obviously, we handle a varargs situation.

Depending on the varargs situation we'll be handling a
(:lname:`Scheme`-ishly named) "fix(ed arguments) closed application"
or a "dotted (ie. varargs) closed application".

.. _`fixed closed application`:

Fixed Closed Applications
"""""""""""""""""""""""""

If you recall our example:

.. code-block:: idio

   (function (a b) (+ a b)) 1 2

The function expression, ``fe``, is ``(function (a b) (+ a b))`` and
the list of argument expressions, ``aes``, is ``(1 2)``.  From that we
can trivially extract:

.. csv-table::
   :widths: auto
   :align: left

   ``ph fe``, ``function``, a symbol
   ``pt fe``, ``((a b) (+ a b))``
   ``pht fe``, ``(a b)``, formal parameters
   ``ptt fe``, ``((+ a b))``, the body -- a list of one expression

``idio_meaning_fix_closed_application()`` is passed: ``fe``, the
formal parameters, the body and the arguments.

The first thing we do is rewrite or normalise the body.  If you recall
the :ref:`scheme-let` discussion where ``let`` is rewritten into a
closed function then we're looking to do that here.

A couple of other rewrites occur including handling (potentially)
mutually recursive functions defined inside a block:

.. code-block:: idio

   {
     ...
     define (odd? n) ...
     define (even? n) ...
     ...rest of block...
   }

which we can rewrite into ``letrec`` definitions with the rest of the
block as the body of the ``letrec``:

.. code-block:: idio

   {
     ...
     (letrec ((odd? (function (n) ...))
	      (even? (function (n) ...))) {
       ...rest of block...
      })
   }

Next we do a neat trick.  We *extend* the existing name tree with the
list of formal parameters and then process the body (as an implied
sequence) with the extended name tree.

We return a slightly different instruction for the code generator.
Rather than one of the two function call variants we use a ``FIX-LET``
or ``TR-FIX-LET`` instruction ("tailp" is still applicable).

The difference is in the way the function part is invoked.  For a
regular function we prepared a frame of arguments then "jumped" into
the (prepared elsewhere) function body, expecting the function body to
return.

For a closed application, we've only just evaluated the function body,
there's nowhere to jump to!

Instead, we prepare a frame of arguments in the usual way then simply
run the body of the function.  The body of the function will access
the formal parameters (in the frame we just prepared) and lexical
variables further out in the usual way because we extended the name
tree before evaluating the body.

Dotted Closed Applications
""""""""""""""""""""""""""

For a varargs closed function, say:

.. code-block:: idio

   (function (a & b) (+ a (ph b))) 1 2 3

where we would expect ``b`` to have the value ``(2 3)``, everything
proceeds in much the same way as for the :ref:`fixed closed
application <fixed closed application>` until we get to the varargs
parameter.

To recap from the fixed closed application we issued a
``STORE-ARGUMENT`` instruction which produces the following sequence
of byte code:

* evaluated the argument (leaving it in the *val* register) then

* ``PUSH-VALUE`` the *val* register onto the stack

* recursed for the other arguments

* when there are no arguments left we create a *frame* and put it in
  *val*

* ``POP-VALUE`` the value off into the n\ :sup:`th` slot

We'll repeat the ``STORE-ARGUMENT`` instruction for the fixed formal
parameters.  For the parameters after that we'll issue a
``LIST-ARGUMENT`` together with the slot for the varargs variable.

This time we'll evaluate all the arguments in order as before except
when we see the ``LIST-ARGUMENT`` instruction we'll create a *pair*
from the value we pop off the stack and the value currently in the
varargs slot (which defaulted to ``#n``).  In this way we'll build a
list from the arguments we pop of the stack.  They appear on the stack
in the reverse of the order they were evaluated meaning that as we pop
them off pushing them onto the head of a list we (eventually) end up
with a list of the varargs arguments in the right order in the varargs
slot.

Of course, we'll then pop the fixed formal parameters off the stack
and into their slots in the frame and everything has just worked.

.. include:: ../../commit.rst

