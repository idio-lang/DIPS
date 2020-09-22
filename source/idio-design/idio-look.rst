.. include:: ../global.rst

******************
:lname:`Idio` Look
******************

:lname:`Scheme` looks like it can be used to program computers,
indeed, it looks like it can do far more in terms of programming
computers that we are used to or, more likely, capable of!  It is very
succinct with several key implementation details:

* closures, we can close over variables and use them in a function
  body

* anonymous functions, we can create functions on the fly

* functions are first class, we can construct and return them for
  others to call

* compound data types

* error handling

* macros, at least syntax transforming macros

* continuations, as a means of deriving exceptional behaviour they are
  required though whether we would want the full power of
  continuations available is debatable.  If we don't then users cannot
  create their own escape procedures -- remembering that we're meant
  to be writing a shell!

Variables might be introduced differently but are otherwise the same.
Data structures are broadly the same with a pair simply being the guts
of a linked list.

Calling functions is essentially no different, function followed by
arguments.

But, and I suppose it is the never ending bugbear of :lname:`Lisp`\ s,
it *looks a bit funny*.  However, thanks to syntax transformations, it
can *look like* whatever we want it to, so long as we can transform it
back into something the underlying :lname:`Scheme`-ish engine can
handle.

We should recognise that we're describing two things: firstly we need
the core functionality to make some behaviour happen, think about the
ability to create and manipulate file descriptors, and secondly, some
syntactic sugar to abstract away the repetitive detail.

So, how should the language *look*?

Line-Oriented
=============

I'm quite content with my ALGOL-inspired syntax and with my shell hat
on, I want, nay, *insist* that I be able to type:

.. code-block:: idio

 ls -l

With no (obvious) punctuation, just like the shell.  Isn't that the
point?

Mind you, with our :lname:`Scheme` hats on, ``ls`` is *undefined* in
the program.  We know, with our shell hats on, that the shell will
take it upon itself to have a rummage around the shell's ``PATH`` to
find an ``ls`` executable.  In :lname:`Scheme`, though, we need to
break the behaviour that ``ls`` is undefined.

Similarly, for ``-l``.  Is that a funky function to subtract the value
of ``l`` from its argument or just a string of characters to be passed
as an argument to some command?  Tricky.

I like the idea that I can, at long last, have hyphens in my variable
names saving us from the thrall of underscores or CamelCase or
whatever -- albeit with the cost that whitespace is *required* to
distinguish between terms.  I can live with that, whitespace is
*cool*.

