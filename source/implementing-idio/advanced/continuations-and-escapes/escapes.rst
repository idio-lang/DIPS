.. include:: ../../../global.rst

*******
Escapes
*******

Escapes can be thought of as a limited ability to truncate further
processing and continue from a given point.

An obvious example is :lname:`C`\ 's ``return`` which says a function
should stop further processing and return a value now.

Loops in many languages have ``break`` and ``continue`` (or
equivalent) to stop processing of the loop altogether or stop further
processing of this iteration and go on to the next iteration of the
loop.

Elsewhere you might ``throw`` a value back to a preceding ``catch``
that can be in a different function.

``return``, ``break`` and ``continue`` have lexical scope -- you don't
really expect them to jump function boundaries -- whereas ``catch``
and ``throw`` have dynamic scope.

Another interesting `titbit
<https://www.collinsdictionary.com/dictionary/english/titbit>`_ is
that :lname:`Common Lisp`'s lexical escape :samp:`block {label} ...`
and :samp:`return-from {label} ...` use :samp:`{label}` unevaluated
which suggests at least a macro, if not a special form.  The dynamic
escape, :samp:`catch {label} ...` and :samp:`throw {label} ...` have
:samp:`{label}` evaluated which suggests they are derived forms,
ie. functions.

Lexical Escapes
===============

Lexical escapes, whilst visually easier to see and reason about are
surprisingly hard to implement.

Let's take ``return``.  ``return`` should return from a function but
wait, we do a lot of transformations from incidental things into
functions.  ``let``, or other assignments, is at risk of becoming a
function:

.. code-block:: idio

   {
     return 0
   }

should report an error as there's no function to return from but:

.. code-block:: idio

   {
     a := 1
     return 0
   }

won't because it is transformed into the application of a closed
function taking a single parameter, :samp:`{a}`, to the argument
``1``:

.. code-block:: idio

   {
     (function (a) {
        return 0
      }) 1)
   }

and ``return`` now has a function to return from.

That's probably not what we meant to return from -- and we would
probably still expect to get an error -- and *lots* of transformations
occur.  Not just in core rewriting but most templates will use
functions with the original source text embedded in them.

.. rst-class:: center

\*

We could differentiate between an anonymous function and a named
function.  :lname:`Common Lisp` supports something along these lines
by associating every defined function with an implied ``block`` named
after the function and most looping operations have a block named
``nil`` that can be returned from.

The idea being that for the named function we can wrap the function
body with the implied escape block before asking the evaluator to do
its thing.

In our case, though, we have started to lose the distinction between
named and unnamed functions because we transform:

.. code-block:: idio

   define (foo a) {
     ...
   }

into:

.. code-block:: idio

   set! foo (function (a) {
     ...
   })

and the actual function value is anonymous again.

We could float the idea of having the evaluator's ``define`` code
recognise where the value is a function and do something but slightly
worse is the rewriting of a nested function:

.. code-block:: idio

   define (foo a) {
     define (bar b) {
       ...
     }
     define (baz c) {
       ...
     }
     ...
   }

into:

.. code-block:: idio

   define (foo a) {
     set! bar #f
     set! baz #f
     set! bar (function (b) {
       ...
     })
     set! baz (function (c) {
       ...
     })
     ...
   }

which is a transform where we don't have a handle on the individual
``define``\ s and we can't handle it as easily.

That directs us into the code for handling assignment and having the
function be identified there.  Which is OK, not great, but at least we
*can* capture that association between a function name and the
underlying function value.

Nested functions introduce another dilemma.  Does it make sense for a
nested function to ``return-from`` (in :lname:`Common Lisp` parlance)
the *outer* function?

.. code-block:: idio

   define (foo a) {
     define (handler c) {
       ...
       return-from foo #t
     }
     ...
     trap some-condition handler {
       risky-processing ...
     }
   }

Actually, I think I'm OK with that.  The ``return-from`` label,
``foo``, is in scope for ``handler`` and it makes sense for a handler
to patch up whatever mess has occurred and exit cleanly.

