.. include:: ../../../global.rst

.. _`idio continuations`:

*************
Continuations
*************

:ref:`Continuations <continuations>`, as you recall, are a mechanism
to resume processing with a known state.  To implement that we need
two things:

#. the state

#. where to resume

and...that's it, which seems quite remarkable for something so powerful.

We should further distinguish between *undelimited* and *delimited*
continuations.  Few languages allow continuations at all because of
their perceived danger (programmatic *goto*) and many :lname:`Scheme`
users shy away from undelimited continuations in favour of delimited
continuations -- you can only jump back so far.

For further reading consider :ref-author:`Oleg Kiselyov`'s site on
`Continuations and Delimited Control
<http://okmij.org/ftp/continuations/index.html>`_.

Implementation
==============

State
-----

The obvious first question is what constitutes the program's *state*?
A second, less obvious, question is what does *not* constitute the
program's state?

In an ideal stack-oriented language *all* the program state would be
on the stack so we could just stash a copy of that away and be done.

We don't have an ideal stack-oriented language as, amongst other
things, we stash values away in a per-function call *frame*.  Clearly,
for a function to resume it must have access to the frame (hierarchy)
in order that it can continue to manipulate those values so it looks
like we need to save the current frame as well.  In practice, we would
save the current top-level (module) as well, just like a function call
saves and restores the frame and top-level.

The formal parameters in the frame might have an air of being
read-only but in practice are mutable and so there is no useful way to
create a snapshot of these values.  Thus frames fall into a grey area
where we can ensure that the restored structure is correct but we
can't be so sure about the values in them.

Finally, there are top-level values, globals if you like.  We can't do
anything about them, they are what they when we resume.  You can see
here how globals (and frame parameters in our case) are considered
even more harmful than usual.  We (might) want to resume *as was* but
can't.

But wait, there is also the *dynamic environment*, the likes of the
current input, output and error handles.  These are state variables
currently maintained in the current *thread*.

Where
-----

The descriptions of continuations always makes an understanding of
*where* a bit woolly.  With our byte-coded VM, the *where* very simply
becomes the next instruction after the body of the continuation.

We already have to handle this "instruction after" business with the
implementation of ``if`` to allow us to jump over the one or the other
clause depending on the result of the test clause.

However, in terms of the normal interface, ``call/cc``, it is even
easier still.  The normal form is :samp:`call/cc {p}` where
:samp:`{p}` is a unary procedure, ie. takes one argument which is the
continuation.

So, :samp:`{p}` is an argument to ``call/cc`` and by the normal
evaluation of arguments it will have been evaluated *before*
``call/cc`` is invoked.  That means that the pseudo-byte code for:

.. parsed-literal::

   call/cc p
   ...

looks like:

.. parsed-literal::

   evaluate call/cc
   push value
   evaluate *p*
   push value
   create frame
   pop-frame0		the value of *p* into frame slot 0
   pop-function		the value of call/cc into *func*
   invoke-function
   ...

But look, at the moment of running ``call/cc``, at the
``invoke-function`` instruction, which is about to create a
continuation which needs to know where to go "next" if the
continuation is invoked, the place it needs to go "next" is the very
next instruction.  In other words, the *PC* that ``call/cc`` needs to
save happens to be, uh, *PC* (because it is incremented after reading
the instruction to *invoke-function*).

Here it doesn't matter whether :samp:`{p}` is a predefined function or
one you are declaring on the fly because of the way arguments are
evaluated to return a function value.  If ``p`` was a named function
then :samp:`evaluate {p}` will cause a lookup of ``p`` and we'll get
back a function value.

If ``p`` was an on the fly function then :samp:`evaluate {p}` will
result in a wall of code the end value of which is a function value.

Either way, :samp:`evaluate {p}` has resulted in a function value
which we push onto the stack and later into the frame like any other
value.

Operation
---------

When we capture a continuation we need to stash a copy of the current
stack.  It must be a full copy, rather than a reference, as if future
processing changes the stack then we won't be restoring the stack as
it was.  In that sense it doesn't matter if the restoration is larger
or smaller than the current stack, ie. if we are heading out of the
stack[sic] of function calls or heading back into the depths, we need
a copy of the stack as was.

The obvious case is if we capture a continuation in the bowels of some
function calls -- a generator springs to mind -- and then allow the
function calls to unwind naturally.  Had we only kept a reference to
the stack then our continuation will now have a reference to a
naturally unwound stack.  Not very useful if we want to resume the
generator!  Of course, if it had made a copy of the stack at the time
the continuation was captured then it can restore that stack
trivially.

You can take the word "trivially" with a pinch of salt as copying the
stack repeatedly isn't a cheap operation.  There's a time and space
penalty to using continuations.

We also need to stash the frame and current module.  We could have
called the standard ``idio_vm_preserve_state()`` except it modifies
*the* stack -- we don't want the stack modified.

Instead we'll just make the continuation object have references to all
the objects of interest.  The one exception is the stack which we will
take a full copy of for full continuations.  This allows us to
independently reproduce the entire computing state (modulo frame
contents and global values!) whenever requested even if the program
had otherwise wound everything up.

I've also saved a reference to the current *thread*.  We don't have
too many threads but we need to recover the right one when a
continuation is invoked!

sigjmp_buf
^^^^^^^^^^

There's a minor addition to all this in the form of a :lname:`C`
``sigjmp_buf``.  When a file is ``load``\ ed we get a new, nested
``sigjmp_buf`` and, therefore, if we need to unwind the program state
we need to unwind to this correct ``sigjmp_buf``.

The whole :manpage:`sigsetjmp(3)` business could do with some clearer
thinking!

:lname:`C` Implementation
-------------------------