I like that other punctuation characters are available to add meaning
to my names, ``?`` and ``!``, and I have a cunning plan for accessing
structure fields with ``.`` in the Jinja_ way (my original inspiration
was :lname:`Perl`'s `Template::Toolkit
<http://www.template-toolkit.org/>`_).

However, there is a far worse bind we put ourselves under if we allow
punctuation characters in names as it conflicts with the
meta-characters the shell uses to spot pathname patterns:

.. code-block:: idio

 ls -l *foo*.txt

Is that:

* the variable ``*foo*.txt``?

* the variable ``*foo*``, a structure, where we want to access the
  field ``txt``?

* the variable ``*foo*``, an array where we want to access the
  ``txt``\ :sup:`th` element (``txt`` itself being a variable)?

* a pattern match expression to be passed to :manpage:`glob(3)`?

Hmm.

What if none of the above are true?  If ``*foo*`` (or ``*foo*.txt``)
is yet to be defined at the top level, say, then we have a *runtime*
decision to make which is not a good place to be if we are thinking
about any form of compilation.

I confess I'm at a bit of a loss here and I'm leaning in favour of a
consistent programming language over shell-ish conveniences.

For pathname matching I'm turning towards the idea that since we
intend that the result of a :manpage:`glob(3)` pattern match be a list
that we *preserve as a list* until it is required then perhaps we
should distinguish the pattern match that creates it.  Does something
like:

.. code-block:: idio

 ls -l #P{ *foo*.txt }

cause palpitations?  In one sense it is a bit like preparing a regular
expression in :lname:`Python` or :lname:`Perl`.

It's not *Art*, I agree.

There's a very similar problem with plain filenames:

.. code-block:: idio

 ls -l foo

``foo``, here, will be looked to be evaluated -- and could be --
otherwise will cause an *unbound* error like ``ls`` might.

As a transient feature most things that expect a filename will work
with a string (no globbing!):

.. code-block:: idio

 ls -l > "foo"
 open-input-file "foo"

Single Word Feature
-------------------

By and large command lines are a command and some arguments, ``ls -l``
etc..  That's fine because it translates easily into a function
application, ``(ls -l)``, just like ``(+ 1 2)``.

However, there is an outstanding feature which is a side-effect of the
REPL.  If your command consists of a single word, eg. ``ls`` then it
is indistinguishable in a standard :lname:`Scheme`-ly REPL where any
single word will be evaluated and its value printed:

.. code-block:: idio

 Idio> n := 10
 Idio> n
 10
 Idio> map
 #<CLOS map @51321/0x30c4580/Idio>


giving us the value of ``n`` and some internal representation of the
closure, ``map``.
 
(Internal representations having no useful meaning possibly even to
developers.  Indeed, I had to look at the source to remind myself what
those values represent as I only really look at the ``CLOS`` part
telling me it is a closure.)

Which is what you want.  Well, it's what many people would expect from
an interactive :lname:`Lisp`\ y session.

Consequently, typing ``ls`` will get, um, ``ls`` printed back as it is
determined to be an undefined symbol where we choose, in an
un-:lname:`Scheme`-ly fashion, to simply print the symbol (rather than
a more :lname:`Scheme`-ly raise an *unbound* error).

If you want to force the single word command ``ls`` to be invoked then
you *must* put it in parentheses:

.. code-block:: idio

 Idio> (ls)
 My Documents
 ...

That's true of functions as well:

.. code-block:: idio

 osh := (open-output-string)

It's quite annoying for me where I habitually type ``make`` at the
:lname:`Idio` prompt to have ``make`` printed back at me.  Not
helpful.  I've taken to typing ``make -k`` a lot more....

.. sidebox:: TBD

I don't *like* it.  I'm not sure what a better behaviour might be.

Complex Commands
----------------

There's another awkwardness from the idea of a line-oriented shell for
complex functions, ones that have multiple clauses.  Take, ``cond``,
for example, which is nominally:

.. code-block:: scheme

 (cond (c1 e1)
       (c2 e2)
       (else e3))

``cond`` by rights, should be invokable in the same way as ``ls``,
ie. without leading parenthesis but that would lead us with:

.. code-block:: scheme

 cond (c1 e1)
      (c2 e2)
      (else e3)

which our line-oriented engine is going to see as three distinct
statements -- albeit with the second two having exaggerated indents.

:lname:`Python` supports the idea of indented code -- indeed you can
see references to *indent* and *deindent* in the parser -- but it
doesn't feel like the indentation here is a syntactic thing, it's
really a visual *aide-mémoir*, after all, we could have written:

.. code-block:: scheme

 cond (c1 e1) (c2 e2) (else e3)

and be done.  Except the condition and expression clauses are almost
certainly complex and the resultant enormous line would be difficult
to read let alone maintain.

The original ``(cond ...)`` across multiple lines works because the
:lname:`Scheme`-ish engine is looking for the matching close-parens
(for the leading open-parens on the first line) and so will consume
all lines until it gets it.

For our "unwrapped" ``cond``, we can use a regular shell-ish line
continuation character:

.. code-block:: idio

 cond (c1 e1) \
      (c2 e2) \
      (else e3)

But, be honest, it looks a bit clumsy.  And I can say that with some
confidence as I have, out of a duty to see it through, written *all*
the complex multi-clause forms use this style.  (What an *idiot*!  I
sense growing sagacity of the language name...).

This gives us the dreadful:

.. code-block:: idio

 if (some test) \
    (truth-fully) \
    (not so truthy)

I know, I know!  (And it gets worse.)

Of course, you *can* continue to use the wrapping parenthesis -- all
that the non-wrapped line is doing is having the wrapping parenthesis
silently added -- but the result is like the `Curate's egg`_:

.. code-block:: idio

 ls -l
 (if (some test)
    (truth-fully)
    (not so truthy))

and, to be honest, I find it less appealing than the clumsy variant.
The line-continuation style has the decency to be consistent.

Infix Operators
===============

There is the issue of infix operators, ``|`` and arithmetic operators
amongst a plethora of others.

I think there's a trick we can pull here following in the footsteps of
the reader macros for ``quote`` and friends.

Suppose we have a means to declare a symbol as an infix operator
together with some behavioural code.  Then, after the reader has read
the whole line/parenthetical expression in, it goes back and looks to
see if any of the words are an infix operator.  This is much like
macros where the evaluator goes and looks for macros and behaves
differently except we are running this before reaching the evaluator.

So, if I had typed:

.. code-block:: idio

 zcat file | tar tf -

then the reader will have read in six words in a(n implied) list.  It
can scan along, find that ``|`` is an infix operator and call its
behavioural code.  I'll assume we're all happy that it wants to rework
this into:

.. code-block:: scheme

 (| (zcat file)
    (tar tf -))

.. sidebox:: Always a good position.

which is a simple list transformation requiring no knowledge of
anything.

After this transformation, ``|`` is in functional position
and so the evaluator will expect it to be the name of a function.

Had someone typed the second form in directly then the reader would
have left it alone as the thing that *looks* like an infix operator
can't be, because it's the first element in the list.  An infix
operator (surely?) has to have something before it to be *in*\ fix.

Recall I suggested that this happens in the reader for parenthetical
expressions so that if you'd typed:

.. code-block:: idio

 zcat file | (tar tf - | grep foo)

(I'm leaving ``foo`` in there as it fails my point about symbols and
expansion but is easier to read whilst we mull over the idea.)

Although we start reading ``zcat file ...``, the first *complete*
parenthetical expression read would be ``(tar tf - | grep foo)`` which
can be re-written as:

.. code-block:: scheme

 (| (tar tf -)
    (grep foo))

to become part of the outer line-oriented expression when it is
eventually completely read in (by hitting the end of line):

.. code-block:: idio

 zcat file | (| (tar tf -)
		(grep foo))

This time, even though there's a ``|`` in the middle of the second
expression it isn't directly in the outer expression which looks, to
the reader, like:

.. parsed-literal::

 *rhubarb* *rhubarb* | *rhubarb* *rhubarb*

.. aside:: I should be careful of referencing 1970s British TV comedy
           for fear of attracting :ref-title:`The Phantom Raspberry
           Blower of Old London Town`!

and can be transformed into:

.. code-block:: scheme

 (| (zcat file)
    (| (tar tf -)
       (grep foo)))

Contrast that with multiple instances of the operator in the same
expression:

.. code-block:: idio

 zcat ... | tar ... | grep ...

which we might transform into:

.. code-block:: scheme

 (| (zcat ...) 
    (tar ...) 
    (grep ...))

It's more subtle than that, though, as a pipeline (and the logical
operators ``and`` and ``or``) take multiple words as their arguments,
*including other operators*, yet arithmetic operators (and IO
redirection) take only a single argument either side.

