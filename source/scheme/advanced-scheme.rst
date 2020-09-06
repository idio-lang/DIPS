.. include:: global.rst

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

To be fair, raw macros are "a bit tricky" so people have written
syntax transforming macros for you to use which let you create syntax
transforming macros.  The idea being to keep people away from the real
deal when they don't need to be there.

let
---

``let`` is a macro, it is a syntax transformer.  Here's how.

Just to make you hate the parenthesis a little bit more, our
evaluation model for :lname:`Scheme` says that functions are invoked
when they are the first element in a list and we've said that
``lambda`` is a function constructor.  Let's combine the two:

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

This is creating a function which takes two formal parameters, ``a``
and ``b``, to be in scope for the extent of the body forms.  It has a
single body form, ``(+ a b)`` the result of which is what the function
will return.

Like, ``(+ 1 2)``, had this function been bound to the symbol ``add``
we would have happily invoked ``(add 1 2)`` where ``add`` is going to
evaluate to a function value.  Wait, a function value is just the
thing we created with ``lambda``.  So put it all together:

.. code-block:: scheme

 ((lambda (a b) (+ a b)) 1 2)

(I told you you wouldn't like it.)

There's a lot of visual clutter there to figure out it is saying:

.. parsed-literal:: 

 (*func* 1 2)

and we haven't made the arguments complicated expressions at all!

But that's what it *is* saying and so the function value, created on
the hoof, is applied to the arguments and we get a result.
(Hopefully, 3!).

Where does this errant nonsense with on-the-fly function values get
us?

``let``, of course!  Consider a ``let`` statement:

.. code-block:: scheme

 (let ((a 1)
       (b (* 2 3)))
   (+ a b))

In the ``bindings`` we said each binding was a list containing a
symbol and an expression, so our symbols are the ``car``\ s of each
binding (``a`` and ``b``) and the expressions are the ``cdr``\ s
(``1`` and ``(* 2 3)``).

So a syntactic transformation of ``let`` could walk down the list of
bindings putting the ``car`` of each binding into a list of symbols
called, say, ``formals``, and the ``cdr`` of each binding into a list
of expressions called, say, ``args``.  The ``body+`` forms look like
they're going to be handled the same way in a ``let`` as in a function
so we can easily transform the ``let``:

.. parsed-literal::

 (let ((*formal1* *arg1*)
       (*formal2* *arg2*))
  *body+*)

firstly, partly into a function definition:

.. parsed-literal::

 (lambda (*formal1* *formal2*) (begin *body+*))

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

:question:`Eh?  What's that doing?` What we've done is declared a
(usually self-recursive, hence ``letrec``) function called ``foo``
which takes formal parameters, ``f1`` and ``f2``, and we automatically
called it with arguments, ``e1`` and ``e2``.

So we've declared and invoked a function in one statement.  It seems a
bit... *exciting* ...but it's actually really useful.  You recall that
:lname:`Scheme` prefers a recursive loop and there's any number of
occasions when we want to loop over something, counting, filtering,
whatever and this ``let`` form allows us to declare a loop function
(that can self-recurse) and kick it off with some starting values.

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

  --- everyone

A macro, which is ostensibly a regular function, is created using a
function that tags your function's name as a macro.  This tagging
function clearly has to have hooks into the backend because, having
looked out for all the special forms, the :lname:`Scheme` engine will
check to see if the function name for a form is tagged as a macro and
if so it does not evaluate the arguments but passes them onto the
function/macro as is (atoms, lists).  The macro can then poke about
with its arguments as it sees fit and return some value.

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
are identical-across-classes tracts of code and you already have
``name``, ``parent`` and all the field names in your hands?  The
``define-class`` call has been given everything it needs to know, the
rest of it should get built automatically.

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

which is fine but will itself start to get rather long winded.

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
:question:`Eh?  Isn't that the point?` Not quite.  What we want to do
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
definitions floating about).

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

Note that macros are expanded "at compile time" which should really
say that macros are expanded (recursively and in a separate
evaluation-space) before the resultant program is evaluated.  In fact,
it's even more complicated than that as if a macro defines and uses
macros itself then those macro-macros live in a meta-evaluation space
and another level again if those macro-macros define and use
macros....

Macro Issues
^^^^^^^^^^^^

The primary problems with macros are:

- you forget its arguments are not evaluated -- so you can't pass a
  variable you've calculated

- you forget it is run at compile -- your variable wouldn't exist
  anyway

- you're a dirty hacker

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

