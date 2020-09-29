.. include:: ../global.rst

***************
Advanced Scheme
***************

Much of what we've seen so far has been slightly different ways of
expressing the same things as other languages.

Can we go a bit deeper?

Syntax Transformers
===================

As suggested previously, this is the word of macros.  The basic
premise is that you can determine some minimalist or comfortable
expression and a macro can re-write your code into proper
:lname:`Scheme`.

It's not so far from, say, :lname:`C` pre-processor macros except you
don't have to figure out what the list and string manipulation
limitations of the :lname:`C` pre-processor are, you have the full
power of :lname:`Scheme` at your disposal.  Including, of course,
other macros.

To be fair, raw macros are "a bit tricky" so people have gone a bit
meta and written syntax transforming macros for you to use.  These let
you, in turn, create syntax transforming macros.  It seems a bit
redundant but the syntax transforming macros limit what you can do
with the idea being to keep people away from the real deal when they
don't need to be there.

let
---

``let`` is a macro, it is a syntax transformer.  Here's how.

Just to make you hate the parenthesis a little bit more, our
evaluation model for :lname:`Scheme` says that functions are invoked
when they are the first element in a list and we've said that
``lambda`` is a function constructor.  Let's combine the two.  So the
``func`` in:

.. parsed-literal:: 

 (*func* *args*)

can be replaced with a ``(lambda ...)`` construction:

.. parsed-literal:: 

 ((lambda *formals* *body+*) *args*)

The number of arguments in ``args`` should clearly match the number of
formal parameters in ``formals``.

Can we work an example?  How about a function that adds two numbers:

.. code-block:: scheme

 (lambda (a b) (+ a b))

or, in a more common styling:

.. code-block:: scheme

 (lambda (a b)
  (+ a b))

This is constructing a function value which takes two formal
parameters, ``a`` and ``b``, to be in scope for the extent of the body
forms.  It has a single body form, ``(+ a b)`` the result of which is
what the function will return.

Like a more obvious example, say, ``(+ 1 2)``, had this function been
bound to the symbol ``add`` we would have happily invoked ``(add 1
2)`` where ``add`` is going to evaluate to a function value.  A
function value is just the thing we created with ``lambda``.  So put
it all together:

.. code-block:: scheme

 ((lambda (a b) (+ a b)) 1 2)

(I told you you wouldn't like it.)

There's a lot of visual clutter there to figure out it is saying:

.. parsed-literal:: 

 (*func* 1 2)

and we haven't made the arguments complicated expressions at all!

But that *is* what it is saying and so the function value, created on
the hoof, is applied to the arguments and we get a result.
(Hopefully, 3!)

:socrates:`Where does this errant nonsense with on-the-fly function
values get us?`

``let``, of course!  (The clue was in the heading...)

Consider a ``let`` statement:

.. code-block:: scheme

 (let ((a 1)
       (b (* 2 3)))
   (+ a b))

In the ``bindings`` we said each binding was a list containing a
symbol and an expression, so our symbols are the ``car``\ s of each
binding, ``a`` and ``b``, and the expressions are the ``cadr``\ s,
``1`` and ``(* 2 3)``.

So a syntactic transformation of ``let`` could walk down the list of
bindings putting the ``car`` of each binding into a list of symbols
called, say, ``formals``, and the ``cadr`` of each binding into a list
of expressions called, say, ``args``.  The ``body+`` forms look like
they're going to be handled the same way in a ``let`` as in a function
so we can easily transform the ``let``:

.. parsed-literal::

 (let ((*formal1* *arg1*)
       (*formal2* *arg2*))
  *body+*)

in the first case into a function definition:

.. parsed-literal::

 (lambda (*formal1* *formal2*)
  (begin *body+*))

and then into a function call form by putting the function definition
as the first element and the arguments to be evaluated as the
remaining elements:

.. parsed-literal::

 ((lambda (*formal1* *formal2*) (begin *body+*)) *arg1* *arg2*)

And, lo!  ``let`` has been transformed into an on-the-fly function
call.

This transformation also explains why ``let`` does not allow you to
re-use a formal argument in the definition of another as ``arg1`` and
``arg2`` are presented as independent values to the function.
``arg2`` cannot *use* ``arg1`` because ``arg1`` exists only as a value
not as a name bound to a value that you can reference.  ``arg1`` is
not usable as ``formal1`` until *inside* the function.

No one expects to be able to write the following in :lname:`C`:

.. code-block:: c

  int main (char **argv, int argc = length(argv))

where one formal parameter is derived from an earlier one.  The formal
parameters are independent and, so far as you can tell (from inside
the function), created in parallel.

Why are we doing this anyway?  What was wrong with plain old ``let``?
In principle, nothing, in practice it means we have to support two
different ways of introducing variables into scope.  With a syntax
transformation like this we only have to support function calls.
``let`` vanishes.

In some sense it is much like any transformation of an iterative loop
into a tail recursive loop (or *vice versa*) which might be more
convenient for your language to support.

Let Variant
-----------

``let`` has another funky form:

.. parsed-literal::

 (let *name* *bindings* *body+*)

which really needs an example to understand.

.. code-block:: scheme

 (let foo ((f1 e1)
           (f2 e2))
  body+)

gets transformed into:

.. code-block:: scheme

 (letrec ((foo (lambda (f1 f2))
		body+))
  (foo e1 e2))

:socrates:`Eh?  What's happened there and what's that doing?`

Look carefully.  We've done a similar trick with the bindings.
Firstly, the symbols have become the formal arguments again but,
rather than for an anonymous function, this time for a *named*
function, ``foo``.  Secondly, rather than apply the anonymous function
to the arguments we've called the named function with those arguments.

What we've done is declared a (usually self-recursive, hence
``letrec``) function called ``foo`` which takes formal parameters,
``f1`` and ``f2``, and we *automatically called* it with arguments,
``e1`` and ``e2``.

So we've declared and invoked a function in one statement.  It seems a
bit... *exciting* ...although not a million miles removed from the
standard ``let``.

However, it's actually really useful.  You recall that :lname:`Scheme`
prefers a recursive loop and there's any number of occasions when we
want to loop over something, counting, filtering, whatever and this
``let`` form allows us to declare a loop function (that can
self-recurse) and kick it off with some starting values.

.. code-block:: scheme

 (define stuff '(1 "two" 3 'four))

 (let numbers ((ls stuff)
               (r nil))
  (if (null? ls)
      (reverse r)
      (numbers (cdr ls) (if (number? (car ls))
			    (cons (car ls) r)
			    r))))