:lname:`Scheme` might allow:

.. code-block:: scheme

 (+ 1 2 3)

but

.. code-block:: idio

 1 + 2 3

is incorrect in regular arithmetic.  That means that the code for
operators needs to do some syntax checking.  It's not great that
syntax checking is happening in the reader but, hey ho.  Let's run
with it.

To complicate matters, ``+`` and ``-`` are commonly unary operators as
well as binary ones: ``- n`` should return negative ``n`` (remembering
that ``-n`` is a symbol!).

Operator Associativity
----------------------

The arithmetic operators have *associativity*, that is ``1 - 2 - 3`` is
equivalent to ``(1 - 2) - 3`` as ``-`` is left-associative.  ``+`` is,
mathematically, non-associative although usually defined in
programming languages as left-associative.  Assignment is
right-associative -- evaluate the value first!

Pipelines are left associative, hence the triple pipeline example is
quite likely to be *executed* as:

.. code-block:: scheme

 (| (| (zcat ...) 
       (tar ...) 
    (grep ...)))

Even if its nominal form is all three children parented by the same
``|`` operator.

Operator Precedence
-------------------

There's also *precedence*: ``(1 + 2 * 3)`` could be ``((1 + 2) * 3)``
or ``(1 + (2 * 3))`` depending on which operator was run first.

Logical operators, pipelines, arithmetic, logical operators and IO
redirection are all ordered by precedence:

.. code-block:: idio

 tar *.txt 2>/dev/null | gzip > foo || echo whoops

should be interpreted as first ``pipeline || pipeline``, then ``cmd+io
| cmd+io`` then, finally, arrange ``io`` followed by executing
``cmd``.  Hence we might derive:

.. code-block:: scheme

 (or (| (io-> 2 /dev/null
 	      tar *.txt)
        (io-> 1 foo
 	      gzip))
     echo whoops)

using some putative ``(io-> fd file cmd . args)`` function to handle
IO redirection (which doesn't handle multiple redirections so doesn't
exist).

Notice no :manpage:`execve(3)` function has been introduced as, at
this stage, we don't know if ``tar`` and ``gzip`` are internal
functions or external commands.  All we're doing is rewriting the
statements involving infix operators.

The Reader and Infix Operators
------------------------------

Such transforms will also mean that:

.. code-block:: idio

 echo 1 + 2 3 * 4

will be re-written as:

.. code-block:: scheme

 (echo (+ 1 2) (* 3 4))
 
resulting in:

.. code-block:: sh

 3 12

but the original form was hard for the human mind to scan -- the
pedantic grouping of sub-expressions of :lname:`Scheme` would have
forced us to write:

.. code-block:: idio

 echo (1 + 2) (3 * 4)

which is, at least, clearer in intent!

It's not uncommon to have multiple clauses in a logical statement,
drawn out over multiple lines for clarity:

.. code-block:: idio

 if (this and
     that and
     the-other) \
    ...

So I feel that if the last word on a line is an infix operator then
the expression is assumed to continue on the next line.

That said, I've gotten quite used to writing the more
:lname:`Scheme`-ly:

.. code-block:: idio

 if (and this
	 that
	 the-other) \
    ...

but the trailing operator trick stills stands.

Operator Overloading
--------------------

"Operator overloading" is a fan favourite in other languages -- which
is another way of saying, heavily controversial.

Think ``+`` is just about adding integers together?  It's common
enough to appear as string concatenation and so I guess people would
be happy enough to see it used for any kind of append operation
(lists, arrays, hashes(?)).

Our infix operators are blind to your types, though.  They simply
massage lists into another form.  You'll be wanting function
overloading which means :ref:`generic functions`.

Operator Summary
----------------

I think this reader macro trick has some mileage.


Lexical Blocks
==============

If you're a :lname:`Scheme`\ r, you're quite used to:

.. code-block:: scheme

 (let ((a 1))
   (+ a 1))

whereas others would be more at home with a more :lname:`ALGOL`-ish:

.. code-block:: idio

 {
   a = 1
   a + 1
 }

