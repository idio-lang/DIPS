.. include:: ../../global.rst

.. _`logical expressions`:

*******************
Logical Expressions
*******************

A great trick the shell plays is with *logical expressions* where the
elements of the logic can be external commands:

.. code-block:: sh

   if grep "foo" file ; then
       ...
   fi

Here, if :program:`grep` exits non-zero then the condition is
considered false.  If it exits with zero then the condition is
considered true and the conditional block is executed.

Here's the low down from the ``set``/``-e`` section in
:manpage:`bash(1)`:

    The shell does not exit if the command that fails is part of the
    command list immediately following a **while** or **until**
    keyword, part of the test following the **if** or **elif**
    reserved words, part of any command executed in a **&&** or **||**
    list except the command following the final **&&** or **||**, any
    command in a pipeline but the last, or if the command's return
    value is being inverted with **!**.  If a compound command other
    than a subshell returns a non-zero status because a command failed
    while **-e** was being ignored, the shell does not exit.

It turns out that this is, not necessarily hard but, rather, "quite
involved" to implement in :lname:`Idio`.

Basics
======

As a starter for ten, :lname:`Idio` *already* returns ``#f`` or ``#t``
based on whether the external command exits non-zero or with zero.

*Wait!* If the external command exits non-zero we don't get ``#f``
because we will have raised a ``^rt-command-status-error`` condition
(rcse) with the non-zero exit status.  The default behaviour being for
:lname:`Idio` to exit in the same manner.

So, we **don't** get ``#f``.  We need to suppress that
condition-raising behaviour, somehow.

In the meanwhile we have another issue to contemplate: *what*,
precisely, are we suppressing rcse's over?

Let me try to explain that in the context of ``if``:

.. code-block:: idio

   if (contemplate-navel) "yes" "no"

The normal expectation is that we want to suppress rcses during the
``if``'s *condition* but not during either of the *consequent* or
*alternative*, so perhaps our putative solution might look like:

.. parsed-literal::

   *suppress-rcse*
   (contemplate-navel)
   *allow-rcse*
   *test result of contemplate-navel*
   *run* "yes" *or* "no" *accordingly*

Which seems fine.  ``contemplate-navel`` doesn't sound like an
external command but maybe it executes external commands instead?  A
bit of :program:`grep`'ing and :program:`sort`'ing and fiddling with
files, say.

Should the suppression apply to those (sub-)commands?

The answer is almost certainly yes as, despite the fact they are not
the (immediate) subject of the parent ``if`` *condition*, it would
break user-expectations for such a logical test to generate a
condition you thought would be suppressed because it was part of a
logical expression.

Therefore, you can imagine that more explicitly obvious ``if``
condition expression of

    ``if (printf "%s\n" (false)) ...``

should succeed as the ``(false)`` is an argument (to be implemented as
a sub-process) of the parent ``printf ...`` expression which is the
the ``if`` condition expression.  We would expect to have ``#f``
printed -- the *result* of executing the external command
:program:`false` which exits non-zero -- even though the argument to
``printf`` very definitely failed.

.. aside::

   Keep up at the back!

(``printf`` itself will return ``#<unspec>`` which, as it isn't
``#f``, means the result is `true` and the *consequent* will be
evaluated.)

Implementation Issues
---------------------

A quick aside on implementation issues.

The easy, obvious and completely wrong option is to suppress rcses
altogether.  We *should* be being alerted to external commands failing
(presumbaly, unexpectedly) and react accordingly.  Most of the time
that should be to halt to script, which is the default behaviour.

A second, nearly as bad, option, is to have a global "suppress rcse"
:lname:`Idio` state variable.  This simply doesn't work because the
code that considers raising the rcse is itself written in
:lname:`Idio` (``wait-for-job`` in :file:`lib/job-control.idio`).
That code might well say:

.. code-block:: idio

   if suppress-rcse-var ...

but the *use* of the variable is in the condition of an ``if`` and
will therefore always have a true value (because we just said we would
suppress it in the condition of an ``if`` statement -- *duh!*).

A third, poor, option is to have a global "suppress rcse" :lname:`C`
state variable.  This breaks down very quickly as it's not obvious
what to put the value back to.  It turns out there are a lot of nested
``if``\ s.

So we need a dynamic mechanism to save and restore the current
"suppress rcse" status -- which can now be mirrored by a :lname:`C`
global safely because it is being continually updated by the VM.

We can envisage the *suppress-rcse* operation being to push the
current value onto the stack and set the value to `true`.  The
corresponding *allow-rcse* being simply to set the global back to the
value popped off the stack.

