.. include:: ../../global.rst

*********
Expansion
*********

One of the evaluator's tasks is to expand templates and then evaluate
the result of that expansion.  This process occurs immediately on
discovery of the *use* of a template and can use any :lname:`Idio`
function (or template) defined so far.

Let's just say, it gets a little involved....

Template Definition
===================

Defining a template is straightforward enough.  It's a function that
takes some arguments (unevaluated from the application of the
template), does whatever it wants then returns some "code."  Given
that we're in that weird world of :term:`homoiconicity`, the "code"
looks like a list of lists of lists etc..

Within those lists we can ask for expressions to be evaluated and the
results of that evaluation to be substituted in place.  That's
beginning to sound complicated, let's try an example.  I'll use the
non-operator style inside the ``#T{...}`` construct to avoid the
reader confusing matters by re-writing infix expressions:

.. code-block:: idio

   define-template (my-plus-two sym val) {
     var := string->symbol (append-string "my-" (symbol->string sym))

     #T{
       := $var $(+ val 2)
     }
   }

   my-plus-two bob 3

The template, ``my-plus-two``, takes two arguments, a symbol and a
value (yes, we haven't done any checking).  We create a local
variable, :samp:`{var}`, which is the "symbolification" of the string
concatenation of ``"my-"`` and the "stringification" of the symbol
passed in.

The "code" we return inside the ``#T{...}`` construct wants to be an
assignment operator, the value of the :samp:`{var}` variable and then
the value of the expression :samp:`(+ {val} 2)`.

The overall result of which is that we would expect the call to the
template, ``my-plus-two "bob" 3`` to result in the "code":

.. parsed-literal::

   := my-bob 5

Quasiquotation
==============

It's not quite that easy, though, and here we start getting a bit
*meta*.  There's going to be two evaluations, for a start!

The ``#T{...}`` expression (``quasiquote`` in :lname:`Scheme`) is our
first port of call.  Ultimately it needs to produce some "code" from
the expression ``:= $var $(+ val 2)``, its body form(s).

There's a two step process, even here.  At some point the evaluator
will have recognised that this is a quasiquote expression, the ``#T``
bit should have been a clue.

#. we have to *expand* the quasiquote expression

   Here we're looking to recursively descend the expression toggling
   the state of "expansion" and returning a data structure for the
   evaluator to, er, evaluate into the desired result.

   Quasiquote expansion's job is *not* to evaluate anything but return
   a construction with the quoting figured out.  We'll use the
   evaluator afterwards to figure out what the resultant expression
   should be.

   The default state of quasiquotation is quoted.  You get back what
   you put in.

   However, if a (sub-)expression is "unquoted" then we should not
   quote it but rather allow it to be evaluated.  As we descend into
   this unquoted expression we will very likely encounter another
   quasiquoted expression in which case quoting is re-enabled, and so
   on.

   The final "code" will be a list of things but we're not there yet.
   We're in an intermediate stage, here, where we're merely toggling
   quoting on and off and entities like :samp:`{var}` and
   :samp:`{val}` are just symbols in the mix -- nothing in the
   quasiquote *expansion* knows anything about the *values* of
   :samp:`{var}` and :samp:`{val}`.

   That means the output of quasiquotation expansion should be
   something that, when evaluated, would construct a list (of lists
   ...).

   In our example, to construct that "code" by hand, knowing the
   expected result, *we* could have written the following:

   .. parsed-literal::

      list ':= *var* (+ *val* 2)

   Notice something subtle, here.  For a start we're not returning the
   final form, we're returning something that *creates* the final
   form.

   Secondly, the assignment operator is quoted but nothing else is.
   So, if we were to ask the evaluator to take a look at this we would
   expect it to be treated as a regular bit of source code in which
   those arguments will get evaluated as ``list`` is just a regular
   function.

   In which case it is the function ``list`` with arguments: the
   quoted *symbol* ``:=``, whatever :samp:`{var}` evaluates to plus
   the result of the evaluation of the expression :samp:`(+ {val} 2)`.

   .. rst-class:: center

   \*

   Of course, the fact that we knew the result and could figure out
   the condensed answer doesn't mean the quasiquotation expander can.
   Instead, it will plod through creating a result from much more
   fundamental parts, pairs:

   .. parsed-literal::

      pair ':= (pair *var* (pair (+ *val* 2) #n))

   which will result in the same thing.

#. Now, as noted above, if we ask the evaluator to figure out that
   expression then the evaluator is in a position to replace
   references to :samp:`{var}` and :samp:`{val}` with some variable
   references.

   By invoking ``idio_meaning()`` on the output of quasiquote
   expansion we get two benefits:

   #. ``idio_meaning()`` will descend all of the expression so that if
      the result of quasiquote expansion contained the use of another
      template then we will expand that template in turn.

      Templates calling templates calling...

   #. templates really are just regular functions, so :samp:`{var}` is
      a local variable in the body of the template and :samp:`{val}`
      is a parameter to the template

      Templates really only differ in that they are flagged as
      "expanders" internally so the evaluator can identify them, and
      that the value they return is itself evaluated in turn (we'll
      get to this!).

   In this case there are no addition templates, only expressions that
   need evaluating.  If we could peek halfway we'd now see:

   .. parsed-literal::

      list ':= *my-bob* (+ *3* 2)

   ``idio_meaning()``'s job is, normally, a pre-cursor to calling the
   code generator to generate some byte code, however, in this case,
   we're using it to figure out the intermediate code for the
   quasiquote expression on our behalf.

   When we return the result from ``idio_meaning()`` it'll just be
   like any other calculated chunk of intermediate code from any other
   expression.  The only novelty, here, is that we are using it on
   self-generated code rather than user-supplied code.

   As this will ultimately be sent to the code generator we'll end up
   with some byte code to run the code for :samp:`list ':= {var} (+
   {val} 2)` which, when run would result in:

   .. code-block:: idio

      (:= my-bob 5)

   a list of three elements: ``:=``, ``my-bob`` and ``5``.

   In other words, some *code*.

That's just the result of finding the meaning of the quasiquotation
expression, the result of the template invocation.

.. rst-class:: center

---

While we're tying ourselves in meta-knots, you can use quasiquotation
at any time.  There's a tendency to use it as the return value in a
template because of its code-generating nature but if you want it to
generate some code (unlikely) or a data structure (much more likely)
then it's just as good for you.  Suppose you wanted to construct an
element for an association list:

.. code-block:: idio

   Idio> var := 'my-bob
   my-bob
   Idio> val := 3
   3
   Idio> #T{ $var $(+ val 2) }
   (my-bob 5)

Of course you could have just called :samp:`list {var} (+ {val} 2)`
but where's the fun in that?

Re-Evaluation
=============

When you *use* a template, the body of the template is run (including
that final meaning of the quasiquotation expression) and, in this
case, we'll get back the "code" ``(:= my-bob 5)``.

There's still one last trick.  We've said all along that the *result*
of using a template will be evaluated.  So, we throw that resultant
"code," ``(:= my-bob 5)``, at the evaluator.  In other words we can
look at our original template invocation:

.. code-block:: idio

   my-plus-two bob 3

and imagine that it was replaced with:

.. code-block:: idio

   := my-bob 5

and the evaluator now runs on ``:= my-bob 5`` which will (finally!)
give us our desired assignment.

*Phew!*

Expansion Space
===============

When we're running a template expansion we're in a strange halfway
world of creating new source code -- something *you* did completely
separately from :lname:`Idio` with your favourite text editor,
:program:`cat`, right?

.. image:: https://imgs.xkcd.com/comics/real_programmers.png
   :target: https://xkcd.com/378/

-- and this code creation process may use a couple of tricky features.

On the one hand it may use some inter-call state variables, think
about giving every new class a unique identification number before it
piles a slew of accessor functions into your namespace.  That number
has to be kept somewhere, preferably where it isn't going to clash
with what the user is doing and, even more preferably, somewhere where
the user isn't likely to endanger it.

On the other hand, the expansion of this template might provoke the
expansion of another template.  The first template is now acting much
like the user in the first scenario, the second template should, by
rights, be running somewhere where the actions of the first template
and it will not interfere.  Especially so if this template in a
template is creating accessor functions left right and centre.

The answer to this recursive conundrum is to have template expansion
run in a new namespace/module, which we might call, ``*expander*``
which should be adjoint to the current module.  If another template
requires expansion from this first template then it should be run in a
module called ``*expander*`` adjoint to the first ``*expander*``
module.

We should see a tree of ``*expander*`` modules indicating the levels
of expansion we've attained.  This is an idea explored by
:ref-author:`Christian Queinnec` in :ref-title:`Macroexpansion
Reflective Tower` (:cite:`me-rt`).

We don't currently, we just get the one.  Play nicely, everyone!

Timing
======

Changing *what* is being unquoted makes all the difference to how the
resultant code behaves, so:

.. code-block:: idio

     #T{
       := $var (+ $val 2)
     }