The :lname:`C` data structure is, not surprisingly:

* the (full copy of the) stack

* the frame and current module

* current thread

* the *PC*

* the ``sigjmp_buf``

plus the usual ``grey`` link for compound types:

.. code-block:: c

   typedef struct idio_continuation_s {
       struct idio_s *grey;
       idio_ai_t pc;
       struct idio_s *stack;
       struct idio_s *frame;
       struct idio_s *env;
       sigjmp_buf jmp_buf;
       struct idio_s *module;
       struct idio_s *thr;
   } idio_continuation_t;


Invocation
^^^^^^^^^^

Invoking a continuation requires that we identify the element in
functional place as a continuation in ``idio_vm_invoke()`` (verifying
there is a single argument) and call
``idio_vm_restore_continuation()``.

.. aside::

   ...and I have a number of bite marks to prove it!

   `Ooh err, missus <https://en.wiktionary.org/wiki/ooer>`_

We *must* duplicate the continuation's copy of the stack, rather than
simply replace it, in case we re-use this continuation.  I keep
repeating that, it is important and you will get bitten if you don't.

.. rst-class: center

\*

The verification of a single argument is a bit moot depending on
whether we intend to use a :lname:`Scheme`-ish ``call-with-values``.
There are some details in :ref-author:`Kent Dybvig`'s chapter on
`Control <http://www.scheme.com/tspl3/control.html#./control:s53>`_ in
:cite:`TSPL`.

I've kept the test in as multiple values occurs where the native
``call/cc`` (actually ``%%call/uc``) has been wrappered and therefore
is a closure and won't be passing through the code for invoking a
(true) continuation value.

Where the native call is used then we will have a true continuation
value and can apply the test.

dynamic-wind I
--------------

I've looked at a couple of implementations of ``dynamic wind``.

The broad thrust of ``dynamic-wind`` is that you have three *thunks*,
``before``, ``during`` and ``after``.  You run ``before`` as some sort
of setup, ``during`` as the action part and, most importantly,
**always** run ``after``.

.. sidebox::

   Here you'd also require that the variable referencing the file
   handle we're opening, using and (always!) closing is in an
   appropriate scope.

   Some syntax sugaring might help which leads to the

   .. parsed-literal::

      with *fh* as *open-file-expression* {
        *do-something-with fh*
      }

   forms.

The most common usage has ``after`` perform some cleanup operations.
You might imagine that ``before`` arranged to open a file descriptor,
``during`` does something with the supplied file descriptor and
``after`` closes the file descriptor so we don't have any operating
system resource issues.

Clearly, if we have some issue in ``during`` then we want to ensure
that ``after`` is always run.

.. aside::

   I've always mis-read concomitant as co-committed but in fact it is
   from the Latin *concomitant* meaning 'accompanying' derived from
   *concomitari*, from *con* meaning 'together' and *comitari* from
   *comes* meaning 'companion'.

I picked up on what I believe to be the R5RS description making
``dynamic-wind`` and ``call/cc`` concomitant.  Further Intertube
scrambling suggests that the ``reroot!`` function is using the
Hanson-Lamping algorithm (see `http://arclang.org/item?id=15536
<http://arclang.org/item?id=15536>`_) from an unpublished 1984(?)
paper.

R5RS says:

    A state space is a tree with the current state at the root. Each
    node other than the root is a triple <before,after,parent>,
    represented in this implementation as two pairs:

    .. code-block:: scheme

       ((before . after) . parent)

    Navigating between states requires re-rooting the tree by reversing
    parent-child links.

The code looks like:

.. code-block:: idio

   dynamic-wind := #f

   {
     *here* := list #f

     define (reroot! there) {
       if (not (eq? *here* there)) {
	 reroot! (pt there)
	 {
	   before := phh there
	   after := pth there
	   set-ph! *here* (pair after before)
	   set-pt! *here* there
	   set-ph! there #f
	   set-pt! there '()
	   *here* = there
	   (before)
	 }
       }
     }

     orig-call/cc := call/cc

     call/cc = function (k-proc) {
       here := *here*
       orig-call/cc (function (k) {
			   k-proc (function results {
				     reroot! here
				     apply k results
			   })
       })
     }

     dynamic-wind = function (before during after) {
		      here := *here*
		      reroot! (pair (pair before after) here)
		      call-with-values during (function results {
						 reroot! here
						 apply values results
		      })
     }
   }

Don't worry about the ``call-with-values`` in ``dynamic-wind`` (it has
*also* been concomitant'ed with ``call/cc``!) as it's just a means to
bundle multiple values around as though they were one.  The key point
is that ``reroot!`` is called before extracting the values[sic] from
``results``, themselves the results[sic] of invoking ``during``.

By way of explanation, ``reroot!`` is playing a very dirty trick --
the sort of thing it should be ashamed of and yet simultaneously is
very clever.  It is modifying the *contents* of ``*here*`` and
:samp:`{there}` and then changing what ``*here*`` refers to which is
critical because the callers of ``reroot!`` have generally taken a
reference to ``*here*`` (as it was when they started).

The important part about ``reroot!`` modifying the *contents* is
because of the ``eq?`` test.  ``eq?`` will be testing the address in
memory of the pairs and not the contents of the pairs.  It is
obviously true that if the two variables refer to the same address
then they are the same.  However, they no longer have the contents you
first thought of.