A slightly clearer example might be a bespoke ``SIGINT`` handler for
``risky-processing`` that could break out of a time- or
resource-consuming loop.

We could have a system-wide ``SIGINT`` handler but that wouldn't know
it was in ``risky-processing`` and wouldn't know what resources needed
to be cleaned up.

A slightly more dubious case might be:

.. code-block:: idio

   while #t {
     define (handler c) {
       ...
       break
     }
     ...
     trap some-condition handler {
       risky-processing ...
     }
   }

where we're achieving the same effect although it seems less elegant
to have a handler function *break* from an enclosing loop.

I think it really is much the same, though, and the uncomfortable
feeling is probably because we're not used to nested functions.

Escapees
--------

In :lname:`C`, ``return`` may or may not take an argument -- notably
not if the function returns ``void``.  ``break`` and ``continue``
never take arguments, in fact, they are bare words.

Implementations
===============

Let's consider that, somehow, we have an :samp:`escape-block {label}
{body}` from within which we can :samp:`escape-from {label} [{val}]`
with an optional value.

A LiSP Escaper
--------------

.. sidebox::

   This feels like a curious hybrid as the use of the stack to store
   the continuation to use is surely dynamic behaviour yet the
   validation is done lexically by the evaluator.

In :ref-title:`LiSP`, :ref-author:`Queinnec` suggests a simple stack
oriented *escaper* which we can rework into something along the lines
of the :lname:`Common Lisp` ``block`` and ``return-from``.

We'll use the names ``escape-block`` and ``escape-from`` partly as I
already use a (largely redundant) ``block`` expression and partly
because I prefer it when unfamiliar things have a name related to
their function.

We can handle both with special forms -- although special forms will
cause problems with ``unwind-protect``.

In the first instance we need to build a set of lexical escapes as we
pass through the ``escape-block``\ s starting with ``#n`` at the top
level.  The :samp:`{label}` is not evaluated and should be a symbol --
although as it isn't evaluated then anything passed will be used as a
constant.  We'll need to pass our list of escapers through to all the
functions deriving meaning (think of them as another argument, adjunct
to ``nametree``) but the list is just that, a list, and we can simply
prepend new labels onto the front of the list when we see an
``escape-block``.

If we have successfully captured the association between a name and a
function then we are in the position of clearing the slate of existing
escapes when we enter the definition of a new function.  I had varying
degrees of success with this while experimenting but it's a question
of semantics as to whether a nested function should be able to see its
enclosing functions' escapes.

The meaning of the :samp:`{body}` can be wrappered with
:samp:`PUSH-ESCAPER {ci}` and ``POP-ESCAPER`` instructions.

The escaper functions handle the extra values on the stack:

* the :samp:`{ci}` of the :samp:`{label}`

* the saved *frame*

* the *PC* to continue with -- the one after ``POP-ESCAPER``

  A slight annoyance is that the *PC* must be absolute.  We can't use
  a relative *PC* here as a sort of jump as we don't know what the
  current *PC* is at the time the escaper is invoked!  We could have
  gotten anywhere in the code since this *PC* was stored on the stack
  so our only hope is an absolute *PC*.

  It's no worse than storing the absolute *PC* that ``RETURN`` uses
  but it feels wrong.

The special form ``escape-from`` then only needs to verify that
:samp:`{label}` exists in the current escape list and it can invoke
the :samp:`ESCAPER-LABEL-REF {ci}` instruction.

At runtime, as we lexically verified that :samp:`{label}` was in scope
during evaluation, we can feel reasonably confident that
:samp:`{label}`\ 's corresponding :samp:`{ci}` will be on the stack.
We can search down (up?) for it and:

#. squelch the stack above this point

#. restore the saved *frame*

#. set *val* to any supplied value

#. jump to the absolute *PC*

And on we go.  Seems to work.

``break`` and ``continue``
^^^^^^^^^^^^^^^^^^^^^^^^^^

In one sense these are quite easy as they are explicit
``escape-block`` labels.

.. sidebox::

   Essentially, :lname:`Scheme`'s ``do`` wants to return a value
   whereas the :lname:`C` or :lname:`Bash` ``for`` doesn't (care to).

We can rework :lname:`Scheme`'s ``do`` into something more like a
:lname:`C` or :lname:`Bash` ``for`` loop where the interesting thing
to us about the template is:

.. code-block:: idio

     #T{
       {
	 $loop :+ function $v {
		    (escape-block break
				  (if $test {
				    (escape-block continue {
				      $@body
				    })
				    ($loop $@s)
				  }))
	 }
	 $loop $@i
       }
     }

Here, you can see we've just inserted the relevant ``escape-block``\ s
in the loop such that ``escape-from break`` will do the right thing.

We want ``break`` not ``escape-from break`` (although it will work) so
we'll need some syntax sugar to translate the one into the other.

Of course, we now need ``escape-from``, the special form, to be
willing to accept no value and use, say, ``(void)`` in its stead (more
syntax sugar).

``return``
^^^^^^^^^^

Here, I think, we want ``return`` to mean return from the current
function.  That's a bit tricky as we don't know what the current
function's name is!

The :lname:`Common Lisp`\-y :samp:`return-from {label}` at least knows
explicitly what it wants but plain old ``return`` is a bit vague.

I think we can play a similar trick to ``break`` and ``continue``,
though, in that when we pick up on the association between a name and
a function in assignment and insert an escape block for the function
name we can also insert an escape block for the generic label
``return`` which will allow us to ``escape-from return`` much like
``escape-from break``, above.  We return from the nearest enclosing
(named) function body.

The net effect of the two escape blocks would be something like:

.. parsed-literal::

   define (*name* *args*)  {
     (escape-block *name*
       (escape-block return
         ...
       ))
   }

Usage comes up in a couple of places.  ``return`` might be used as a
name in function position or as a bare word:

.. code-block:: idio

   return #t
   return

As a name in functional position we'll need to handle ``return`` like
``break`` and ``continue``, above.  Bare words are more tricky.

Bare Words
^^^^^^^^^^

What if we want to have just plain old:

.. code-block:: idio

   break
   continue
   return

Bare words are handled at the bottom of the
*meaning* function (``idio_meaning()`` or ``meaning``) where,
normally, if the bare word is a symbol then we look it up as a
reference.

We can make a check there to see if the bare word is ``return``, say,
and execute the code to invoke the escape.

That works fine for bare words on their own as above.

However, the same code is used for the expansion of any symbol in an
argument position.  That means we can write:

.. code-block:: idio

   define (foo) {
     printf "A return looks like %s\n" return
   }

and we won't see a thing because the action of evaluating the third
element of the list, ``return``, replaces it with ``escape-from
return`` which is compiled into ``ESCAPER-LABEL-REF return``.

In other words, when we run through this code in the VM, we stop
processing at that point (in the middle of the arguments to
``printf``) and leave the function immediately (with a value of
``(void)`` as no argument was passed).

Tricky.  I suppose the argument would be that ``return`` is a reserved
word and you get (exactly) what you asked for.

unwind-protect
--------------

We have a problem, though, in the shape of the interaction between
escapers and ``unwind-protect``.

``unwind-protect`` is a good thing (although there are plenty of
people who are less keen) but we don't get to use it here.

.. code-block:: idio

   define (foo x) {
     resource := #f
     unwind-protect {
       resource = some precious thing
       trap some-conditions (function (c) {
         return
       }) {
	 risky-processing
       }
     } {
       freeup resource
     }
   }

Here, if the trap handler is invoked and calls ``return`` to leave
``foo`` then we haven't run the cleanup clause from ``unwind-protect``
and the resource is locked away.

When we apply the :samp:`escape-label-ref {label}` special form,
ultimately, :samp:`ESCAPER-LABEL-REF {ci}`, in the byte code, we'll
find the corresponding escaper on the stack and unwind the stack and
*frame* back to there.  The point being, that we are unaware of
``unwind-protect`` and its cleanup clause.

Special Forms
-------------

There is no function to be re-written for special forms -- no matter
how hard we try.  We can't capture it in a name:

.. code-block:: idio

   original-escape-block := escape-block

because the evaluator will see the right-hand side ``escape-block`` in
functional position in an expression and complain that there are no
arguments.

We can't wrap it in a template:

.. code-block:: idio

   define-template (template-escape-block label & args) {
      val := (void)
      if (pair? args) {
        val = ph args
      }

      #T{
        escape-block '$label $val
      }
   }

because the evaluator will see ``escape-block`` in functional position
in an expression and then use the unevaluated word ``'$label`` as the
label.  Erm, but we want ``'$label`` evaluated to give us the
not-to-be-evaluated label...

*Drat!*

    As an observation, the ``unwind-protect`` cleanup clause that we
    skipped with our special form lexical escape will (often but not
    always) be run albeit some time after it is expected.  The reason
    is that ``load`` has `done the honours
    <https://www.collinsdictionary.com/dictionary/english/do-the-honours>`_
    for us.

    ``load`` wants to ensure that the current module is restored when
    a loaded file is finished with (either normally or abnormally) and
    so restores the current module in a ``unwind-protect`` cleanup
    clause.

    So when ``load`` has its ``unwind-protect`` cleanup clause run
    then the recursive nature of the unwinding mechanism will mean
    that any other staged cleanup clauses from other
    ``unwind-protect`` calls will get run (in correct order).

    However, you can't force that mechanism, it is a side-effect.  So
    if your ``unwind-protect`` call is holding critical resource,
    you can't rely on a timely cleanup.