The function ``numbers`` is defined as taking formal parameters ``ls``
(for the "current" value of the list) and ``r`` (for the accumulated
result).  ``numbers`` is initially called with ``stuff`` and ``nil``.

The body of the function is a single ``if`` statement where it asks,
is ``ls`` an empty list?  If so return the reversed value of ``r``
(seems a bit odd).

Otherwise, recursively call ``numbers`` again with the tail of the
list (ah, clever) and the result of another ``if`` statement.

This second ``if`` statement is checking to see if the head of the
list is a number with ``number?``.  If it is then prepend the head of
the list to ``r`` otherwise just use ``r`` as it is.  So, as we walk
down the original list, ``stuff``, left to right, if the head of the
list is a number we create a new ``r`` which has this most recent
value prepended to it.  Hence the need to reverse the final result.

It is a different way of thinking.

For what it's worth, the iterative variant would look something like:

.. code-block:: scheme

 (define stuff '(1 "two" 3 'four))

 (let ((ls stuff)
       (r nil))
  (while (not (null? ls))
   (if (number? (car ls))
    (set! r (cons (car ls) r)))
   (set! ls (cdr ls)))
  (reverse r))

Horses for courses, I suppose, though the use of ``set!`` will upset
the purists.

Just to keep you on your toes, as :lname:`Scheme` *is* tail-call
optimised then it makes sense to transform any iterative calls, like
``while``, into tail recursive calls as originally penned.  Then we
have the discomfort of re-working the user's ``set!`` calls inside our
elegant recursive function.  *Bah!*


Macros
------

.. epigraph::

  Thar be Dragons!

  --- *everyone*

A macro, which is ostensibly a regular function, is created using a
special form, ``define-macro`` that tags your function's name as a
macro.  This tagging function clearly has to have hooks into the
backend because, having looked out for all the special forms, the
:lname:`Scheme` engine will check to see if the function name for a
form is tagged as a macro and if so it does not evaluate the arguments
but passes them onto the function/macro as is (atoms, lists).  The
macro can then poke about with its arguments as it sees fit and return
some value.

The trick with macros is that the returned value must be something
that can be immediately re-evaluated -- so the return value must be an
atom or a list.  Macros, then, are code generators.

A great example is the production of boilerplate code.  Given a
``name`` we might want to produce a host of related functions that do
``name``-related stuff.  Imagine some object-oriented system where you
might want to define a class which has a parent class and some
fields:

.. parsed-literal::

 (define-class *name* *parent* *field+*)

Who, in their right minds, wants to type in the constructor:

.. parsed-literal::

 (define make-*name* (args)
   ...
   *parent*
   ...)

and accessors for the arbitrary number of fields:

.. parsed-literal:: 

 (define *name*-*field1* (o)
   *field1*
 )

 (define set-*name*-*field1*! (o v)
   (set! *field1* v)
 )

and a predicate:

.. parsed-literal:: 

 (define *name*? (o)
   ...
 )

and whatever else is necessary for every class where all the ``...``
are tracts of code that are identical across all classes when you
already have ``name``, ``parent`` and all the field names in your
hands?  The ``define-class`` call has been given everything it needs
to know, the rest of it should get built automatically.

To help create those chunks of code the Schemers have come up with
:ref:`quasiquoting <quasiquoting>` and, normally, a macro will return
a quasiquoted expression:

.. parsed-literal::

 (define-macro (*name* *formals*)
  ...do any prep work...
  *quasiquoted-expression*)

.. _quasiquoting:

Quasiquoting
^^^^^^^^^^^^

Literally quoting things, ``'``, doesn't let us do much in the way of
substituting in values, well, not without a struggle:

.. code-block:: scheme

 (let ((a 1))
   '(a 2 3))

returns ``(a 2 3)`` which is probably not the ``(1 2 3)`` you wanted.
You could try:

.. code-block:: scheme

 (let ((a 1))
   (list a 2 3))

which is fine but will itself start to get rather long winded and
you'll have to explicitly quote all of the other arguments that don't
want evaluating.

Instead we can *quasiquote* things where, like variable interpolation
in strings in the shell, eg.:

.. code-block:: bash

 echo "this is $0"

will iterate through its argument expression looking for *unquoting*
expressions otherwise leave things quoted just like ``quote``:

.. code-block:: scheme

 (let ((a 1))
   (quasiquote ((unquote a) 2 3)))

Here, ``quasiquote``’s argument, ``((unquote a) 2 3)``, is a list of
three elements, the first is an unquote expression so ``quasiquote``
will evaluate the argument to ``unquote`` and replace the unquote
expression with the result of the evaluation.  The other two arguments
remain quoted. Evaluating ``a`` results in the number value *1* hence
the result of the quasiquote expression is ``(1 2 3)``.

Like ``quote``, ``quasiquote``’s result will **not** be evaluated.
:socrates:`Eh?  Isn't that the point?` Not quite.  What we want to do
is return what the user might have typed, the :lname:`Scheme` engine
can then choose to evaluate it or not.

``quasiquote`` and ``unquote`` have reader macros similar to
``quote``'s ``'`` which are :literal:`\`` (backquote/backtick) and
``,`` (comma) respectively.  We could have written the above example
as:

.. code-block:: scheme

 (let ((a 1))
   `(,a 2 3))

So ``unquote``/``,`` is very much like variable interpolation in the
shell, with ``quote``/``quasiquote`` akin to the use of single quotes
or double quotes in the shell.

One important difference, though, is that it is an *expression* that
is evaluated not simply evaluating a variable:

.. code-block:: scheme

 (let ((a 1))
   `(,(a+ 5) 2 3))

will return ``(7 2 3)`` (assuming we still have the previous
definition for ``a+`` floating about).

There is another unquoting expression, ``unquote-splicing`` (with a
reader macro of ``,@``) which expects its argument expression, when
evaluated, to be a list then it will splice the elements of that list
into the quasiquote expression whereas ``unquote`` would have simply
inserted the list as a single entity.  Given:

.. code-block:: scheme

 (define b '(1 2 3))

Then:

.. code-block:: scheme

 `(a ,b c)

returns ``(a (1 2 3) c)`` whereas:

.. code-block:: scheme

 `(a ,@b c)

returns ``(a 1 2 3 c)``.

It goes without saying that real macros are not trivial examples like this.  In practice the ``a`` in

.. code-block:: scheme

 `(,a 2 3)

is likely to be an expression and surprisingly commonly it is a
``map`` where each time round the loop you will be generating another
quasiquoted expression.  Think about the ``field+`` from the class
suggestion above.  The engine doesn't know how many field names you're
passing in so it must use a loop.  Of course, ``,`` isn't ideal for
handling the list of results from ``map``, we probably want ``,@`` to
splice in the results to the output of the macro:

.. code-block:: scheme

 (define-macro (define-class name parent field+)
  ...class prep work...
  `(
    ...quasiquote with ,name ,parent etc...
    ,@(map (lambda (field)
            ...field prep work...
	    `(...quasiquote with ,field ,name etc...))
	    field+)
   ...
   ))

(The prep work is likely to be creating symbols from combining the
symbols for the *name* and *field* variables and so on.)

Probably the most subtle misstep people take is that macros are
expanded "at compile time" (whatever that is but you get the
impression that it's not an ideal time).  Which, in turn, should
really say that macros are expanded (recursively and in a separate
evaluation-space) before the resultant program is evaluated.  In fact,
it's even more complicated than that as if a macro defines and uses
macros itself then those macro-macros live in a meta-evaluation space
and another level again if those macro-macros define and use
macros....

Macro Issues
^^^^^^^^^^^^

.. sidebox:: Yes, I'm looking at myself.

The three primary problems with macros are:

#. you forget its arguments are not evaluated -- so you can't *pass a
   variable* you've calculated

#. you forget it is run at compile time -- your variable *doesn't
   exist* anyway

#. you're a dirty hacker

The latter point (probably well made) is about *hygiene*.  If your
macro is off generating code then you're likely as not going to be
using some variables.  Variables, of course, are names which, unless
you've washed your hands carefully, are going to get in the way of the
real program's variables.

Suppose we wanted to define some logical-or functionality where you
would evaluate a pair of forms in sequence until one of them returned
a non-false result and then you would return that result.  As we're
not going to evaluate all the arguments (forms) before invoking the
function we must define a macro:

.. code-block:: scheme

 (define-macro (my-or e1 e2)
   `(let ((tmp ,e1))
      (if tmp
          tmp
          ,e2)))

which looks good.  We've even been smart enough to use a temporary
variable, ``tmp`` so that ``e1`` is only evaluated once in the
enclosed ``if`` statement.  Less smart users would have written:

.. code-block:: scheme

 (define-macro (my-or e1 e2)
   `((if ,e1
         ,e1
         ,e2)))

and if ``e1`` had been ``(honk-horn)`` then their macro would have expanded out to:

.. code-block:: scheme

 (if (honk-horn)
     (honk-horn)
     ...)


and they'd have heard "*parp!* *parp!*".  Hah, suckers!

In the meanwhile our sophisticated winning solution for:

.. code-block:: scheme

 (my-or "this" "that")

will expand to:

.. code-block:: scheme

 (let ((tmp "this"))
   (if tmp
       tmp
       "that"))

which wins all the plaudits until someone types:

.. code-block:: scheme

 (let ((tmp "foo"))
   (my-or #f tmp))

The macro is expanded thusly:

.. code-block:: scheme

 (let ((tmp "foo"))
   (let ((tmp #f))
     (if tmp tmp tmp)))

Yikes!  ``(if tmp tmp tmp)``?  Which ``tmp`` is which?

This problem is solved by using *hygienic* macros -- actually macros
are still macros but rather the macro writer uses a little code trick
to inject a unique variable name in the prep work:

.. code-block:: scheme

 (define-macro (my-or e1 e2)
   (let ((tmp (gensym)))
     `(let ((,tmp ,e1))
        (if ,tmp
            ,tmp
            ,e2)))

Here, we used ``gensym`` (generate symbol!) to come up with a unique
symbol that cannot conflict with anything else.  ``tmp``, now a
regular locally-introduced symbol during the evaluation of ``my-or``
(albeit in "compile-time macro-space" -- do keep up at the back!), is
bound to that unique symbol value and, having been defined in the
outer ``let``, can be unquoted and evaluated (becoming the unique
symbol) inside the ``quasiquote`` expression.

So, ``tmp`` will have the symbol value ``G707``, say, and the result
of the macro, the last form, the ``quasiquote`` expression will look
like:

.. code-block:: scheme

 (let ((G707 e1))
   (if G707
       G707
       e2))

If we called ``my-or`` again, ``tmp`` would be bound to a new (unique)
symbol value, ``G713``, say, and we'll end up with a similar expansion
but one that did not conflict -- which means we could have ``my-or``\
s inside ``my-or``\ s without the per-invocation local ``tmp``
variables colliding (as they never appear in the expanded code).

However, macro writers are not perfect and hygiene is difficult to
ensure so much work has been made to remove risk from macro writing.
There have been two thrusts: ``syntax-rules`` and the more advanced
``syntax-case`` both of which have pattern matching at their hearts.
Mind you, the latter is so complicated that it requires a 30,000 line
pre-built version of itself to bootstrap!

The broad idea of both is to re-imagine macros as syntax transformers
(which they always were...) within strict limitations (that's the
key).  Elements of the macro calls are tagged and the tags are managed
so that no unhygienic variables are introduced.  (Unless you really
really want to!)

Closures
========

Let's try a more dynamic variant:

.. code-block:: scheme

 (define a 1)

 (let ((ab+ (let ((b 3))
	     (lambda (n)
	      (+ a b n)))))
  (ab+ 5))

:socrates:`Cripes!  What's happening here?` The inner ``let``'s body
is a function constructor (``lambda``) and so the inner ``let`` is
returning a function *value*.  The function is using ``n``, a formal
parameter, ``b``, a variable introduced by the inner ``let``, and
``a`` from the top level.

The outer ``let`` is binding that function value to the symbol ``ab+``
which is called in the outer ``let``'s body.  The result (from the
outer ``let``) should be 9, the sum of ``a``, ``b`` and ``n``.

But wait!  ``b`` isn't in scope in the outer ``let``!  No it isn't,
but the function value in the inner ``let`` was closed over ``b``
trapping it, if you like, within its body.  We can't access ``b`` in
any sense from ``ab+``, other than the fact that it is *used* inside
``ab+``, so there's no risk of ``b`` being used *directly* outside of
its bound scope.  We can't *change* it, it is stuck forever bound to
the value 3.

So we have here the idea of enclosing the access to a variable inside
a function.  If the code was different, could we *modify* such a
closed variable?

Yes, of course.  This idea of, in effect, creating a *private*
variable is as common in :lname:`Scheme` as anywhere else.  You might
want to keep a counter such that every time your closure was called it
incremented the private variable and returned the result.  You might
want to maintain a list of *stuff*.

The critical part of this trick is that *only this function* has
access to this variable.  There is no other way for anything to use it
or modify it.  It is completely private.

You can extend this idea to enclosing a suite of functions over a
common set of variables which the functions co-operatively maintain.
Clearly you can't return multiple function definitions from a single
``let`` but you can play a similar trick to ``letrec``:

.. code-block:: scheme

 (define this #f)
 (define that #f)

 (let ((private 0))
  (set! this (lambda ...))
  (set! that (lambda ...)))

Both of the functions bound to ``this`` and ``that`` have global scope
(because the names were declared at top level with ``define``) and
both of the function values have access to ``private`` (because they
were created in the scope of ``private``).  No-one else has access to
``private`` other than through the interfaces, ``this`` and ``that``.

This is about as complicated as it gets!  (Well, when I say that...)

Ports
=====

:lname:`Scheme` uses *ports* to describe things that you can read from
and write to.  The obvious use case is files.

In the pernickety way of :lname:`Scheme` there are separate functions
to open files for reading and writing: ``open-input-file`` and
``open-output-file``.  After that you can read, write, check for
end-of-file, close, "seek", "tell" and so on.  All the usual things.

On top of that :lname:`Scheme` has the notion of the *current* input,
output and error ports.  Obviously, maybe, those start off being the
usual *stdin*, *stdout* and *stderr* that we're used to.  However,
there are common idioms to temporarily switch those noting that many
functions are well aware that they might be switched and will
rigorously ask for the *current* input, output or error port.

This little snippet from :ref-title:`S9fES` (:cite:`S9fES`) combines
several techniques to create a function that takes a file name and a
:ref:`thunk <thunk>` then switches the current input port to the newly
opened file, runs the thunk, saving its result, closes the file,
resets the input port and returns the saved result:

.. code-block:: scheme

 (define with-input-from-file
   (let ((set-input-port! set-input-port!))
     (lambda (file thunk)
       (let ((outer-port (current-input-port))
             (new-port (open-input-file file)))
         (set-input-port! new-port)
         (let ((input (thunk)))
           (close-input-port new-port)
           (set-input-port! outer-port)
           input)))))

Most programming languages have the capability to manipulate files in
a similar fashion.  We're not breaking new ground, here.

.. _`string ports`:

String Ports
------------

This is a bit more interesting.  Instead of ports meaning an interface
to files, how about an interface to *strings*?

:socrates:`Eh?`

For an *input* string port you need to be able to:

- *open* one -- that means wrappering an existing string with a port
  construct to give it the *port* interfaces

- *read* from one -- we can probably get characters from a string,
  right?  All we have to do is maintain a pointer to where we've read
  so far in the string.

- check for *EOF* -- are we at the end of the string yet?

- *close* one -- stop using it?

- *seek* and *tell*?  Well those sound like jumping about to different
  indexes in the string, setting or returning the current pointer into
  the string.  Can't be that hard.

As it is an *input* port then all write operations should fail on
principle.

For an *output* string port we need a little more trickery under the
hood:

- *open* -- requires an output port construct where the underlying
  string is extensible.

- *write* -- every time we write to the output string port we *extend*
  the underlying dynamic string.

- check for *EOF* -- is that meaningful?

- *close* -- stop using it?  Maybe set a flag.

- *seek* and *tell*?  Well those sound like jumping about to different
  indexes in the string -- so we should have been maintaining a
  current pointer into the string like above.  Can't be that hard.

As it is an *output* port then all read operations are invalid.
However, unlike files, where we have an (externally) examinable result
-- one we can call ``open-input-file`` on, if nothing else -- this
output string port is hiding the underlying string in memory.  We must
be able to retrieve our carefully crafted musings, hence,
``get-output-string`` which returns the (underlying) string from the
string port.

Maybe, at this point, string ports seem a little quixotic but, if
nothing else, you can recognise that if all kinds of ports are
maintaining the same interfaces then they should be interchangeable.
Where, previously, you might have been writing to a temporary file,
you can now be writing to a temporary string and you wouldn't know.
*Whoa!*

To be fair, that does rely on the code doing the writing to be
scrupulously honest and ask for the current output port if it is going
to write anything.  Which is why (most) :lname:`Scheme` functions do.

Error Handling
==============

.. sidebox:: I guess the name comes from the program state being in a
             particular condition, I'm not sure.

:lname:`Lisp`\ s do things a little differently, here.  Rather than
have "errors" or "exceptions" they have *conditions*.  Which have a
sort of class hierarchy feel to them as the different types of
conditions are (*looks for a better word but fails*) sub-classed from
one another.  *A* difference is that they are not restricted to errors
but users can create their own condition type (hierarchies) and such a
condition can be *signalled* (ie. raised) whenever the user deems that
a particular state of processing has occurred.

Mostly errors and exceptions, though.

A second, somewhat more profound difference, is where in the
evaluation the condition handler is run.  For most languages that have
some kind of exception mechanism, say :lname:`Python`'s ``try``
mechanism:

.. code-block:: python

 try:
     risky_command ()
 except Exception as e:
     print ("ERROR: risky_command() said: {0}".format (e)

you don't really know, and probably don't care, quite what
``risky_command`` was doing when it ``raise``\ ed the exception.  What
you do know is that, however deep into its evaluation stack it has
gone (think: how deeply nested the function calls in the ``risky``
library got), the evaluation stack is truncated back to here -- all
those function calls from ``risky_command`` through to the failure are
discarded, we call ``print`` and more on with our lives.

:lname:`Lisp`\ s don't go in for that, rather, the condition handler
is run *instead of* the failed function (that raised the condition).
It can choose how to proceed: return an appropriate value on behalf of
the failed function; call the next condition handler up; raise a
different condition.

Sometimes you do want to truncate processing in which case you need
continuations.

Nested Handlers
---------------

Your handler can be buggy (I know, unlikely) in which case who handles
that?  Whenever a condition handler is installed it sits first in the
queue, if you like, of handlers to be consulted when a condition is
raised.

Correspondingly, when a handler is run it is run in the context of the
next handler out.  In other words, you don't handle your own bugs!

Obviously this cascades back out to some system installed handlers --
which, you would like to think, are bug-free and can take anything in
their stride.

Restarts
--------

In concert with conditions, :lname:`Scheme` supports the idea of
*restarts*.  The idea is that the flow of the code gathers up a set of
labelled blocks of code called restarts -- in one sense a bit like
picking up variables defined in the source that you normally wouldn't
use.  When a condition is raised the condition handler is at liberty
to determine the set of restarts collected and make a decision about
whether to call one of them or not or revert to a higher (outer)
handler which might have a better view (or a better restart)
available.

If chosen, control is handed to the restart code block and the program
continues.  The trick being that, having repaired whatever mess had
been caused, it continues back into the code that raised the error in
the first place, this time, hopefully, continuing without error.

Consider a process managing backup files where the number of backup
files is less important than the amount of disk space they are using.
Eventually you will fill the disk which requires operator
intervention.

On the other hand, the "disk full" handler might identify there is a
"throw out the old" restart which we picked up before entering the
section to create backup files.  The restart can be called, have the
old backup files cleared out and then carry on back into the section
to create backups.

I, like many people, have written plenty of code to pro-actively
(although often, post-actively) trim the set of backup files but in
neither case is that code re-active.

Whether that's the right way to approach problem solving is another
question.

Continuations
=============

.. epigraph:: Timey-wimey stuff.

	      -- The Doctor

Continuations are the greatest idea in computing... that you've never
heard of -- despite using continuations all day every day!

They are also, possibly, the last thing you should be allowed to
touch.  So, noting we are curious but not cats, let's dive in!

I think I have an example that explains the idea of a continuation to
a non-continuation audience -- if not, it's going to be tricky.
Consider a little snippet of :lname:`C`:

.. code-block:: c

 ...
 int i = a + b * c;
 ...

There are (arguably) four continuations there, *four*!  Let's break it
down.  As a starter for ten, we know from :lname:`C`'s operator
precedence rules that ``a + b * c`` is really ``a + (b * c)`` that is,
the calculation of ``b * c`` is performed first and the result passed
to the next sub-expression, ``a + []`` -- with ``[]`` standing in for
the result of the previous sub-expression, ``b * c``.

In turn, the initialisation of ``i`` is waiting for the result of the
addition, so, in this style, it looks like ``int i = []``.  If we were
to rewrite our original snippet it might look like:

.. parsed-literal:: 

 ...
 b * c
 a + *[]*
 int i = *[]*
 ...

This is now looking like a little chain of sub-expressions where each
sub-expression generates a (single!) value ready for the next
sub-expression to use in turn.  Form the perspective of the ``b * c``
sub-expression, it will calculate its value then *continue* (aha!)
onto ``a + []``, therefore ``a + []`` is described as being the
continuation of ``b * c``.

``a + []``, in turn will calculate its value and continue onto ``int i
= []``.  ``int i = []`` is ``a + []``'s continuation.

:socrates:`You said four continuations?` Yes.  The continuation of the
line *before* ``b * c`` has a continuation too: it is ``b * c`` except
``b * c`` chooses not to do anything with the value provided by the
line before.

Similarly, ``int i = []`` has a continuation as well, the line after
it.  We can't see from this snippet whether the line after chooses to
use the value that ``int i = []`` provides.  (Which is itself an
interesting question, what is the *result* of an assignment?
Discuss.)

Each of these sub-expressions is a bit of code that is expecting an
argument then calls another bit of code, like a chain of
(continuation) functions.  We can re-fashion our snippet as (the
vastly uglier):

.. parsed-literal:: 

 ...
 k_l(v) { k_m(b * c); }
 k_m(v) { k_n(a + v); }
 k_n(v) { k_o(int i = v); }
 ...

Again, exactly the same thing is happening, ``b * c`` is now encoded
in ``k_l()`` and ignores the parameter, ``v``.  It calls ``k_m()``
with its calculated value.

``a + []`` is now ``k_m()``, it does use the parameter ``v`` and calls
``k_n()`` with the result.

``int i = []`` is now ``k_n()``, assigns the parameter ``v`` to ``i``
and (assuming you've figured out what the result of an assignment is)
passes its result to ``k_o()`` and the chain continues.

There's a variation called `continuation-passing style`_ (CPS) which
might look a bit like:

.. parsed-literal:: 

 ...
 k_l(v, k) { k(b * c, *k_n*); }
 k_m(v, k) { k(a + v, *k_o*); }
 k_n(v, k) { k(int i = v, *k_p*); }
 ...

where the continuation that you should pass your result to is passed
to you and you have to tell your continuation whom to call in turn.
That's looks "difficult" to create but it turns out to be easier than
you think.

.. sidebox:: At one point I went through the process of transforming
             my :lname:`C` implementation of :ref-author:`Bill Hails`'
             :lname:`Perl` interpreter and transformed it into a CPS
             version.  *Phew!*

	     You don't want to do that *too* often.

You can even go through a process of transforming your, say,
:lname:`C` code into a CPS program which, with your :lname:`C` hat on,
looks like you are in a never-ending chain of callbacks.  

Which is *exactly* what you are in!

Of course, you can't *be* in a never ending chain of callbacks because
your program will clearly(?) be in a tight loop.  At the end of the
chain is a NULL pointer (or some other sentinel value) which tells you
to stop.

(How you start and how you stop are another matter.)

In order to generate the chain, the way I like to think about it is
you start with your end-of-chain sentinel value.  Each splodge of code
you add is like a balloon inflating between where you are now and the
sentinel, with the new code scribbled over the (arbitrarily expandable)
surface.  For the next bit of code you again squeeze it in before the
sentinel but with the addition that the last code balloon no longer
points at the sentinel as its continuation but now points at the start
of the new balloon.

When you're done processing the source code you can call the first of
your balloons with some dummy value and the chain kicks off and will
trundle through, function calling function calling function.

OK, back on course.  So now we have a seemingly pointless rewrite of
our code into the tiniest sub-expressions each of which are doomed to
call the next sub-expression.  :socrates:`What have we achieved?` To
be honest?  Not much.

However, and this is the trick.  These continuation functions, taking
a value at a time, they look quite a lot like regular functions,
taking a value at a time.  Suppose I could ask for one of these
continuation functions then I could call it with some value of my
choosing, right?

Let's take, ``a + []``.  If I had access to ``k_m()`` then I could
call ``k_m(37)`` and then the program would continue from that point
onwards -- because everything is chained together and the links in the
chain cannot be reordered -- with ``k_m()`` calculating ``a + 37`` and
passing that result onto ``k_n()``.  I have dived into the middle of
the chain and inserted a value that ignores the (immediately) previous
calculation?  What happened to ``b * c``?  *Pfft!* Don't care, we're
continuing with 37.

Apart from that immediately previous calculation everything else is
the same.  The code still accesses the same lexical and global
variables, will call the same functions in due course, it's all
hard-coded into the program.  It has the same prior *state* every time
you (re-)call it.  *Meh!* Except not *quite* the same state if you
have modified one of those variables in the meanwhile.

.. sidebox:: I can understand if you don't quite *grok* this.  It
             takes a while.

*Whoa!* That's a bit weird.  So weird, in fact, that most languages
don't give you access to them.  Although, to be honest, it's more
likely because they can (and probably will) create *causal* havoc.

Once you've got a continuation (function) you can keep calling it.
*Wooo!*  Although that will get boring after a while.

Except when it's really cool.  Think about generators_ where you want
to go back and ask for the next value from a sequence without having
to have pre-created all values in advance.  Those require that the
generating function stop processing and yield a value and then when
you next call it the generator continues (hint, hint) from where it
left off.

The greater use of continuations is not, however, repeatedly calling
the same thing but rather for being able to jump to another point in
the program -- usually a local point but not always.  Indeed,
continuations have been called *programmatic gotos* with all the
baggage that goto incurs.

Jumping to another point in the code sounds awful but talk to me again
about:

- ``return`` in a function

- ``next``/``last`` or ``break``/``continue`` in ``while`` and ``for``
  loops

- ``try``/``except`` -- remember the ``risky_command`` example where
  all that stack of functions calls was discarded?  How did that
  happen?  Hint: non-local goto.

where you mess about with the natural control flow of the code?  Of
course, you might be so attuned to something like ``return`` that it
has never occurred to you that you are prematurely jumping out of the
flow of the code.  But ``return`` and ``next``/``last`` are only
jumping about in the loop/function?  Sure, but they're still jumping
about, something has to make that happen.

What we're saying here with continuations is that that ability to
decide on some kind of control flow jump is no longer the preserve of
the language implementers (for example, granting you ``return`` out of
the decency of their hearts) but instead is exposed to the user for
them to create their own.

In fact, continuations are capable of creating *any* control flow
structure.  *Any*.

:socrates:`OK, it sounds like a dangerous free-for-all, there must be
some constraints?` Yes, thankfully, you have to be able to get hold of
a continuation (function).

call/cc
-------

You can't get any old continuation -- that would be madness (though
there's probably some programming languages where you can).  In
:lname:`Scheme` you have to have passed *through* the continuation you
want to capture -- that clearly places a severe limitation on being
able to jump about.  On top of that it is caught with a slightly
confusing function, ``call-with-current-continuation`` or ``call/cc``
(a relief to everyone's keyboard, if nothing else).

``call/cc`` does exactly what it says on the tin.  It figures out *its
own* continuation and passes that to the function you supplied.  It
has called your function with the current continuation.  Can't fault
the name!

``call/cc`` calls the function with the continuation and, sort of like
a single form'ed body of a function, will return the value that the
function returns.  Confusing, eh?

Actually, that's even more annoying than at first blush.  What on
earth can I do with a continuation if it is just a parameter in a
function?  That's the least of your worries.  Your first problem is
*which* continuation are you capturing?

Remember our snippet of :lname:`C` where we had four continuations,
albeit just the two in our single line of code?

.. parsed-literal:: 

 ...
 b * c
 a + *[]*
 int i = *[]*
 ...

If we want to capture ``k_m()`` -- so we can jump in at ``a + []``
with a value -- we need to back-track a little and ask, whose
continuation is ``k_m()``?  Here, as we know, ``k_m()`` is the
continuation of ``b * c``.

Now, this is where it gets tricky.  We said ``call/cc`` will return
its own continuation to the supplied function and we want it to be the
continuation of ``b * c`` so we need to insert ``call/cc`` where ``b *
c`` currently is.

OK, so what happens to ``b * c``?  Recall that ``call/cc`` will call
the supplied function with the continuation and return the value the
function returns.  Aha!  So we can put ``b * c`` in the body of the
supplied function and that calculation will be returned by ``call/cc``
to its continuation which is ``k_m()``, ie. ``a + []``.

That sounds like a mess!  It is but it's a well-structured mess -- and
you get used to it.

Let's see if we can visualise that:

.. parsed-literal:: 

 func(k) { b * c; }

 ...
 call/cc (func)
 a + *[]*
 int i = *[]*
 ...

I've got a unary function (one-argument!), ``func``, whose body is the
calculation ``b * c`` so that's the value ``func`` should return.

We've also slipped in ``call/cc`` into the sub-expression stream *in
place of* ``b * c`` so that ``call/cc``'s continuation is
``k_m()``/``a + []``.

``call/cc`` should now call ``func`` with the argument ``k_m()``.
``func`` will calculate ``b * c`` and return it to ``call/cc`` which
will return it in turn to... ``k_m()``.

Yay! ... :socrates:`Yay?  Have we done anything there?` Hmm,
fortunately, no.  But that's the idea, we've managed to slip in some
continuation capturing code and we haven't changed a thing.
Definitely a big *wooo!* there, believe you me!

:socrates:`But I thought we were going to capture` ``k_m()`` `?` Well,
technically we did, in ``func``, except we didn't do anything with it.

It's not like we can do anything useful with it *in* ``func`` either.
Imagine if you called ``k`` in ``func``:

.. parsed-literal:: 

 func(k) {
           k (37);
           b * c;
	 }

.. sidebox:: Go straight to Jail.  Do not pass GO.  Do not collect
             £200.

Cool!  You will immediately *goto* ``k_m()`` with the value 37.  Not
only that, you will only *ever* call ``k_m(37)`` because continuations
are *control flow* operators.  It happens right there, right now.
``b * c`` is *never* going to be called.

The only *useful* thing you can do with a continuation inside the
function supplied to ``call/cc`` is save it in a variable with wider
scope.  Wide enough scope that you can call it sometime later.  A
variable with global scope is considered a bad place to store it as it
means that anyone at any time can jump straight back in with
``gvar(37)`` (or whatever you've called it).

Instead, you're probably going to be storing it a variable with the
least wide scope you can get away with to solve your problem
(doubtless there *will* be situations where global scope is
appropriate).  Think about the private variables discussed earlier.

Finally, we've been playing with the sub-expressions, what do we do in
the real code?

.. parsed-literal:: 

 func(k) {
  private_k = k;
  b * c;
 }

 ...
 int i = a + call/cc (func)
 ...

Sweet!

Naturally, Schemers don't like named functions because it's a one-use
function and we don't need to clutter the namespace -- and no need
when you can throw in a ``lambda`` expression and get those
parentheses going!

.. code-block:: scheme

 (let ((private-k #f))
  (let ((i (+ a (call/cc (lambda (k)
			  (set! private-k k)
			  (* b c)))))))
  (private-k 37))

Which looks cool (we'll gloss over the ``set!``) but will loop
forever.

The trouble is, the continuation that we've captured is part of the
lead up to the call to ``(private-k 37)`` the invocation of which
means we instantly appear to return from the ``call/cc`` function with
the value 37 and work our way through to the ``(private-k 37)`` line
whereon we instantly appear to return from the ``call/cc`` function
with the value 37 and work our way...

Oops.  Continuations, here, with a popular narrative of "call once,
return many times..." need some careful thought.

Another, annoying/entertaining example, whilst we're befuddling
ourselves is the innocent capture of the current continuation into a
top level variable:

.. code-block:: scheme

 (define top-level-k (call/cc (lambda (k)
			       k)))

which certainly sets ``top-level-k`` to *a* continuation.  We can call
that continuation with ``(top-level-k 37)`` whereon we return (again)
from ``call/cc`` with the value, uh, 37 which gets assigned to
``top-level-k``.  Oopsies, we've just trashed our saved continuation
on its first use.

I might have mentioned there are "issues" with poorly chosen
continuations.

Corner Cases
^^^^^^^^^^^^

Choosing to capture a continuation in the middle of a sequence isn't
quite fair.  What about our two "hidden" continuations, the one for
the line before and the one for the line after?

The line before's continuation is quite easy.  We know -- because
we're looking at the code -- that ``b * c`` doesn't use the value
passed from the previous expression so if we want to capture this
continuation then we can simply insert a dummy ``call/cc`` before our
line.  Dummy in the sense that its only job is to capture the
continuation but not provide any useful calculation.  In fact, it
*will* produce a result, what ever the result of the act of saving
``k`` is (you *have* figured out the result of assignment, right?):

.. code-block:: scheme

 (call/cc (lambda (k)
	   ...save k...))
 (set! i (a + (b * c)))

``k``, if invoked with any argument, will then start processing ``b *
c`` (which will ignore the value passed) and we continue cleanly.

The line after's continuation is more of a mixed bag.  From looking at
the code we might determine that the next statement does nothing with
the value from the previous statement in which case we can insert a
similar dummy ``call/cc`` or we realise that our ``(set! i (a + (b *
c))`` statement is in the middle of something else which is reliant on
the result in which case we need to wrapper the whole ``set!`` form in
``call/cc``:

.. code-block:: scheme

 (call/cc (lambda (k)
	   ...save k...
	   (set! i (a + (b * c)))))
 
where the value returned by ``call/cc`` (the value returned by
``set!``) is passed to whomever wants it.  ``k``, now, is in the
position of giving whomever a different value than whatever you've
spent all that time figuring out what the result of an assignment is.

Escapes
-------

We're familiar with (or have at least heard of!) various exception
handling memes:

- :lname:`Python`'s ``try``/``except``/``else``/``finally`` and proactive ``raise``

- :lname:`Java`'s ``try``/``catch``/``finally`` and ``throw``

But those are far from any complete set.  :lname:`Lisp`\ ers have
thrown a few more hats into the ring:

- ``(catch label form+)`` allowing during the execution of ``form+`` a
  ``(throw label form)`` which requires a *dynamic escape environment*
  (as those ``label``\ s are evaluated and then associated with
  continuations)

- ``(block label form+)`` and the corresponding ``(return-from label
  form)`` where ``label`` is *not* evaluated (ie. is a
  symbol/identifier) but still bound to a continuation but the
  combination is only available in a *lexical escape environment*.

- ``let/cc`` (and :lname:`Dylan`'s ``bind-exit``) support assigning a
  continuation to a dynamic variable

- delimited, composable continuations or *prompts*

  * ``shift``/``reset``

None of those support the idea of a ``finally`` clause.  The headline
solution to that is :lname:`Scheme`'s ``unwind-protect`` which is a
derivative of ``dynamic-wind`` which, despite being in the RnRS, is
probably the most subtle and hackiest thing I have seen.  So we *will*
implement it.

The implementation, though, requires several layers to support it
which we will get to in due course.

Continuations in C
------------------

Naturally, these abstract computer science notions are too high brow
for :lname:`C`.  Until you realise that :lname:`C` has had the same
tools since forever in :manpage:`setjmp(3)` and :manpage:`longjmp(3)`
and their signal-safe cousins :manpage:`sigsetjmp(3)` and
:manpage:`siglongjmp(3)` (probably all on the same man page!).

Indeed, there's a reasonable likelihood that :lname:`Scheme`'s
continuations are implemented using :lname:`C`'s
``sigsetjmp``/``siglongjmp``.

The Linux man page notes:

    In summary, nonlocal gotos can make programs harder to understand
    and maintain, and an alternative should be used if possible.

Wise words.

Compound Data Types
===================

There is a tendency for these to be implementation-specific but
broadly you can use the usual compound data types of strings, arrays
(or vectors), hash tables and structures.

Strings, perhaps unusually for :lname:`Scheme`, allow you to modify
them (*poor form!*).  I guess this is a commonly expected
functionality.  ``string-ref`` and ``string-set!`` are accessors.

Arrays and hash tables work much as you would expect with the element
accessor functions following a similar style:
``array-ref``/``array-set!`` and ``hash-ref``/``hash-set!``.

Structures
----------

Various :lname:`Scheme` implementations introduce the idea of
*records* (and have normalised the interfaces in various SRFIs).  It
is very much like the suggestions been given previously for creating
classes in that a structure has a type, defining its name and fields
(and possibly parent!) and then instances of that structure can be
created and passed around.

Accessor functions for the fields are created when the record type is
created giving you same style of names as above: commonly
``name-field1`` (omitting the ``-ref``) and ``name-field1-set!`` and
the like.

Object Orientation
==================

Object-oriented programming is often bound tightly to the concept of
message passing.  In the original :strike:`Klingon` Smalltalk_:

.. code-block:: smalltalk

 object <- message arguments

which you might imagine, in a :lname:`Scheme`-ly way, to look like:

.. code-block:: scheme

 (object message arguments)

which would be perfectly fine so long as we allow an object in
functional position -- remember that the first element in a list is
going to be applied to the remaining elements in the list.  So you
might think that should be:

.. code-block:: scheme

 (message object arguments)

although we've only just said we can call ``k(37)`` where ``k`` is a
continuation not a "real" function.  Quite what *is* allowed to be in
functional position in a :lname:`Scheme` form is becoming a little
greyer.

:ref-title:`EPLAiP` (:cite:`EPLA`) p.135, implements the former (in
*Perl*) in a straight-forward manner.  If the evaluated value in
functional position is an object then the first argument is assumed to
be an object-specific function, a method, and there's a mechanism for
looking up a method within the hierarchy of the class.  The method is
then applied to the arguments with the object itself bound to the
variable ``this`` (cf. ``self``) for the duration of the method.

On the whole, though, that's not very :lname:`Scheme`-ly which prefers
functions in functional position.

There's a second argument in favour of not using the message passing
idiom in that if there are multiple objects within the arguments then
only the *first* argument can be used to distinguish the call.  For
example, if we wanted to add two numbers together where we might have
a class hierarchy of ``Integer`` is a ``Real`` is a ``Number``, then:

.. code-block:: scheme

 (add Number1 Number2)

we only get to make decisions about which actual function to dispatch
to based on ``Number1``:

.. code-block:: scheme

 (case (class-of Number1)
   ((Integer) (add-integer Number1 Number2))
   ((Real)    (add-real    Number1 Number2))
   ((Number)  (add-number  Number1 Number2)))

which means the implementation functions, ``add-integer``,
``add-real`` and ``add-number``, must look at the class of ``Number2``
to really determine what to do:

.. code-block:: scheme

 (define  (add-integer n1 n2)
   (if (not (eq (class-of n2) 'Integer))
       (add-real n1 n2)
       (make-Integer (+ (Integer-value n1) (Integer-value n2)))))

Using multiple arguments to determine the correct implementation
method is called *multiple dispatch* and for that we need
:ref:`generic functions <generic functions>`.

:ref-title:`LiSP` (:cite:`LiSP`) p.87 introduces a basic object system
will allow us to define a class:

.. parsed-literal::

 (define-class *classname* *superclass* (*field+*))

which, as a side-effect, creates a flurry of class-oriented functions
based on the identifiers used above.  A constructor:

.. parsed-literal::

 (make-*classname* *arguments*)

field accessors for an object of that type:

.. parsed-literal::

 (*classname*-*field1* *obj*)

field mutators:

.. parsed-literal:: 

 (set-*classname*-*field1*! *obj* *value*)

(note the trailing ``!``) and a predicate:

.. parsed-literal:: 

 (*classname*? *obj*)

.. _`generic functions`:

Generic Functions
-----------------

Again, from :ref-title:`LiSP` (:cite:`LiSP`) p.88

Generic functions is a mechanism for declaring the preferred behaviour
based on the class of (at least) one of the arguments (although,
single dispatch is the norm, multiple dispatch is possible albeit with
exponentially increased complexity which is why it isn't common).  The
point being you can choose which of your arguments should be the one
to distinguish behaviour rather than being forced to choose the first.

:ref-author:`Queinnec`'s generic function is introduced with:

.. parsed-literal:: 

 (define-generic (*name* *arguments*)
   *body*)

Where ``body`` will commonly be a call to an error function to catch
instances where the programmer has forgotten to define a
class-specific method.

One of the arguments must be distinguished (not necessarily the first
argument!).  That is done by making it a list (of itself):

.. code-block:: scheme

 (define-generic (foo arg1 (arg2) arg3)
   (error "bad args")

Here, we've made the second argument, ``arg2``, the distinguishing
one.

Remember, ``define-generic`` is a syntax transformer so its arguments
are passed to it direct.  There is no danger of ``(arg2)`` being
evaluated.  Not by the :lname:`Scheme` engine, anyway.

A generic method (ie. a class-specific method) is introduced with:

.. parsed-literal:: 

 (define-method (*name* *arguments*)
   *body*)

notably, syntactically identical to the ``define-generic`` above

Here the distinguished argument must again be identified as a list but
this time of itself and the name of the class this method is specific
to.  Our ``foo`` example might look like:

.. code-block:: scheme

 (define-method (foo arg1 (arg2 <X>) arg3)
   ...)

.. sidebox:: Here we really do mean class ``<X>`` as we allow angle
             brackets in symbol names.

where this ``foo`` method is specific to calls where ``arg2`` is an
object of class ``<X>``.

Our number example looks like:

.. code-block:: scheme

 (define-generic (add (n1) n2)
   (wrong "no method defined for" n1 n2))

 (define-method (add (n1 Integer) n2)
   (add-integer n1 n2))

 (define-method (add (n1 Real) n2)
   (add-real n1 n2))

CLOS
----

:ref-author:`Queinnec` doesn't need to head down the road of
multiple-dispatch (where more than one argument has a class
distinguisher) for his purposes.

The *Common Lisp Object System* (:term:`CLOS`) is multiple-dispatch
and has a very complicated *Meta Object Protocol* (:term:`MOP`) which
is far too overbearing for our needs.

Subsequently, :ref-author:`Gregor Kiczales` developed *Tiny-CLOS*
(:term:`Tiny-CLOS`) at Xerox Parc in 1992 which is a much simpler but
still multiple-dispatch with a simple MOP variation on CLOS.
*Tiny-CLOS* has been re-implemented in many :lname:`Scheme`\ s as well
as other languages.

Type Inference
==============

That said, whilst :lname:`Scheme` won't help you, there is opportunity for
compiler writers to introduce *type inference* where in principle, if
only the basic functions have any type information about them stored,
everything else can be derived:

.. code-block:: scheme

 (define (strlen s)
   (string-length s))
 (define i 3)
 (strlen i)

A type inferencing compiler, knowing only that ``string-length`` takes
a *string* as an argument would deduce therefore that ``s``, the first
argument of ``strlen``, should be a *string*, that ``i`` is a *number*
therefore the function call ``(strlen i)`` is a type error.