will get you :samp:`pair ':= (pair {var} (pair (pair '+ (pair {val}
(pair 2 #n))) #n))` where only the evaluation of :samp:`{val}` will
occur, not :samp:`(+ {val} 2)` giving the final "code" of:

.. code-block:: idio

   (:= my-bob (+ 3 2))

Whether you want the value ``5`` or the function call ``(+ 3 2)`` is
up to how you want the assignment to perform.  In this instance,
integer addition makes little difference but would make a huge
difference if you were looking a key up in a table.  In one case the
key will be looked up at the time of compilation (probably bad) and
the other at run time (*probably* good).

.. rst-class:: center

\*

You don't normally get to see these quasiquotation expansions as they
are immediately thrown at ``idio_meaning()`` however a judicious call
to:
   
.. code-block:: idio

   idio_debug ("dq=%s\n", dq);

in ``idio_meaning_quasiquotation()`` is very helpful if you
subsequently type the ``#T{...}`` expression at the prompt.

Mechanisms
==========

Finding sources for template expansion is a little tricky, more so
since there are two phases: quasiquotation expansion and template expansion.

Quasiquotation Expansion
------------------------

In the :lname:`C` version of the evaluator I
implemented a version along the lines of the one in
:file:`lib/compiler.stk` in the STklos_ distribution, partly as I
could follow what it was doing.  I see that there's a very similar
implementation to the STklos one in :file:`lib/init-7.scm` in
:ref-author:`Alex Shinn`'s :ref-title:`Chibi-Scheme`.