.. sidebox::

   Actually, we box ourselves into a corner there as pipelines and
   other jobs *are* established by :lname:`Idio` and as :lname:`Idio`
   is the entity creating the ``%idio-job`` structure then it will
   need to know the value of the variable.

   We can solve that with a computed variable which returns the
   :lname:`C` global value which is being maintained by the VM off the
   stack...

:lname:`Idio`, itself, needn't know about this "suppress rcse" state
as, in practice, what matters in ``wait-for-job`` is a decision as to
raise a condition or not.  That decision could be pre-set in part of
the per-job structure.

The reason we can do that is that it turns out all external commands
are run through the :lname:`C` code base.  When the VM sees a symbol
(or a string) in functional position it calls the :lname:`C` code to
launch a job.  The :lname:`C` code can easily look at the :lname:`C`
"suppress rcse" state and set the flag in the ``%idio-job`` structure
accordingly.

Of interest, it can, at the same time, set a flag to disable
notification of failure when the job completes.  In practice, it
pre-sets it to "done."

Where
^^^^^

There's another question of where, or, perhaps, by whom this
suppression is applied.

I've plumped for putting it in the code generator.  This means the
logic in the evaluator is (more or less) unchanged and the suppression
of rcses is an implementation issue.

Logical Expressions
-------------------

Logical expressions, ``and`` and ``or``, operate in a similar way.
The practical implementation is more like a rolling ``if`` statement:

.. code-block:: idio

   (and expr1
        expr2
	expr3)
   ...

is implemented as:

.. code-block:: text
   :linenos:

   evaluate expr1 -> *result1*
   if *result1* is false goto #6
   evaluate expr2 -> *result2*
   if *result2* is false goto #6
   evaluate expr3 -> *result3*
   ...

Where the evaluation of each expression will generate a result:

* if the result is `false` then we jump straight to the end of the
  ``and`` expression and therefore effect a result of `false` for the
  overall ``and`` expression

* if the result was `true` then we continue on to evaluate the next
  expression

* if all of the previous evaluations were `true` then the result of
  evaluating the last expression (whether `true` or `false`) is the
  overall result

The conditional test is reversed for ``or``.

With our "suppress rcse" hats on we have a choice to:

#. wrap each evaluation in suppress/pop statements

#. wrap the whole expression in suppress/pop statements

.. aside::

   Can you see what I did there?

However, in both cases, we keep coming back to a problem: recursion.

Recursion
^^^^^^^^^

A problem not faced by the shell is that :lname:`Idio` is a pretty
flexible programming language including arbitrary "depth" recursion
through tail-call optimisation.

Here we trip over a different problem in that we might not reach the
end of the block to pop the rcse state.

.. aside::

   Hint: it might be the one I tripped over...

Here's a function that implements recursion inside a logical
operation.  The function is testing each element of a list with a
predicate, ``p?``.  If the current head of the list satisfies ``p?``
then recurse to the next element.

.. code-block:: idio

   define (list-of? p? a) {
     (or (null? a)
         (and (p? (ph a))
	      (list-of? p? (pt a))))
   }

Here, you can imagine that the *suppress-rcse* operation is invoked
for both the ``or`` and ``and`` blocks.  Let's just look at the
``and`` block and let's go for the per-expression suppression option:

.. code-block:: text
   :linenos:

   ...
   *suppress rcse*
   p? (ph a) -> *result1*
   *pop rcse*
   if *result1* is false goto #9
   *suppress rcse*
   list-of? p? (pt a)
   *pop rcse*
   ...

However, the call to ``list-of?`` at the end of the ``and`` block (on
line 7 above) is in tail position and so will "goto" the start of the
``list-of?`` function (again).  The start of the logical operators
will push another set of "suppress rcse" values onto the stack.

Now, we *will* eventually hit the end of the block -- one of those
calls to ``list-of?`` will return a value -- and each of the two
logical operators will pop *one* "suppress rcse" value off the stack.
Unfortunately, we pushed *2n* onto the stack when we were recursing.

We've now messed up the stack.

Hmm, wait, though.  Tail-call optimisation is only effective on the
last expression (and only in a function).  What if we only wrapped the
non-final expressions in the suppress/pop operations?

.. code-block:: text
   :linenos:

   ...
   *suppress rcse*
   p? (ph a) -> *result1*
   *pop rcse*
   if *result1* is false goto #7
   list-of? p? (pt a)
   ...