Go Deeper!
^^^^^^^^^^

For special forms, we could say, OK, let's rewrite the
``dynamic-wind`` function (and attendant values) in :lname:`C` and
make the special forms use it.

That's possible.  However, as things stood at the time I had
``dynamic-wind`` implemented in :file:`call-cc.idio` using ``reroot!``
and ``*here*`` which were private variables inside the block of code
that uses them.

Private variables are a very neat trick to encapsulate local variables
and we can carry on in that vein here using :lname:`C` functions.
Until someone, say, ``call/cc``, wants to be re-written in
:lname:`Idio`\ -land and we now have to expose the
(wanting-to-be-private) :lname:`C` function and variable to arbitrary
:lname:`Idio` functions.

That sounds like trouble waiting to happen.

Go Functional
^^^^^^^^^^^^^

We could implement ``escape-block`` and ``escape-from`` as functions.
There's several problems here.

In the first instance, as functions, all their arguments are
evaluated, notably, the :samp:`{label}`.  That's not the end of the
world, you'd just have to ``quote`` the :samp:`{label}` to be safe.

However, a function having :samp:`{label}` in its hands isn't the same
as the evaluator having :samp:`{label}` in its hands.  As the
evaluator is processing the, now arbitrary, function ``escape-block``
it would need to identity it and pluck the :samp:`{label}` argument
from it and add that to the list of lexical escapes in order that it
can verify the presence of the escape from it identifies the, now
arbitrary, function ``escape-from`` and plucks *its* :samp:`{label}`
argument from it.