The callers' reference to ``*here*`` (usually called :samp:`{here}`)
started as, probably, ``(#f . #n)`` but will become

:samp:`(({after} . {before}) . {orig-there})`

and :samp:`{orig-there}` was itself

:samp:`(({before} . {after}) . {orig-*here*})`

which means when the caller subsequently calls ``reroot!`` again with
:samp:`{here}` they're actually calling it with

:samp:`(({after} . {before}) . {orig-there})`

which means the first thing ``reroot!`` does is call itself with
:samp:`(pt {there})`, ie. :samp:`{orig-there}`.

But wait!  :samp:`{orig-there}` was *also* modified by ``reroot!`` to
be ``(#f . #n)`` which now ``eq?`` ``*here*`` because ``reroot!``
changed what ``*here*`` referred to as well (to :samp:`{orig-there}`
in fact).

.. sidebox::

   A pencil and paper and remembering that ``eq?`` for pairs is
   testing the location in memory and not the contents is the key,
   here.

   Or admit defeat and simply believe it is true.

Don't forget, if you're remotely following, that any modification to
:samp:`{there}` will affect all those who were referencing it as part
of another data structure!

A neat side-effect of toggling the :samp:`({after} . {before})` pair
is that ``reroot!`` will now blindly call :samp:`({before})` as
previously but now :samp:`{before}` -- :samp:`(phh {there})` -- is
actually :samp:`{after}`.

*Capiche?*

This works for full continuations and is largely invisible other than
for anyone paying careful attention to the continuation object they
are passed which may now be a function.  You still invoke it in the
same way, :samp:`k {value}`, but ``k``, here, is just a closure.

However I didn't see much in terms of delimited continuations which I
wanted to play with for some of the escapes we want to use.

Delimited Continuations
=======================

Delimited continuations differ from undelimited continuations by
virtue of being, uh, limited in extent.  It should come as no surprise
that the theory is considerably more vexed than this but let's not get
side-tracked for a moment.

So now we looking at :ref-author:`Oleg Kiselyov`'s
`delim-control-n.scm`_ which uses
undelimited continuations to derive delimited continuations.

I've, *\*ahem\**, "improved" that code slightly by constraining its
elegant multi-faceted implementation (the original can be any of the
:ref-author:`Felleisen` \*F\* operators) and bodging in
:samp:`{tag}`\ s.

Delimited continuations tend to be described in terms of two pairs of
operators: ``prompt``/``control`` and ``reset``/``shift`` which differ
in some quite subtle ways.  They also capture a slightly obtuse
continuation, that between the ``prompt`` and ``control`` (or
``reset`` and ``shift``).

.. sidebox::

   I've seen reference to "over 700" delimited control operators --
   YMMV.

Otherwise, as the `Guile manual notes
<https://www.gnu.org/software/guile/manual/html_node/Shift-and-Reset.html>`_
there appear to be "a number" of delimited control operators to be
enjoyed.

.. sidebox::

   I've worded the extent of the continuation badly but let's keep on
   and see where we get.

However, sticking with our two base control operators, for the sakes
of argument they largely act the same in that you establish a
start-of-continuation with :samp:`prompt {body}` (or :samp:`reset
{body}`) and then in the :samp:`{body}` you can further establish the
end-of-continuation with :samp:`control {k} {body}` (or :samp:`shift
{k} {body}`).

The delimited continuation is the bit of code between
``prompt``/``reset`` and ``control``/``shift`` so for:

.. code-block:: idio

   prompt {
     1 + (control k {
       k 3
     })
   }

we get the continuation :samp:`1 + {[]}`.  The value passed will be
whatever the invocation of the continuation in ``control``'s body
passes.  In this case it is :samp:`{k} 3` meaning the delimited
continuation is invoked with :samp:`1 + 3`.  It will return that value
back into ``control``'s body which, in this case, promptly[sic]
returns it.

*Not* invoking the continuation in the body of ``control`` means
``prompt`` will return whatever ``control`` returns (as the
continuation body is not invoked -- as you would hope).  Hence:

.. code-block:: idio

   prompt {
     1 + (control k {
       3
     })
   }

without invoking :samp:`{k}` returns ``3``.  This is the same
*behaviour* as ``k 3`` in the previous example, which, being the last
expression, would have been the value ``4``, ie. ``control k 4`` which
means ``prompt`` returns ``4``.

.. code-block:: idio

   prompt {
     1 + (control k {
       printf "(k 3) is %s\n" (k 3)
       9
     })
   }

will, in combination, print ``(k 3) is 4`` then return ``9``.

.. rst-class:: center

\*

There is a subtlety, here, when using such trivial examples in that
the continuation is the smallest possible transactable expression as
per the original wording in :ref:`continuations`.

So a more involved scenario:

.. code-block:: idio

   prompt {
     display "Hi Mum!\n"
     1 + (control k {
       printf "(k 3) is %s\n" (k 3)
       9
     })
   }

Does **not** give you a continuation of:

.. code-block:: idio

     display "Hi Mum!\n"
     1 + []

but is just the simplest transaction :samp:`1 + {[]}`.  The
``display`` (and all code leading up to the actual continuation) will
get run once, `early doors
<https://en.wiktionary.org/wiki/early_doors>`_.

This will come back to bite us so let's consider a quick fix.  We,
essentially, want to encompass all the expressions leading up to the
start of the ``control`` expression.

The usual :lname:`Scheme`\ ly approach is to wrap such a group of
expressions into a thunk to be evaluated "later".  We can see that in
the syntactic sugar for ``control`` which wrappers an arbitrary set of
expressions, :samp:`{e}`, into a function taking the name of the
continuation, :samp:`{k}`, as an argument.

.. _`closed function trick`:

We should be able to do something similar here.  Suppose we took our
set of expressions and wrapped them up in a function that was waiting
for a continuation value, :samp:`{[]}`, to be passed, something like:

.. code-block:: idio

   function ([]) {
     display "Hi Mum!\n"
     1 + []
   }

and then made that whole expression a closed function call with the
``control`` expression as the argument:

.. code-block:: idio

   (function ([]) {
     display "Hi Mum!\n"
     1 + []
   }) (control k ...)

Hmm, it might just work!

prompt/control
--------------

The `reduction rules for prompt
<https://docs.racket-lang.org/reference/cont.html#%28form._%28%28lib._racket%2Fcontrol..rkt%29._prompt%29%29>`_
essentially say that the original expression is rewritten:

.. parsed-literal::

   prompt (*delim-body* (control k *control-body*))
   prompt ((function (k) *control-body*) (function (*[]*) *delim-body*))

.. sidebox::

   :samp:`{[]}` is not -- or shouldn't be -- a valid identifier in
   :lname:`Idio` -- I'm just trying to tie this description in with
   the commonly used notation for the value passed to a continuation.

The replacement expansion is slightly lost in :lname:`Scheme`\ ly
parentheses.  What it is saying is

.. parsed-literal::

   prompt (*closed-unary-function* *arg*)

with :samp:`{arg}` itself being a unary function.  Very confusing,
very :lname:`Scheme`\ y!

Ultimately, though, it means that the :samp:`{k}` in
:samp:`{control-body}` is the function :samp:`function ({[]})
{delim-body}` such that when you call :samp:`{k} {v}` you will be
passing :samp:`{v}` as the continuation value :samp:`{[]}`, ie. the
argument to :samp:`{delim-body}`.

From that you can also see that if the continuation :samp:`{k}` is not
invoked then :samp:`{delim-body}` is not invoked and
:samp:`{control-body}`'s returned value is what ``prompt`` will
return.

Applying those reduction rules to our trivial example (and rewriting
in a more :lname:`Scheme`\ ly fashion as it's shorter!):

.. parsed-literal::

   prompt (1 + (control k (k 3)))

   *apply the reduction rule*
   prompt ((function (k) (k 3)) (function ([]) (1 + [])))

   *substitute k in control-body*
   prompt ((function ([]) (1 + [])) 3)

   *substitute [] in delim-body*
   prompt (1 + 3)

   *...complicated maths...hang on!...*
   prompt 4

   4

You can invoke the continuation more than once:

.. code-block:: idio

   prompt (1 + (control k ((k 3) * (k 4))))

the invocations of :samp:`k {n}` are replaced with ``4`` and ``5`` and
the result of ``control`` (and therefore ``prompt``) is ``20``.

.. note::

   This use of multiple invocations implies that delimited
   continuations must be implemented with undelimited continuations --
   or, at least, the underlying implementation copies the stack.
   Here, :samp:`{k}` is being used more than once so to be able to
   resume :samp:`{control-body}` with its deeper stack intact the
   underlying continuation must have saved it.

   If you implement ``prompt``/``control`` using a "native" delimited
   continuation (which only remembers the height of the stack and not
   its contents) then when the code resumes the stack will be
   extended, rather than truncated, and the extra values are whatever
   the default value of an array element are (probably ``#f``).  The
   VM gets upset quite soon after that (noted the author).

       I suppose you could implement such "native" delimited
       continuations as not simply remembering the height of the stack
       but rather the section of the stack that needs to be restored
       -- a height plus stack segment.

You can have multiple ``control``\ s which starts getting a bit more
*interesting*:

.. code-block:: idio

   prompt (1 + (control k1 (2 * (control k2 (k1 3)))))

:socrates:`Erm, OK.`

To be fair, it's not *that* hard!

Taking each ``control`` in turn:

* :samp:`{k1}` has a

  - :samp:`{delim-body}` of :samp:`1 + {[]}` and a

  - :samp:`{control-body}` of :samp:`2 * (control k2 (k2 3))`

  noting that :samp:`{k1}` isn't used anywhere

* :samp:`{k2}` has a

  - :samp:`{delim-body}` of :samp:`1 + (control k1 (2 * {[]}))` and a

  - :samp:`{control-body}` of :samp:`k2 3`

:samp:`{k2}` *is* invoked so we will run its :samp:`{delim-body}`,
:samp:`1 + (control k1 (2 * {[]}))`.  :samp:`{[]}` is ``3`` so we get
:samp:`1 + (control k1 (2 * 3))` ie :samp:`1 + (control k1 6)`

That :samp:`{control-body}` is interesting because it does not use
:samp:`{k1}`.  If you recall the reduction rules an unused :samp:`{k}`
means that ``prompt`` returns whatever ``control`` returns and,
critically, the :samp:`{delim-body}` is not run.

In other words, ``prompt`` returns ``6``.

.. aside::

   OK, OK, I didn't get it for a while either.  We're in a sort of
   theory stage, nod sagely and let's move on.

Though, I confess it's not something that's immediately obvious.

Implementation
^^^^^^^^^^^^^^

If we look at the implementation of :ref-author:`Oleg Kiselyov`'s
``prompt``/``control`` in :lname:`Scheme` it requires the maintenance
of a list of "holes" (also confusingly called "cells") each of which
is a tuple of the continuation and a flag distinguishing ``control``
from ``shift`` (as they are otherwise identical).  I've slightly
reduced the code complexity by removing one of the variables that
allows for more control operators (that we're not interested in):

.. code-block:: scheme
   :caption: `delim-control-n.scm`_

   ; This is one single global mutable cell
   (define holes '())
   (define (hole-push! hole) (set! holes (cons hole holes)))
   (define (hole-pop!) (let ((hole (car holes))) (set! holes (cdr holes)) hole))

   (define (cell-new v mark) (cons v mark))
   (define (cell-ref c) (car c))
   (define (cell-marked? c) (cdr c))

   ; Essentially this is the ``return from the function''
   (define (abort-top! v) ((cell-ref (hole-pop!)) v))
   (define (unwind-till-marked!)
     (if (null? holes) (error "No prompt set"))
     (let ((hole (hole-pop!)))
       (if (cell-marked? hole)		; if marked, it's prompt's hole
	 (begin
	   (hole-push! hole)		; put it back
	   '())	
	 (cons hole (unwind-till-marked!)))))

   (define (prompt* thunk)
     (call-with-current-continuation
       (lambda (outer-k)
	 (hole-push! (cell-new outer-k #t)) ; it's prompt's hole
	 (abort-top! (thunk)))))

   (define (control* f)
     (call-with-current-continuation
       (lambda (k-control)
	 (let* ((holes-prefix (reverse (unwind-till-marked!)))
		(invoke-subcont 
		  (lambda (v)
		    (call-with-current-continuation
		      (lambda (k-return)
			(hole-push! (cell-new k-return is-shift))
			(for-each hole-push! holes-prefix)
			(k-control v))))))
	   (abort-top! (f invoke-subcont))))))

   (define (abort v) (control* (lambda (k) v)))

   ; Some syntactic sugar
   (define-syntax prompt
     (syntax-rules ()
       ((prompt e) (prompt* (lambda () e)))))

   (define-syntax control
     (syntax-rules ()
       ((control f e) (control* (lambda (f) e)))))

Where we start by declaring the (global) ``holes`` and then some push
and pop operations on it and how to create a hole (or cell).  We then
get to the more interesting functions.

.. |outer-k| replace:: :samp:`{[]}`:sub:`outer-k`

.. |k-control| replace:: :samp:`{[]}`:sub:`k-control`

.. |k-return| replace:: :samp:`{[]}`:sub:`k-return`

``prompt*`` (the ``*`` because the code allows it to be either
``prompt`` or ``reset`` -- technically, they are identical) pushes a
hole/cell onto ``holes`` which contains its own continuation,
:samp:`{[outer-k]}`, and then calls ``abort-top!`` with the value from
evaluating its thunk argument (ie. its body).

``abort-top!`` will pop the topmost hole and extract the continuation
from it (using ``cell-ref``) and apply that continuation to
``abort-top!``'s own argument, :samp:`{v}`.

So far, then, in the most trivial sense, if the body of ``prompt*``
didn't do anything interesting, then the ``abort-top!`` in ``prompt*``
will pop ``prompt*``'s own hole straight back off the list and thus
invoke ``prompt*``'s continuation, :samp:`{[outer-k]}`, with the result of
evaluating ``prompt*``'s body.  Thus, in a rather round-about manner,
``prompt*`` returns the result of evaluating its own body.

``unwind-till-marked!`` pops holes until it finds a marked hole
(ie. created by ``prompt`` -- or ``shift``, it turns out) and returns
the popped list.

``control*`` (the ``*`` because the code allows it to be either
``control`` or ``shift``) is a bit more complicated.  First of all it
captures its own continuation as :samp:`{[k-control]}`.  It then
establishes the set of holes up to the nearest enclosing marked hole,
ie. one created by ``prompt``, and saves the reversed result as
``holes-prefix``.

It then establishes a function, ``invoke-subcont`` which, if invoked,
will capture its own continuation, pushing that onto the list of
holes, immediately follow that with the (reversed!) list of holes
(thus re-ordering it again) and invoke :samp:`{[k-control]}`, the "parent"
continuation with whatever value ``invoke-subcont`` was passed.

``invoke-subcont`` is acting a bit like ``prompt*`` in pushing its own
continuation onto the set of holes and then invoking a wider
continuation on its argument but it also re-establishes the set of
holes that were lying in between ``prompt*`` and ``control*``.  It's a
form of repeater, re-establishing the set of holes as was modulo the
current invocation's continuation.

Of course, ``invoke-subcont`` might not get invoked because it is just
an argument passed to ``f`` the function passed to ``control*``.  The
only thing we know for sure is that ``abort-top!`` is going to be
called with the result of calling ``(f invoke-subcont)``.  Don't
forget, ``invoke-subcont`` is just the name of a function and
evaluating it will just result in a function value, nothing will be
running it.  (Not there, anyway.)

``control*``'s ``f``, as we can see from the syntactic sugar for
``control``, lower down, is a function derived from its arguments.  If
you recall the invocation of ``control`` it is something like
:samp:`control {k} ...` where :samp:`{k}` is some named continuation
and we can see through the syntactic sugar that that has been
rewritten as :samp:`control* (function ({k}) ...)` thus making
:samp:`{k}` a valid lexical name in ``...``.

Again, in the most trivial case, with :samp:`...` being a simple
value, say, ``3``, then ``control*``'s ``f`` is :samp:`(function ({k})
3)`.

Here, now, we see the more interesting part, from ``(f
invoke-subcont)``, we can see that the argument :samp:`{k}` to
``control*``'s ``f``, that is ``control``'s named continuation, is the
function ``invoke-subcont``.  Although we're not invoking :samp:`{k}`
in this example so it doesn't matter right now.

Instead, we run ``f``, ignoring its argument :samp:`{k}` and return
``3`` which ``abort-top!`` then invokes with the continuation in the
hole on the top of the list which, in our trivial case, should be
``prompt*``'s.  And so ``prompt*`` returns ``3`` in turn.

If we review an expanded invocation:

.. parsed-literal::

   *[outer-k]* prompt (1 +
               *[k-control]* (control k 3)
	  )
   ...

The ``prompt`` will establish its :samp:`{[outer-k]}` as whatever receives its
value (here, the top level!).  ``control`` will establish its
:samp:`{[k-control]}` in the expression :samp:`1 + {[k-control]}`.  At
the time ``control``'s body is invoked, the list of holes only has
``prompt``'s hole, :samp:`{[outer-k]}` on it.

Next, let's have ``control`` use its continuation, ``k``, say, ``(k
3)``.  ``prompt`` sets up the same and now ``k``,
ie. ``invoke-subcont`` comes into play:

.. code-block:: idio

   prompt (1 +
		(control k {
			     ...
		             k 3
			     ...
			   })
	  )

As we run through ``control*``, ``holes-prefix`` will be an empty list
as there's only ``prompt*``'s hole on the list (and
``unwind-till-marked!`` puts it back).  We then call ``k 3``,
ie. ``invoke-subcont 3`` which establishes its own continuation,
:samp:`{[k-return]}` and pushes a hole with that on the list and then
pushes the (empty!) ``holes-prefix`` on as well.  ``holes`` now looks
like: :samp:`(({[k-return]}) ({[outer-k]}))` and the continuations
look like:

.. parsed-literal::

   *[outer-k]* prompt (1 +
               *[k-control]* (control k {
					  ...
					  *[k-return]* k 3
					  ...
					})
	  )

We now explicitly call :samp:`{[k-control]}` with :samp:`{v}`,
ie. ``3``, in other words we're now in :samp:`1 + {[k-control]}` and
the invocation of ``(thunk)`` in ``prompt*`` returns (with the value
``4``).

That value is passed to ``abort-top!`` as it was before but this time
there is an extra hole on the list and ``abort-top!`` now invokes the
continuation :samp:`{[k-return]}` with the value (``4``).  That means
we return into the body of ``control`` with the value (``4`` -- still,
*phew*!) which we, uh, discard.

In this case, the body of ``control`` continues with whatever the
second ``...`` is and the value from that is what is returned by
``(thunk)`` in ``prompt*`` (we are returning from a function call for
the second time!) whereon ``abort-top!`` will invoke the continuation
on top of the list which should be :samp:`{[outer-k]}` and so
``prompt`` will return the value from the second ``...``.

There, `easy peasy lemon squeezy
<https://en.wiktionary.org/wiki/easy_peasy_lemon_squeezy>`_!

However, let's back up and look at another couple of examples.

In that last example, where we called :samp:`{k} 3` and the code had
returned ``4`` from ``(thunk)`` and ``abort-top!`` invoked
:samp:`{[k-return]} 4` then ``holes`` is back to a list with a single
hole, from ``prompt*``: :samp:`(({[outer-k]}))`.

That is, of course, exactly the same state as when ``control``'s body
was first run.  In other words, any subsequent call to :samp:`{k}`
will be in the same state (of ``holes``) as any other.  Hence the
example from much earlier where we called :samp:`{k}` multiple times:

.. code-block:: idio

   prompt (1 + (control k ((k 3) * (k 4))))

Where each invocation of :samp:`{k}` will engineer a return back to
its own continuation with whatever the computed value of
:samp:`{delim-body}` is.

A more complicated case, without a useful example, is when
``holes-prefix`` does have a non-empty value.

Suppose ``holes`` was (somehow!) :samp:`(({hole2}) ({hole1})
({[outer-k]}))` when we start ``control``.  What happens then?

.. code-block:: idio

   prompt {
	   ...something adding holes...
	   1 +
		(control k {
			     ...
		             k 3
			     ...
			   })
	  )

(Technically the example above is missing some parentheses
but... *look!  a pony!*)

As we run through ``control*``, ``holes-prefix`` will be the reverse
of the holes in front of ``prompt*``'s hole.  It'll be
:samp:`(({hole1}) ({hole2}))` and ``holes`` is left with just
:samp:`(({[outer-k]}))`.

``invoke-subcont`` is unchanged other than that ``holes-prefix`` now
has a value.

``control*`` then invokes ``(f invoke-subcont)`` as before and ``f``,
``control``'s body, trots along until it reaches :samp:`{k} 3`,
ie. ``invoke-subcont 3``.

``invoke-subcont`` will push a hole with :samp:`{[k-return]}` on then
push on the entries in ``holes-prefix`` (re-ordering them).  That
means that, , ``holes`` will be :samp:`(({hole2}) ({hole1})
({[k-return]}) ({[outer-k]}))`.

We call :samp:`{[k-control]} 3` as before which will return from
``(thunk)`` in ``prompt*`` and be passed to ``abort-top!`` which will
pop the first hole off of the list, :samp:`({hole2})`.

*Yikes!* What does that do?  Something, I guess.  You also get the
impression that :samp:`(({hole2}) ({hole1}))` might well be of the
same ilk as :samp:`(({[k-return]}) ({[outer-k]}))` which we know how
they interoperate.  It looks like ``...something adding holes...`` was
another ``prompt``/``control`` pair (albeit such that they don't clash
with our pair, somehow!).

So I think we expect that :samp:`(({hole2}) ({hole1}))` will unwind
themselves leaving us with just :samp:`(({[k-return]}) ({[outer-k]}))`
in ``holes`` which we know will unwind in due course.

prompt-at/control-at
--------------------

``control`` defines the end-of-continuation for the nearest enclosing
``prompt`` which seems a little limiting for when we get going as no
doubt someone will throw an unfortunate ``prompt`` into
:samp:`{control-body}` and mess the whole thing up.

We can fix that by generalising ``prompt``/``control`` to
:samp:`prompt-at {tag}`/:samp:`control-at {tag}` allowing us to target
specific marked sections (and where ``prompt``/``control`` are simple
wrappers using some standard default tag).

The :samp:`{tag}`\ s are just some entity differentiable by, say,
``eq?``.  So you could use symbols or maybe pairs or structures or
something else.

for loop
^^^^^^^^

You can now imagine how easy it might be to write a :lname:`C`-style
``for`` loop together with the *control operators* ``break`` and
``continue`` (here as a derivative of the :lname:`Scheme` ``do``):

.. code-block:: idio

   for-loop-break-tag := make-prompt-tag 'for-loop-break
   (define-syntax break
     (syntax-rules ()
       ((break)   (break (void)))
       ((break v) (control-at for-loop-break-tag k v))))

   for-loop-continue-tag := make-prompt-tag 'for-loop-continue
   (define-syntax continue
     (syntax-rules ()
       ((continue)   (continue (void)))
       ((continue v) (control-at for-loop-continue-tag k v))))

   define-template (for var-clauses test & body) {
     split :+ function (clauses vars inits steps) {
		cond ((null? clauses) (list vars inits steps)) \
		     ((or (not (pair? clauses))
			  (not (pair? (ph clauses)))
			  (not (symbol? (phh clauses)))
			  (not (pair? (pth clauses)))) (error 'for "invalid syntax" clauses)) \
		     (else (split (pt clauses)
				  (pair (phh clauses) vars)
				  (pair (phth clauses) inits)
				  (if (null? (ptth clauses))
				      (pair (phh clauses) steps)
				      (pair (phtth clauses) steps))))
     }

     for-loop := gensym 'for-loop
     var+init+step := split var-clauses '#n '#n '#n
     v := ph var+init+step
     i := pht var+init+step
     s := phtt var+init+step

     #T{
       {
	 $for-loop :+ function $v {
			prompt-at for-loop-break-tag {
			  (if $test {
			    prompt-at for-loop-continue-tag {
			      $@body
			    }
			    $for-loop $@s
			  })
			}
	 }
	 $for-loop $@i
       }
     }
   }

We start be defining a couple of *break* and *continue* tags (a
``prompt-tag`` is a simple structure) and some syntax to let us use,
say, ``(break)``, itself transformed into :samp:`(break (void))`, in
user code which is transformed into :samp:`(control-at
for-loop-break-tag k {v})`.

.. sidebox::

   The expected-to-be-unused :samp:`k` for ``break`` and ``continue``
   should probably be ``gensym 'k`` to help debugging!

Note that these syntax transforms simply pass on :samp:`{v}` and,
assuming it doesn't contain :samp:`k`, means that the corresponding
``prompt-at`` will return :samp:`{v}`.

Of course, neither caller of ``prompt-at`` does anything with
:samp:`{v}` in this loop as ``break`` and ``continue`` are
:lname:`C`/:lname:`Bash`\ -type instructions and aren't expected to be
passing information around.

In the ``for`` template we split the variable initialisation and step
clauses up so we can use them in the right place in the same way as
:lname:`Scheme`'s ``do`` then the actual loop is simply augmented by a
couple of extra :samp:`prompt-at {tag}` clauses so that any use of
``(break)`` or ``(continue)`` in :samp:`{body}`, transformed into
:samp:`(control-at {tag} k {v})` will jump around the loop as
expected.

reset/shift
-----------

``reset``/``shift`` differ very slightly from ``prompt``/``control``
in how the `reduction rules
<https://docs.racket-lang.org/reference/cont.html#%28form._%28%28lib._racket%2Fcontrol..rkt%29._reset%29%29>`_
are defined.  Here, there is an extra ``reset`` around the captured
continuation, :samp:`{delim-body}`:

.. parsed-literal::

   reset (*delim-body* (shift k *shift-body*))
   reset ((function (k) *shift-body*) (function ([]) (reset *delim-body*)))

:socrates:`What does that mean?` Well, I confess, I'm a bit pushed to
give a trivial example of why the difference is useful.  In fact there
is only a difference if there are two (or more) ``shift`` operators
(like the multiple ``control`` operators example, above) where, in
essence, the "inner" ``shift`` is unable to "see" the "outer"
``reset`` (the original one you typed, if you like) because the
reduction rules have inserted an extra ``reset`` around the captured
continuation.

dynamic-wind II
^^^^^^^^^^^^^^^

However, considerably more usefully we can look at :ref-author:`Oleg
Kiselyov`'s `dyn-wind.scm
<http://okmij.org/ftp/continuations/dyn-wind.scm>`_ which uses
``reset``/``shift`` to first generate ``yield`` and then
``dynamic-wind``.

An :lname:`Idio` port of the *yield* parts looks something like:

.. code-block:: idio
   :caption: :file:`lib/delim-control.idio`

   yield-record-tag := make-ptag 'yield-record
   define (make-yield-record v k) {
     list yield-record-tag v k
   }

   (define-syntax try-yield
     (syntax-rules ()
       ((try-yield exp (r on-r) (v k on-y)) {
	 exp-r := exp
	 if (and (pair? exp-r)
		 (eq? (ph exp-r) yield-record-tag)) {
		   v := pht exp-r
		   k := phtt exp-r
		   on-y
		 } {
		   r := exp-r
		   on-r
		 }
       })))

   define (yield v) {
     shift k (make-yield-record v k)
   }

First of all, ``yield``, if invoked, is going to call :samp:`shift k
{v}` where :samp:`{v}` is a *yield record*, a list of three items,
:samp:`{magic} {v} k`:

* :samp:`{magic}` is just a magic number, here the name of a function,
  so we can subsequently identify such a *yield record*

* :samp:`{v}` is the value passed to yield so we can recover it

* .. sidebox::

     The continuation of ``yield``?  Why, it has generator written all
     over it!

  :samp:`k` is the continuation created by ``shift`` so we can invoke
  it should we want to.

For the main thrust we're defining a syntax template, ``try-yield``,
which looks a little confusing but has three arguments which I'll
describe in a slightly less confusing order which isn't helped by
meta-variable names being the same as variable names:

#. :samp:`{exp}` is some expression, to be evaluated, that might call
   ``yield``

#. :samp:`{v} {k} {on-y}` says that if the :samp:`{exp}`, when
   evaluated, returns a *yield record* then create the variable
   :samp:`{v}` to be the saved :samp:`{v}` in the yield record,
   :samp:`{k}` to be the saved :samp:`{k}` in the yield record and
   then evaluate :samp:`{on-y}` which, presumably, will make use of
   those newly created variables.

   :samp:`{v}` and :samp:`{k}` are usually ``v`` and ``k`` and
   :samp:`{on-y}` is a suitably twisty expression that invokes ``k``.

#. :samp:`{r} {on-r}` says that if the :samp:`{exp}`, when evaluated,
   is *not* a yield record then create a variable :samp:`{r}` to be
   the evaluated value of :samp:`{exp}` and then evaluate
   :samp:`{on-r}` which, presumably, will make use of this recently
   created value.

   It is quite often ``(r r)`` which is saying create the variable
   ``r`` (left hand one) with the value of :samp:`{exp}` and evaluate
   the expression ``r`` (right hand one) which, uh, returns us the
   value of :samp:`{exp}`.

``yield`` and ``try-yield`` aren't too tricky, albeit we could do with
distinguishing between meta-variables, the ``r``, ``v`` and ``k`` in
the syntax expression ``try-yield`` from what will almost certainly be
the supplied variable names ``r``, ``v`` and ``k``.

Now, before we move on we should note that ``try-yield`` and ``yield``
between them only mention ``shift``.  There's no ``reset``.  Someone,
somewhere, has to supply a suitably placed ``reset`` to make the whole
thing work.  Things start becoming less obvious with
:ref-author:`Kiselyov`'s ``dynamic-wind`` replacement,
``dyn-wind-yield``:

.. code-block:: idio
   :caption: :file:`lib/delim-control.idio`

   define (dyn-wind-yield before-thunk thunk after-thunk) {
     dwy-loop :+ function (th) {
		   (before-thunk)
		   res := (th)
		   (after-thunk)
		   (try-yield res
			      (r r)				; return the result
			      (v k {
				reenter := yield v
				dwy-loop (function () {
					    k reenter
				})
			      }))
     }

     dwy-loop (function () {
		 reset (thunk)
     })
   }

``dyn-wind-yield`` itself takes the expected *before*, *during* and
*after* thunks.  The main part of the function is the inner loop,
``dyn-loop`` which you can see invokes all three thunks in quick
succession -- albeit the *during* thunk is re-written as another thunk
which calls ``reset`` around the original.

At this point it isn't immediately obvious how simply invoking all
three thunks in succession handles any errors (hint: it doesn't, *per
se*, but we'll come back to that in a later section).

After all three thunks have been run we have a ``try-yield``
expression which uses the value returned from ``(th)`` as
:samp:`{exp}` and the normal ``(r r)`` form for the result if not a
yield and something a bit more complicated for the :samp:`{on-y}`
expression.

Although the :samp:`{on-y}` expression has a bit of familiarity.  In
the first instance this will only be run if ``(th)`` (and thus the
original ``(thunk)``) called :samp:`yield {v}` with some :samp:`{v}`.

It collects the result of invoking :samp:`yield {v}` (with the same
:samp:`{v}`) in ``reenter`` and invokes ``dwy-loop`` with a new thunk.
That thunk, when called as ``(th)``, calls that original ``yield``'s
continuation (saved as ``k``, you'll recall) with ``reenter``.
(Whether the point where ``yield`` was originally called chooses to do
anything with ``reenter`` is moot.)

Here, at this point, we can sort of envisage that, whatever was in the
original ``thunk``, we are now resuming where the call to ``yield``
was first made and passing it a continuation back to *here*.  That's a
bit like the :samp:`{[k-control]}` and :samp:`{[k-return]}` business
we saw earlier.

    As a side-track, though, this re-invocation of ``dwy-loop`` will
    have run both ``before-thunk`` and ``after-thunk`` again.  Are we
    really opening and closing file descriptors every time we run
    through the loop?

    Yes, which is part of the debate about what ``dynamic-wind``
    should be doing every time a protected block is re-entered.  In
    this case, file descriptors are a bit *who cares!* as if we run
    out it's our own (internal program logic) fault, usually.  If we
    drop a connection to a busy network service every time we
    ``yield`` then life gets a bit more interesting and we'd be
    thinking of some more esoteric *unwind-on-error* which everyone
    will complain about because it doesn't do what they want either.

Back on track, ``yield`` and ``try-yield`` look as though they work
well in tandem though, of course, having to create an appropriate
``try-yield`` expression every time you want a generator might be
asking for trouble.

"Native" Delimited Continuations
--------------------------------

Whilst working through some ideas about delimited continuations I
implemented some "native" delimited continuations in the sense that
they only maintain the height of the stack, not a copy of the stack.

These are the sorts of things that are good for one-shot rewinds as
they have no ability to re-create the stack as was, only to truncate
it.

The problem is, though, what do we do with all the "holes" we've been
creating?  One the one hand, do we do any unwinding and on the other
hand if we did revert the stack, presumably the "holes" were in some
state at that time as well?

True enough to the latter question, so the "holes" become part of the
dynamic state of the program and are stuffed away in the *thread*
value.  It also means that any continuation has to save (and restore
when invoked) that list of holes as was for that moment in the
program.

How to handle unwinding comes next.

.. include:: ../../../commit.rst