Well, that works and avoids our tail-call recursion problem.

It is curiously similar to the :lname:`Bash` implementation which says
that the ``-e`` is not effective for the last expression in a logical
combination.

It still feels odd, though.  Consider a generic use of :

.. code-block:: idio

   if (and (true)
           (false)) ...

will cause an *exit-on-error* in our programming language because the
``(false)`` will fail and isn't protected by an rcse suppression.  Now
it doesn't seem so right.

What knowledge can we bring to bear on this?  Well, we know that in
this particular example of the logical operation in the condition
clause of an ``if`` expression, the conditional expression **cannot**
be in tail position (both the *consequent* and *alternative*
expression *could be* in tail position but the *condition* is very
definitely not in tail position).

So, there are circumstances when we know tail-call optimisation will
not be used and therefore where we can ensure that the final
expression is also wrapped with suppression.

So that leaves genuine tail calls which we simply have to say cannot
be so constrained, that is:

.. code-block:: idio

   define (foo) {
     (and (true)
          (false))
   }

cannot have the invocation of ``(false)`` suppressed.

We can't even do some analysis of ``(false)`` to determine if it is an
external command or not (however that might be done) as it is not the
*kind* of expression being invoked but that it is in tail position
that changes the kind of code the code-generator generates.

A function call as the last expression in a function results in a tail
call.  That's the deal.

It so happens you can work around the tail call issue *in this case*
by using a temporary variable and returning it:

.. code-block:: idio

   define (foo) {
     r := (and (true)
               (false))
     r
   }

but it becomes anomalous -- and therefore a feature! -- that you need
to use a temporary variable to suppress raising rcses for external
commands in tail call scenarios.

Details
"""""""

We do have a couple of implementation details to handle, here.

Firstly, we need to pass the tail-call-ness of the expression to the
code generator so that it can apply the suppression if required.

Secondly, the evaluator was following in the style of
:ref-title:`LiSP` where a special case was taken for single-expression
sequences, that is to say:

.. code-block:: idio

   and (foo)

   or (bar)

are identical to simply evaluating the expression itself:

.. code-block:: idio

   (foo)

   (bar)

However, in order that we can apply the suppress/pop -rcse operations,
we need even single-expression sequences go through the motions.

Not a huge change.

Pipelines
---------

Pipelines, and other :lname:`Idio` generated jobs, rear their
convoluted heads, now.

We would expect to be able to use a pipeline as part of one of these
logical expressions, along the lines of a shell's:

.. code-block:: sh

   if zcat foo.gz | grep bar ; then
       ...
   fi

(not everyone has GNU grep)

The problem with :ref:`pipelines <pipelines and IO>` is that the ``|``
operator will have established, here, two child processes joined by a
pipe and then any external commands in the pipeline sub-commands are
children of those pipeline child processes.  Grandchildren of us.

We are predicating the ``if`` on figuring out whether :program:`grep`
(or :program:`zcat`!) exits zero or non-zero.  As it stands, though,
because the pipeline is in the condition of an ``if`` we have
suppressed rcses.

Without an rcse then in the right hand pipeline process the
(sub-process) :program:`grep` will return ``#t`` or ``#f``
and... nothing else happens.  Because we just told it not to raise a
condition if the process fails.

Without a condition being raised then the right hand pipeline process
won't, itself, *exit on error* and, in turn, we, the :lname:`Idio`,
won't see anything untoward.

So, the fix is that when we fork in the operator we have the child
process disable the rcse suppression.

Not
---

Slightly unexpectedly, the function ``not`` does not fit into the
scheme.  That's because it's a function and isn't recognised as a
logical operation.

To use ``not`` in a logical sense, supporting external commands, we'll
have to unpick everything:

#. remove function definitions of ``not``

#. make ``not`` a special form

#. the evaluator needs an appropriate clause with a new intermediate
   code, passing the tail-call-status (it should always be false!)

#. the code generator needs an appropriate clause with a determination
   as to wrap with suppress-rcse statements

#. the VM needs an appropriate clause

.. aside::

   Which is both a bit annoying and relatively hard to find.

However, if we do all that then some uses of ``not`` break down.

#. we can't pass ``not`` around as a function value -- which is a
   thing

#. rather more subtly, we can't always use ``not`` in a template
   because the evaluator will have seen and run it rather than leave
   it alone to be asserted next time

In both cases we can work around the problem with an actual function,
say, ``not/function``, which simply calls the ``not`` special form
with its argument.

Clumsy, though.

.. include:: ../../commit.rst