There's a little too much in the way of having the evaluator know what
the (arbitrary) functions are meant to be doing in that approach.

It doesn't sound like it will scale.

It certainly doesn't look like *Art*.

Lexical Verification
^^^^^^^^^^^^^^^^^^^^

In :ref-title:`LiSP`, :ref-author:`Queinnec` gives us a good `gnarly
<https://www.collinsdictionary.com/dictionary/english/gnarly>`_
example of the lexical checking:

.. code-block:: idio

   ((escape-block foo (function (x) (escape-from foo x))) 37)

Here, the application of a closed function to 37, ``((...) 37)``,
results in a function value whose body, when invoked will try to
escape from ``foo``.

But, wait.  The escape block for ``foo`` has been unwound from our
list of lexical escapes after evaluating the expression ``(...)`` --
it is no longer in scope.  This means that when the function value is
run it will try to access a named escape block that no longer exists.

In :lname:`Idio` we'll get an ``^rt-variable-unbound-error``.

This is clearly unlike the closure over (local) variables in scope
that a function provides.  The point being that you cannot capture
lexical escapes, they exist only for the lifetime of the block that
creates them.

Here, the block creating the escape, ``escape-block foo ...``, has
completed it's run when the function has been created and returned.
It therefore will have run ``POP-ESCAPER`` in the VM and the
:samp:`{label}` is no longer available for the ``escape-from`` clause
to return to.