where ``{`` starts a lexical block in which we can introduce lexically
scoped variables.  They would likely all be introduced as a ``let*``
or ``letrec`` type as that's the sort of behaviour non-\
:lname:`Scheme`\ rs would expect where we can have one variable
derived from another:

.. code-block:: idio

 {
   a = 1
   b = a + 1
   
   odd? = function ... even? ...
   even? = function ... odd? ...
 }

Additionally, the lexical block has an implied ``begin`` meaning the
last calculated value is the one to be returned by the block.

The reader is intent on matching bracket-type things so will read
multiple lines -- the lexical block's body -- to get the closing
``}``.


They sound quite handy for :ref:`functions`.

Assignment
==========

I like the idea of ``define`` to force the user to declare names --
and we'll see the (pedantic :lname:`Scheme`\ ly) reasons why later --
however I think we :lname:`ALGOL`-types generally prefer the ``=``
style.

I was thinking of some way to avoid the ``=``/``==`` mistakes
prevalent in :lname:`C`:

.. code-block:: c

 if (a = 1) ...

is probably not what you want, and started off thinking that a
:lname:`Pascal`-style ``:=`` would come in handy.  We can also make it
an infix operator:

[confident narrator voice] *...we have the technology...*

.. code-block:: idio

 a := 1
 ...

which would be transformed by the reader into ``(:= a 1)`` and then
the evaluator can introduce the variable ``a`` giving it the value 1.
Technically, in the underlying :lname:`Scheme`-ish engine that's going
to be a ``define`` or a ``let``.  In a lexical block, for example:

.. code-block:: idio

 {
  a := 1
  ...
  a
 }

would get transformed into:

.. code-block:: scheme

 (let ((a 1))
  (begin
   ...
   a)

in other words, after any ``:=`` statement, the entire rest of the
lexical block becomes the body of the implied ``let`` such that the
``let*``-ish:

.. code-block:: idio

 a := 1
 b := a + 2
 ...
 b

would get transformed into:

.. code-block:: scheme

 (let ((a 1))
  (let ((b (a + 2)))
   (begin
    ...
    b))

which, I think, works OK.

I have, however, failed in my visual-distinction task in that to
"modify" ``a`` we use regular ``=``:

.. code-block:: idio

 a := 1
 ...
 a = a + 1

Noting that the *reader* will transform ``a + 1`` into ``(+ a 1)``
*first* as ``+`` has a higher infix operator precedence than the
``=``:

.. code-block:: scheme

 (= a (+ a 1))

Function calls
--------------

Function calls in assignments come out in the wash, here, as:

.. code-block:: idio

 a = func sol bruh va

is transformed into:

.. code-block:: scheme

 (= a (func sol bruh va))

and ``(func sol bruh va)`` is a regular evaluable form returning its
result to the assignment operator, ``=``.

We *are* still stuck with the single word feature as described above
so you need to type:

.. code-block:: idio

 a = (func)

if you're not passing any arguments.  *\*shrugs\**

Top Level Assignments
---------------------

Defining variables at the top level, ie. outside of a lexical block,
comes in a couple of forms.

``define`` has two forms itself:

.. parsed-literal::

 define *variable* *value*

 define (*func-name* *formals+*) *body*

or you can use one of the assignment infix operators:

.. parsed-literal::

 *variable* := *value*

 *function-name* := function (*formals+*) *body*

The ``define`` form for functions is much cleaner but the assignment
variant is used liberally when re-defining an existing function.

Non-lexical Variables
---------------------

We want to get to handling environment variables seamlessly which I've
been suggesting are a kind of tagged dynamic variable.

Dynamic Variables
^^^^^^^^^^^^^^^^^

Dynamic variables "live on the stack", that is to say that their
existence is dependent on the code path you have run and as your
function call hierarchy unwinds the dynamic variables disappear.
Access to the variable is more work because you need to run back up
(down?) through the stack looking for your transient variable.

(This idea is reused -- probably a bit too much!)

Nominally, there's the ``dynamic-let`` call which introduces a dynamic
variable (onto the stack) and starts processing:

.. code-block:: scheme

 (dynamic-let ((X 10))
  (foo))

Normally, some function calls deeper, you would call ``(dynamic X)``
to get the value of ``X``, your dynamic variable.

Obviously, you don't want to be asking for a dynamic variable in some
random bit of code on the off-chance.  You're meant to know what
you're doing!

.. sidebox:: This evaluator trickery doesn't work quite as cleanly as
             we'd like.  Dynamic variables effectively become top
             level variables.

Digressing a little, there is a mechanism in the evaluator to keep
track of variable names which can keep track of the lexical or dynamic
nature of a variable -- by remembering what kind of form introduced
it.  Subsequently, if we were to reference ``X`` we would know it was
a dynamic variable and can therefore replace the variable reference,
``X`` with ``(dynamic X)`` -- essentially to provoke the stack-walking
mechanism -- and all is good.

Back to our variable initialisation.

.. sidebox:: *Genius!*

We have ``:=`` for lexical assignments, how about ``:~`` for dynamic
variables?  ``~`` representing the maybe, maybe not dynamic nature of
the beastie.

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Environment variables are much more shell-ish.  I'm suggesting we want
to implement them in a similar fashion, as an "environment" variable
with a dynamic nature.  They are different to dynamic variables in
that whenever a program is executed it will have an environment
created which is built from any extant "environment" variables.

.. sidebox:: Look, it's just a little bit of technical debt that, when
             we get round to it, we can apply the extra experience
             we'll have picked up in the meanwhile to do a better
             refactoring job.

	     What's not to like?

It could be implemented by tagging some dynamic variables as
"environment" variables or it could be implemented as an entirely
parallel and separate set of dynamic variables.  *\*cough\**

The reason for this dynamic nature is I want to be able to say:

.. code-block:: idio

 {
  PATH := path-prepend PATH /some/where/else

  do stuff
 }

Here, for the duration of this lexical block, ie. whatever effect we
create should be unwound at the end of the block, I am creating a
*new* PATH variable which should be used by anyone looking up the
``PATH`` environment variable if, say, they want to find an
executable.

After this lexical block people can find the old value.

.. sidebox::  *Stop it, please!*

I'm thinking ``:*`` here, with ``*`` signifying the stars, the
*environment* surrounding us!

So that should have been:

.. code-block:: idio

 {
  PATH :* path-prepend PATH /some/where else

  do stuff
 }

You might ask why didn't I just modify the value of ``PATH``?  Well,
modifying it means that everyone after this lexical block will see my
transient changes unless I ensure that I can unwind the changes
manually before I'm done.

:socrates:`Even on error and in the face of continuations?`  Hmmm, "tricky."

Of course, modifying ``PATH``, say, for everyone following is
perfectly normal we're just covering the variable assignment prefix
case of:

.. code-block:: sh

 PATH=/some/where/else:$PATH do stuff

Un-setting Transient Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is another corner case where you might want to unset such
dynamic variables, possibly transiently, and almost always for
environment variables.

For that we need to add a stack marker that says: stop looking any
further and return "failed to find".

We need to kind of indication we're stomping on the normal way of
things so I'm penning in ``!~`` and ``!*`` for dynamic and environment
variables respectively.

Computed Variables
^^^^^^^^^^^^^^^^^^

There's another class of shell variables we want to emulate.  Remember
``SECONDS`` which returns us the number of seconds the shell has been
running for?  (There's ``$^T`` in :lname:`Perl` as well.)

There's clearly a bit of magic there where the simple act of accessing
a variable has resulted in a (hidden) function call.

I'm calling these *computed variables* (not least because many others
have done so before).

It would be neat if we could allow the user to create these.
``SECONDS``, mind, is probably one for the language implementer as it
requires something in the language bootstrap to start the clock
rolling!

There's another twist for computed variables.  They might be
read-only, like ``SECONDS`` for which it makes no sense to assign a
value to them.  They might be write-only like :manpage:`srandom(3)`,
the seeding mechanism for :manpage:`random(3)` where it defeats the
purpose to get back that secret seed value.  It might be read-write
like the shell's ``RANDOM`` (which combines the behaviour of both
``srandom`` and ``random``).

If the user is defining a computed variable then they must pass two
parameters to the initialisation: a getter and a setter.  If you want
it to be read-only pass ``#n`` (aka. ``nil``) for the setter.  Pass
``#n`` for the getter for a write-only variable.  Passing ``#n`` for
both should result in an error -- *don't be annoying!*

.. sidebox:: *Oh, puh-lease!*

As for the infix operation/function name, try ``:$`` for size!

We can then rustle up something like:

.. code-block:: idio

 getter := #f
 setter := #f

 {
  p := 0

  getter = function () {
	     p = p + 1
	     p
  }

  setter = function (v) {
	     p = v
  }
 } 

 cv :$ getter setter

 printf "%d %d\n" cv cv
 cv = 10
 printf "%d %d\n" cv cv

which should display:

.. code-block:: sh

 1 2
 11 12


.. _functions:

Functions
=========

Of course, functions could change very little from how they exist
now:

.. code-block:: sh

 function foo ()
 {
  echo $(( $1 + 1));
 }

other than a little textual transformation into, say:

.. code-block:: idio

 function (a) {
   b = a + 1
   b
 }

the differences being that there's no function name in the function
declaration and we have formal parameters.

Notice too the start of a lexical block, ``{``, *on the end of the
first line* of the function declaration.  That means our line-oriented
reader will continue reading through to the matching ``}`` thus
creating the function body.

If it wasn't on the end of that line:

.. code-block:: idio

 function (a)
 {
   b = a + 1
   b
 }

would be a semantic error as ``function (a)`` was read and deemed by
the line-oriented code reader to be a whole expression.  But it is a
function declaration with no body and so is an error.  The remaining
lexical block is, well, just a lexical block.  That's legal although
you might get complaints about this new variable ``a`` that has
appeared.

.. sidebox:: Haters gonna hate!

I like the ``{`` on the end of the line as it is, by and large, the
way I write code anyway.  Others will, no doubt, be very angry.

Functional Block
----------------

:lname:`Ruby` and :lname:`Swift` both allow a block to take formal
arguments thus allowing an alternate form of creating anonymous
closures:

.. code-block:: ruby

 { |n| n + 1 }		; Ruby

.. code-block:: swift

 { (n) in n + 1 }	; Swift - could have said { $0 + 1 }

The more you're used to seeing it the easier it is to scan.

I'm not so tied to the idea, though.

Pipelines
=========

We're fairly happy, I think, that we should have regular shell-ish
pipelines:

.. code-block:: idio

 zcat file | tar tf -

I've not implemented it yet -- partly because ``&`` is used for pairs
-- but you can image a form of postfix operator, ``&`` to background a
pipeline, like the shell:

.. code-block:: idio

 zcat file | tar tf - &

Previously I said I was going to reserve the :lname:`C`/shell logical
operators ``&&`` and ``||`` for nefarious purposes.

Again, not implemented, but I'm thinking that ``||`` is more of an
object pipeline -- so, like PowerShell_ and friends -- we might be
able to create some functional composition/comprehension/cascade
(there must be a proper term) where the value returned by one function
call is the argument to the next:

.. code-block:: idio

 func args || f2 || f3

although you immediately think that the later functions should be
allowed to have other arguments themselves (albeit ``f2`` and ``f3``
could be the result of currying themselves and only take a single
argument) in which case you'd need some symbolic argument for the
value being passed down.

:lname:`Perl` used to use ``$_`` for the anonymous value so our
equivalent would be something like:

.. code-block:: idio

 func args || f2 a1 _ a2 || f3 _ b1 b2

However it might be done, you can recognise that it is a
straight-forward enough transformation into a nested call:

.. code-block:: idio

 (f3 (f2 a1 (func args) a2) b1 b2)

On a different tack, ``&&``, might be used to "kick off in the
background" a thread (should we have any):

.. code-block:: idio

 keep-an-eye-on stuff &&

This double-punctuation character thing might have some mileage.

How about ``>>`` to collect "output" in a string?  Of course, ``>>``
is the append variant of ``>`` for (pipeline) IO redirection.  That's
a bit unfortunate.

I appear to have lost my reference but I thought I'd seen some
alternate IO redirection forms, eg. ``>+`` might be used for append
and ``>=`` with an offset might be used to :manpage:`fseek(3)`
somewhere in a file before writing.

Traps
=====

We need to be able to handle errors and exceptions and we'll use the
broad idea of :lname:`Scheme`'s conditions.  We want to trap a
condition.

A condition (a state of being of the program, if you like) is the
parent of errors and exceptions (and other derived conditions, of
course).  For no particularly strong reason I wanted to distinguish
between errors and exceptions.  To some degree it doesn't really
matter as they are all conditions and all get managed in the same way.
The distinction is largely taxonomic and poorly implemented as I look
back now and find that I've called *everything*
something-something-:code:`error`.

An *error* is something that cannot be fixed without rewriting the
source code:

.. code-block:: idio

 pair 1

is an error because no matter how many times you run or whatever
external changes you make, ``pair`` takes two arguments and you've
only given it one.  It is unrecoverable in any sense other than to
edit the source code.

Accordingly, for an error, it is not possible to continue with this
thread of processing and the engine will revert to some safe place.
The user cannot trap it.

An *exception* is any kind of transient condition, usually outside of
the program's control

- if a system call goes wrong we'll get an exception raised (by the
  :lname:`C` code wrappering the call) indicating ``errno``

  - if you fail to open a file -- permissions, disk issues (inodes and
    data blocks in Unix), etc.

- if you try to get the ``string-length`` of a number the function
  will raise an exception.

Some of those are genuinely transient in that you can, say, fix the
file system outside of the (running?) program to allow your file
operation to go ahead.  Some of them are effectively permanent if you
are passing the wrong kinds of parameters to system calls or functions
but are still classed as exceptions as a subsequent run through the
code could have changed the values the parameters are bound to and the
system/function call might now succeed.

:lname:`Bash` ``trap``\ s signals, mostly, but also has a
pseudo-signal, ``ERR``, representing the failure of a simple command.
We can do the same but be a bit more profuse with the kinds of errors
(er, exceptions!).

Actually, it's also pretty reasonable to throw in some signal handling
through the exact same mechanism just using a different part of the
condition hierarchy tree.

Condition Types
---------------

Conditions types are a hierarchy of structures with ``^condition`` at
the root.  I chose to have a leading caret, ``^``, at the start of
condition type names to suggest the handling of conditions "above" the
normal operation of the code.  I'm not massively taken by it on
reflection and might engage in a code-wide edit.

An ``^error`` is a child of ``^condition`` -- merely to start a clean
tree.

``^idio-error``, a child of ``^error``, is the start of our tree of
interest and introduces three fields:

- ``message`` -- the nominal problem

- ``location`` -- some indication, preferably relating to the user's
  source code, of where the error occurred

- ``detail`` -- any other pertinent information, for example, the
  value of a likely problematic variable.

We can now start deriving trees of condition types from
``^idio-error``, for example:

- ``^read-error`` with additional fields of ``line`` and ``position``
  (byte index into the source *handle* -- file or string!) being the
  common root of all reader errors.

- ``^io-error`` and its derivatives primarily relating to files

- ``^runtime-error`` which has a wide tree of children including:

  - ``^rt-parameter-type-error`` for passing the wrong type of value
    into a function, for example we can't get the ``ph`` (pair-head)
    of a number.

  - ``^rt-command-status-error`` for when external commands fail

- ``^rt-signal`` for, er, signals albeit this is derived from
  ``^error`` directly as its asynchronous, out-of-band provenance
  means there's no particular association with any message, location
  or detail that ``^idio-error`` requires for its fields

SIGCHLD
^^^^^^^

Just as food for thought, there's some fun with *SIGCHLD*.  When an
external process completes (or is stopped but that confuses this train
of thought) we, :lname:`Idio`, will get a *SIGCHLD* which means we'll
have updated our ``volatile sig_atomic_t`` and, at an appropriate
time, run an :lname:`Idio` *interrupt handler* -- a condition handler
being run out of turn -- which will, almost certainly be the code
written for *Job Control* (because we're a shell, remember).

If the external process exited non-zero then *that* code will raise an
``^rt-command-status-error`` condition which the user can write a
handler for.

Separately, the code that ran the external process will eventually
unwind to return ``#f``, if the process failed, which can be used by
any of the conditional forms in the shell-ish way:

.. code-block:: console

 Idio> if (false) "worked" "failed"
 job 95645: (false): completed: (exit 1)
 "failed"

.. sidebox:: For many many years I have had a :lname:`Bash`
             ``PROMPT_COMMAND`` which has figured out the exit/killed
             status and printed something useful.

	     I feel that if *I*'m writing a shell, everyone should get
	     that useful behaviour.

The ``job 95645: ...`` line is printed by the *Job Control* code
separately to ``if`` being returned ``#f`` by the expression
``(false)`` -- which was reworked into an invocation of the external
command ``false`` which, er, exited non-zero.

``if`` can then run its *alternate* clause which is the string
"failed" which is what ``if`` returns and what the REPL prints.

Trap
----

Remember, first, that the :lname:`Scheme` model is to effectively
*replace* the failing code with the *handler*, in other words,
whatever the handler returns is what the original call returns.

We need to be able to indicate which kind of condition we are
interested in, some handler code and the set of code this is going to
be valid for:

.. parsed-literal::

 trap *condition* *handler* *form+*

where

- ``condition`` can be a single named condition type or a list of
  named condition types

- ``handler`` is a unary function which is given the condition
  instance if the condition type matches

- ``form+`` is the set of code the trap is valid for

This gives us code of the likes of (using both an anonymous function
and the ``{`` on the end of the line trick visually twice, albeit
lexically once):

.. code-block:: idio

 a := #[ 1 2 3 ]

 trap ^rt-array-bounds-error (function (c) {
				#f
 }) {
   array-ref a 4
 }

where

.. code-block:: idio

   (function (c) {
      #f
   })

constructs my handler -- which could have been reduced to
``(function (c) #f)`` -- and

.. code-block:: idio

   {
      array-ref a 4
   }

is my body forms.

    The slightly weird indentation of the body of the anonymous
    function is the result of my limited abilities with hacking an
    Emacs mode although I've come to rather like it.  The body
    statements are two spaces indented from the word ``function``.

Here in the body forms, ``array-ref a 4``, we try to access the fifth
element of a three element array, ``a``.  This will result in an
instance of ``^rt-array-bounds-error`` being created and raised which
will look for a handler by walking back out through the installed
handlers.

We happen to have installed an ``^rt-array-bounds-error`` handler
immediately beforehand (:socrates:`lucky break!`) so this will be
found and run.  In this case the body of the handler is simply ``#f``
and as this handler is being run in place of ``array-ref a 4`` then
``#f`` is passed to its continuation (not shown).

Now that might not be what you expect, shouldn't we have seen some
error?  Shouldn't we have collapsed back to the prompt?  What does my
code do with ``#f``?

Certainly in the case of the latter point, why are you asking me, you
wrote the code!  What you're really asking is how do I handle array
bounds exceptions?  Well, that's up to you but you might want to test
the value you just got back and compare it to ``#f``.

    ``#f`` isn't a very good sentinel value anyway as, amongst other
    things, it is the default value for an array element!  Rather, you
    might want to use a genuinely unique magic number courtesy of
    ``eq?`` and the uniqueness of values created on the underlying
    :lname:`C` heap:

    .. code-block:: idio

       a := #[ 1 2 3 ]
       magic := pair 'magic 'value
       
       trap ^rt-array-bounds-error (function (c) {
				      magic
       }) {
         v := array-ref a 4
	 if (eq? v magic) ...
       }

    Here, ``magic`` the variable refers to a pair on the heap which
    *cannot* ``eq?`` any other pair on the heap (even if created with
    the same elements) because ``eq?`` does a :lname:`C` pointer
    comparison.  So, armed with something unique, return that from
    your handler and compare against it.  (Even better if ``magic`` is
    a lexically private variable.)

    Others might have suggested that you check the size of the array
    first but at least this method flexes your algorithmic muscles.

We can change the handler to print a message and get someone else to
sort it out:

.. code-block:: idio

 a := #[ 1 2 3 ]

 trap ^rt-array-bounds-error (function (c) {
			        eprintf "Dun goofed!\n"
				raise c
 }) {
   array-ref a 4
 }

(no surprises that ``eprintf`` *printf*\ s to *stderr*)

Now, the ``raise c`` expression (re-)raises ``c`` to whomever further
out in the condition handler tree is willing to handle
``^rt-array-bounds-error``.

The chances are that no-one is except the system condition handlers
which will splurge some message to *stderr* and restart processing
from some safe place:

.. code-block:: console

 Dun goofed!

 foo.idio:line 7: ^rt-array-bounds-error: array bounds error: abs (4) >= #elem 3: idio_array_ref

(The ``abs (4)`` refers to the idea that you can index an array from
the end using negative numbers but either way is more than the array's
size, 3.)

We don't have to (re-)raise ``c``.  Conditions are just things, we can
create a different condition and raise that instead.

Syntactic Sugar
^^^^^^^^^^^^^^^

The basic idea behind trapping conditions works well enough but we're
lacking some syntactic sugar to do two things:

- we probably want something like the familiarity of :lname:`Python`'s
  ``try``/``except`` where there is a single body form but multiple
  handlers associated with it:

  .. code-block:: python

     try:
         form+
     except TypeA_Exception:
         handler1
     except TypeB_Exception:
         handler2

  which looks like it can be re-shaped into nested ``trap`` statements
  fairly easily:

  .. code-block:: idio

     trap TypeB_Exception (function (c) {
			     handler2
     }) {
       trap TypeA_Exception (function (c) {
			       handler1
       }) {
         form+
       }
     }

  noting the ordering rework from lexical to nested!

- add ``trap``'s continuation as something a handler can invoke to
  collapse the function call tree:

  .. code-block:: idio

     trap $condition (function (c) {
		        eprintf "Giving up!\n"
			trap-return 37
     }) {
       ...
     }
     <trap-return to here>

Not implemented.

Comments
========

:lname:`Scheme` has a rich set of comment mechanisms.  So let's do
*more*.

Line
----

You can comment everything to the end of the line with ``;``.

There is some sense of styling when using this form of comment where a
single ``;`` is normally beyond the end of the text and is a
line-specific comment.  Usually indented to column 40 (or more).

A double semicolon, ``;;`` is usually indented to the same level as
the block of code.

A triple semicolon, ``;;;`` is usually indented at column 0.

S-exp
-----

You can usually comment out an entire s-exp with ``#;`` including
multi-line s-exps:

.. code-block:: scheme

 (let ((a 1))
  #;(set! a
          (+ a 1))
  a)

should avoid ``a`` changing value.

I'm not sure is all :lname:`Scheme` implementations support this.

Multi-line
----------

Traditionally, :lname:`Scheme`\ s supports multi-line comments with
``#|`` through to ``|#``.  A commenting style that can be nested --
making commenting out blocks of code containing already commented out
blocks much easier.

That's a good idea.

.. sidebox:: I appreciate this isn't quite the paradigm Knuth is
             suggesting but just let's roll with it.

But this is where I want to differ.  I like the idea of
:ref-author:`Donald Knuth`'s `literate programming`_ although I'm
unsure that it should be natural language interspersed with code
snippets.  I fancy it should be code interspersed with natural
language -- the sort of thing that can be contained in commentary.

However what we need is something to extract those comments and pipe
them into some documentation generation system, and that's where a
multi-line commentary system bracketed by something involving a ``|``
symbol says to me "pipe it out".  Albeit we've not identified, to
what.

Suppose, then, we take the first line (of the ``#|``) and it can
describe the necessary documentation generation system and whomsoever
is extracting the commentary can execute some appropriate system.

I'm being slightly vague there as, primarily, I don't have any feel
for that that documentation generation system might be.  So,
currently, ``#|`` is just a nested multi-line comment waiting... for
Godot?

We should still be able to have regular nested multi-line comments
though without the fear that they'll be emitted to some external
system?  Of course.  Let's pencil in ``#*`` through to ``*#``.

And what's the point unless those two look out for one another?  So
you should be able to both embed literate commentary inside regular
commentary and, of course, be able to comment out parts of your
literate commentary.

Finally, some complexity.  The nested commentary systems are a bit
naive.  They are only looking out for themselves and each other.  You
might be a bit unfortunate with something like:

.. code-block:: idio

 #*

 ; don't use *# here

 *#

with the predictably hilarious result that the reader will find the
closing ``*#`` in the middle of the line comment and start processing
again with the word ``here``.  Not brilliant.

To prevent that we need an escape character which, to no-one's
surprise is ``\``:

.. code-block:: idio

 #*

 ; don't use \*# here

 *#

But wait, ``\`` is my favourite character for my comments!  *<sigh>*

OK, the first character after ``#*`` or ``#|``, if it is a graphic
character (ie. not whitespace) is the escape character:

.. code-block:: idio

 #*%

 ; don't use \% %*# here

 *#

where ``\`` does nothing, ``%`` will first escape a space character
then escape the ``*`` preventing the line comment ending the
multi-line comment.  The nominal result being ``...\ *#...``.

*No, you can't use whitespace as an escape character!*