which is still good until someone types:

.. code-block:: scheme

 (let ((tmp "foo"))
   (my-or #f tmp))

The macro is expanded:

.. code-block:: scheme

 (let ((tmp "foo"))
   (let ((tmp #f))
     (if tmp tmp tmp)))

Yikes!  ``(if tmp tmp tmp)``?  We might just have lost track of which
``tmp`` we are referring to.

This problem is solved by using *hygienic* macros -- actually macros
are still macros but rather the macro writer uses a little code trick
to invent a unique variable name in the prep work:

.. code-block:: scheme

 (definemacro (my-or e1 e2)
   (let ((tmp (gensym)))
     `(let ((,tmp ,e1))
        (if ,tmp
            ,tmp
            ,e2)))

Here, we used ``gensym`` (generate symbol!) to come up with a unique
symbol that cannot conflict with anything else.  ``tmp``, a regular
locally introduced symbol during the evaluation of ``my-or`` (albeit
in "compile-time macro-space"), is now bound to that symbol value and,
having been defined in the outer ``let``, can be evaluated inside the
``quasiquote`` expression.

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
(which they always were...) within strict limitations.  Elements of
the macro calls are tagged and the tags are managed so that no
unhygienic variables are introduced.  (Unless you really really want
to!)

Closures
========

Let's try a more dynamic variant:

.. code-block:: scheme

 (define a 1)

 (let ((ab+ (let ((b 3))
	     (lambda (n)
	      (+ a b n)))))
  (ab+ 5))

:question:`Cripes!  What's happening here?` The inner ``let``'s body
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

You can extend this idea to enclosing a series of functions over a
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
and both have access to ``private`` to which no-one else has access
other than through the interfaces, ``this`` and ``that``.

This is about as complicated as it gets!  (Well, when I say that...)

On the one hand this is immensely complex, functions returning
functions that expect to be passed functions that will be applied to
(effectively) the original arguments!  Who can keep up?

One the other hand: 

* anonymous functions mean there's no naming clashes for these
  "helper" functions -- we can keep firing them out left right and
  centre, they are all independent, created on the fly and closing
  over the arguments that were passed to them

* functions are first class values, i.e. can be passed around just
  like numbers or strings

* the ability to close over variables means we don't need functions to
  communicate values between one another via global objects

* it is very concise!

There's an conceptual step up here from many regular languages and
hand in hand with that are some clear proficiency improvements.  It's
a heady mix!

Object Orientation
==================

.. _Smalltalk: https://en.wikipedia.org/wiki/Smalltalk

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

:ref-title:`ELPAiP` (:cite:`EPLA`) p.135, implements this (in *Perl*)
in a straight-forward manner.  If the evaluated value in functional
position is an object then the first argument is assumed to be an
object-specific function, a method, and there's a mechanism for
looking up a method within the hierarchy of the class.  The method is
then applied to the arguments with the object itself bound to the
variable ``this`` (cf. ``self``) for the duration of the method.

On the whole, though, that's not very :lname:`Scheme`-ly which prefers
functions in functional position.  There's a second argument in favour
of not using the message passing idiom in that if there are multiple
objects within the arguments then only the *first* argument can be
used to distinguish the call.  For example, if we wanted to add two
numbers together where we might have a class hierarchy of ``Integer``
is a ``Real`` is a ``Number``, then:

.. code-block:: scheme

 (add Number1 Number2)

we only get to make decisions about which actual function to dispatch
to based on ``Number1``:

.. code-block:: scheme

 (case (class-of Number1)
   ((Integer) (add-integer Number1 Number2))
   ((Real) (add-real Number1 Number2))
   ((Number) (add-number Number1 Number2)))

which means both ``add-integer`` and ``add-real`` must look at the
class of ``Number2`` to really determine what to do:

.. code-block:: scheme

 (define  (add-integer n1 n2)
   (if (not (eq (class-of n2) 'Integer))
       (add-real n1 n2)
       (make-Integer (+ (Integer-value n1) (Integer-value n2)))))

For *multiple dispatch* we need *generic functions*.

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

Generic Functions
-----------------

Again, from :ref-title:`LiSP` (:cite:`LiSP`) p.88

Generic functions is a mechanism for declaring the preferred behaviour
based on the class of one of the arguments (although, single dispatch
is the norm, multiple dispatch is possible albeit with exponentially
increased complexity which is why it isn't common).  The point being
you can choose which of your arguments should be the one to
distinguish behaviour rather than being forced to choose the first.

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