.. rst-class:: center

\*

Technically, you could have had another ``escape-block foo`` further
out which *is* still in scope in which case the ``escape-from foo``
clause can execute successfully although the code will now return from
an escape block much further out that the user possibly anticipated.

Here, now, we get into some debate about whether having such absolute
:samp:`{label}`\ s are what we really mean.  Would it be better if,
instead of the absolute label ``foo`` we really meant a ``foo``\ -ish
label, constructed by ``gensym`` in a template:

.. code-block:: idio

   real-label := gensym $label
   #T{
     ((escape-block $real-label (function (x) (escape-from $real-label x))) 37)
   }

and then we can be sure that *our* ``foo`` is different to the other
guy's ``foo`` (*splitter!*) should we both have used ``foo`` as a
label.

Another example might be nested loops where ``next`` could be picked
up much further out because the escaper is blindly unwinding the
stack.

Observations
------------

It looks like we have a set of competing issues here.

For :samp:`{label}`\ s to be unevaluated they need to be at least used
by a template (although there become quoting issues) or, more likely,
a special form.

For :samp:`{label}`\ s to be lexically checked they need to be seen by
the evaluator which means a special form.

Special forms don't "play nicely" with anything else.

Special forms cannot interact with private variables and functions
defined in :lname:`Idio`\ -land.  Similar functions defined in
:lname:`C` cannot be conditionally exported into :lname:`Idio`.

Perhaps the lexical escapes, ``return``, ``break`` and ``continue``
are as simple as they are and users shouldn't use them when they are
using ``unwind-protect``?

That doesn't seem to sit very well, though.  Users will make
unintended mistakes and tracking down lost resources is very hard.

Continuations
-------------

Can continuations help us out, here?  Presumably, as they are touted
as being able to create all control flow constructs.

In the very first instance, we can create our escapees rather easily.
We can (implicitly) wrap the body of functions with a suitably
argument-named continuation capture.  Here, rather than call the
continuation passed in ``k``, we'll call it something more meaningful,
like ``return``:

.. code-block:: idio

   define (foo x) {
     (call/cc (function (return) {
       ...
     }))
   }

And now, in the body of ``foo`` we can invoke the continuation
``return`` like a unary function, :samp:`return {value}`.

As it stands, continuations expect to be invoked with a single value
so maybe we can revisit that decision to allow us to pass no argument
and have the engine supply ``(void)`` instead.

``return`` is also lexical in scope -- it can only be used in the body
of the function declaring it, like any parameter.  That doesn't take
it into the realms of a lexical escape as the evaluator is unaware of
``return`` being special in any way, it's just another parameter.

.. sidebox::

   :ref-author:`Queinnec` notes that there is a question then of how
   to determine equivalence between these escape *values*, ``eq?``,
   ``eqv?`` or ``equal?``?

``return`` is not in the realm of :lname:`Common Lisp`'s ``catch`` and
``throw``'s :samp:`{label}` where the :samp:`{label}` is evaluated and
that *value* is associated with a continuation (of some kind).

As a full blown continuation, though, ``return`` can be captured --
saved in a variable in wider scope -- and then you can appear to
return from ``foo`` multiple times.  That might be what we want a
*generator* to do when it yields multiple results but that isn't
really what we want ``return`` to be doing.

We'll get into the same problems with corresponding ``break`` and
``continue`` continuations.  Resuming a *break* multiple times might
make some possible sense, resuming a *continue* might lead to disaster
depending on how the loop's *test* is implemented.  Were the loop to
stop on a specific value then a resumption of a continue will have had
the loop's variables' *step*\ s run and the *test* won't fire in the
same way.

.. include:: ../../../commit.rst