:ref-author:`Nils M Holm` opts for a double function solution in
:ref-title:`S9fES` in ``qq-expand``.  A rummage on the Intertubes
leads you to the appendix of :ref-author:`Alan Bawden`'s
:ref-title:`Quasiquotation in Lisp` paper (:cite:`qq-in-lisp` --where
I can't find a published date nor publisher) where he disparages
:lname:`Scheme` implementations of the day for using ``cons``
(``pair`` in :lname:`Idio`) because it won't handle nested
quasiquotations containing splicing properly.

In the interests of fairness, I've implemented the QiL variant (which
uses ``list`` and ``append``) in the :lname:`Idio` variant of the
evaluator.

The QiL solution, slightly reworked looks like:

.. code-block:: idio
   :caption: file:`evaluate.idio`

   define (qq-expand-list e) {
     if (pair? e) {
       sym := ph e
       (cond ((eq? 'unquote sym)	  #T{ (list $(pht e)) })
	     ((eq? 'unquote-splicing sym) (pht e))
	     ((eq? 'quasiquote sym)	  (qq-expand-list
					   (qq-expand (pht e))))
	     (else			  #T{ (list (append
						     $(qq-expand-list (ph e))
						     $(qq-expand (pt e)))) }))
     } {
       #T{ '($e) }
     }
   }

   define (qq-expand e) {
     if (pair? e) {
       sym := ph e
       (cond ((eq? 'unquote sym)	  (pht e))
	     ((eq? 'unquote-splicing sym) (error 'qq-expand "illegal"))
	     ((eq? 'quasiquote sym)	  (qq-expand
					   (qq-expand (pht e))))
	     (else			  #T{ (append $(qq-expand-list (ph e))
						      $(qq-expand (pt e))) }))
     } {
       #T{ '$e }
     }
   }

which, let's be honest, looks a bit intimidating.

Template Expansion
------------------

For the ``template-expand`` and ``template-expand*`` functions I've
followed in the style of STklos' :file:`lib/runtime.stk` which itself
appears to be following in the style of :ref-author:`Dybvig, Friedman
and Haynes`' :ref-title:`Expansion-Passing Style: A General Macro
Mechanism` (:cite:`eps`).

In essence, we pass the expression to be expanded, :samp:`{x}`, and an
"expansion" function, :samp:`{e}`, around to everything -- by passing
:samp:`{e}` it is the "expansion" passing style.  :samp:`{e}` only
really gets used in ``application-expander``.

The entry point for expansion is always ``initial-expander`` and the
nominal value for :samp:`{e}` is also ``initial-expander``.

``initial-expander`` looks at the expression and decides if it is:

* an atom -- return it

* a template -- use the template's associated function to do the
  expansion

* or we call ``application-expander``

application-expander descends into :samp:`{x}` and asks :samp:`{e}` to
expand each element -- of course we pass :samp:`{e}` into the
expansion otherwise it wouldn't be EPS!

:samp:`{e}` doesn't have to be ``initial-expander``.  The EPS paper
suggests an ``expand-once`` function with a do-nothing :samp:`{e}`:

.. code-block:: idio
		
   define (expand-once x) {
     initial-expander x (function (x e) x)
   }

thus preventing the recursive descent.



.. include:: ../../commit.rst

