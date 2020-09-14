.. include:: ../global.rst

******************
:lname:`Idio` Feel
******************

Unsurprisingly, :lname:`Idio` takes a lot of its programming language
cues from :lname:`Scheme`.

Data Types
==========

This isn't a comprehensive list -- which we can leave until we cover
the implementation details.

What we're looking to describe here are the entities the reader is
willing to consume and construct objects from.

Simple Data Types
-----------------

Atoms, in :lname:`Scheme`, these are the things are not s-exps.

:lname:`Scheme` introduces more exotic numbers with a leading ``#``
I've used ``#`` as the character to introduce all "funny" types.  In
one sense ``#`` is used by the reader to go into "weird stuff" mode.

Of interest, from that, when printing out *internal* types which have
no reader representation -- in other words it'll have some clues for a
developer but isn't any use in (re-)creating one -- they too start
with a ``#`` and generally look like ``#<...>``.  If a ``#`` is
followed by a ``<`` then the reader will issue an error.

nil/NULL
^^^^^^^^

``#n`` is about as short as we can get.

``nil`` (``NULL``, ``None``, ...) is often used as the "no value"
result which raises the idea of an `Option type`_.

*Anything* that helps the programmer in a complex world has to be a
good thing although adding an option type on its own is complexity for
complexity's sake.  What the language implementation needs is the
ability to enforce the testing of the option type.

I don't think we're there.

Booleans
^^^^^^^^

.. sidebox:: No clues as to which is true and which is false!

``#t`` and ``#f``.

Numbers
^^^^^^^

We won't have a full :lname:`Scheme` *number tower* (think of a
class-hierarchy where integers are rationals (fractions!) are reals
are complex numbers) as I can't believe it's quite necessary for a
shell.  Integers and floating point numbers are common enough.

``1``, ``-2``, ``3.14`` and ``1e100`` (for anyone googling).

Ignoring some of the more esoteric numbers we can possibly input some
simple examples are:

- ``#d`` for decimal numbers: ``#d10`` (yes, a duplicate of the
  default form!)

- ``#x`` for hexadecimal numbers: ``#xff``

- ``#o`` for octal numbers: ``#o007``

- ``#b`` binary numbers: ``#b00001111``

The reader code that handles these allows for any numeric *base* up to
36 (the usual 0-9 followed by a-z/A-Z) although there aren't any
trivial reader input mechanisms.

Strings
^^^^^^^

``"foo"``

Hardly unexpected!  Multi-line, though, as that's normal, right?

.. code-block:: idio

 str := "Line 1
 Line 2
 Line 3"

and we should be able to use familiar escape sequences:

.. code-block:: idio

 printf "hi!\n"

We should be able to poke about in strings and get individual index
references back in the usual way.

There is no single-quoted string, partly as ``'`` is used by the
reader as a macro but also because ``"`` isn't doing any variable
interpolation.  ``"$PATH"`` is just five characters.

I haven't needed to use an interpolated string so far.  An obvious
:lname:`C`-style ``sprintf`` function (cf. ``format`` in
:lname:`Python`) does a lot of heavy lifting for us.

I have included the notion of a *substring* in :lname:`Idio`.  My
thinking is that a lot of the time we're splitting strings into fields
in the shell and rather than re-allocate memory for all of these why
not have an offset and length into the original string.  It works
pretty well although how efficient it is is hard to tell.  There is
obviously the pathological case where you only want the single
character substring of a two GB file....

.. sidebox:: Technically, we probably mean ISO10646_ as Unicode_
             describes more than a set of "characters" but semantic
             associations regarding those characters (upper/lower case
             variants, left-to-right etc.).

	     Unicode is a more widely recognised name.

Although not mentioned previously, :lname:`Idio` should be able to
handle Unicode_ in strings.  Unicode is, uh, a *complication* and we
will dedicate some time to it later.

I'd like to say :lname:`Idio` can handle Unicode everywhere but that's
a work in progress.

Of course there is an implication for not being ASCII any more,
:lname:`Idio` expects its source code to be encoded in UTF-8.

Characters
^^^^^^^^^^

We'll mention it in passing but it becomes a thing later, we need to
be able to handle characters.

*\*ducks\**

It is too soon in this text to be discussing it but the idea of a
"character" is slipping away in the modern age.

Here, what we really mean is, given :lname:`Idio` is Unicode-oriented,
that we want to be able to read in a Unicode *code point*.

While Unicode code points are just integers -- there's potentially 2\
:sup:`21` of them -- they are a distinct set from regular integers: 1,
2, 3... not least because some of them are invalid.

This would break a few :lname:`Scheme`-ish libraries which might try
to manipulate a :lname:`C`-ish ``c + 1`` for some character ``c``
which make some assumptions about characters being ASCII_.

Anyway, we need a reader input form:

``#U+hhhh``

Where ``hhhh`` is the commonly used Unicode code point hexadecimal
number.

Exotic Base Types
^^^^^^^^^^^^^^^^^

I haven't needed, yet, any more exotic fundamental types.  A
fundamental type is one where there is some performance or efficiency
gain to be had for the construction (and deconstruction for printing)
of what is, fundamentally, a string in the source code.

GUID
""""

Post-creation, are these used in any way other than to print them out?
I guess there's a comparison of GUIDs that can be made which could be
equally done as a string (albeit slower).

Commonly manipulated forms include (for the same GUID):

::
   
   {123e4567-e89b-12d3-a456-426652340000}
   (123e4567-e89b-12d3-a456-426652340000)
   123e4567-e89b-12d3-a456-426652340000
   123e4567e89b12d3a456426652340000
   urn:uuid:123e4567-e89b-12d3-a456-426655440000

IP Addresses
""""""""""""

My screen-scraping quite often results in a CIDR notation, being an IP
address and a subnet mask, IPv4 and IPv6.

Is there a need for a fundamental type?  Are they manipulated often
enough?  Maybe.  I've survived for a while in the shell without them
though chunking an IPv4 network up into /20 blocks was a bit annoying.
Chunking my IPv6 ULA_ (think RFC1918_ private address space but for
IPv6 spiced up with 40 bits of randomness and then 16 bits of /64
address space within that) might be more fun.

IPv6 addresses have many forms too:

::
   
   fe80:0000:0000:0000:01ff:fe23:4567:890a
   fe80:0000:0000:0000:1ff:fe23:4567:890a
   fe80:0:0:0:1ff:fe23:4567:890a
   [fe80::1ff:fe23:4567:890a]
   fe80::1ff:fe23:4567:890a
   fe80::1ff:fe23:4567:890a%3

Compound Data Types
^^^^^^^^^^^^^^^^^^^

:lname:`Scheme` doesn't come out of the box with any (other than the
pair-derived list) but :lname:`Idio` is not :lname:`Scheme`.

Pair
^^^^

OK, we will have pairs -- and therefore lists -- but let's call a pair
a pair and we'll construct one with ``pair`` and get the head and tail
with ``ph`` (pair head) and ``pt`` (pair tail) respectively.

.. code-block:: idio

 p := pair 1 2
 ph p			; 1
 pt p			; (2)

The :lname:`Lisp`\ y ``cadr`` and friends become the :lname:`Idio`\ y
``pht`` etc..

I have deliberately departed from :lname:`Lisp`\ s in that I don't use
``.`` in the source/printed form.  Largely because I wanted ``.`` for
structure decomposition although the current choice of ``&`` isn't my
greatest decision:

.. code-block:: idio

 ph '(1 & 2)

is a mental hiccup for people used to backgrounding commands in the
shell.  I fancy I will change my mind again.

One area I definitively want to change is varargs functions.  So,
based on the above, a varargs function is declared as:

.. code-block:: idio

 define (foo a b & c) { ... }

What I really want is to make that more in the style of EBNF_ where
what we're really saying is that ``c`` captures "the rest" of the
arguments supplied to the function.  In an EBNF-ish way, we might have
written ``c*`` giving us:

.. code-block:: idio

 define (foo a b c*) { ... }

This requires a little tweak to the reader to capture an odd-number of
``*`` symbols in the name of the last formal argument and if so
quietly re-write the function's form as an improper list.

You need to be reasonably careful as someone is bound to have a
variable ``*foo*`` with matching ``*``\ s (so is just a regular
symbol) but might be especially determined and use ``*foo**`` to mean
varargs.

Arrays
^^^^^^

Of course.

I've implemented dynamic arrays (partly because I wanted to use them
internally for a stack) but note there is a subtlety in
differentiating between the current size of the array in memory and
how many elements are in use.

Broadly you can use any element up to the highest in-use element and
you can push/pop and shift/unshift elements onto the array (affecting
the number of elements in the array, obviously).  When you create the
array, you're creating *n* slots now as a hint to avoid (possibly
repeated) re-allocations of memory as the array grows.

Following the :lname:`Scheme` model we would create and access arrays
along the following lines:

.. code-block:: idio

 a := make-array 10
 array-ref a 1			; #f - default value
 array-set! a 1 "bob"
 array-ref a 1			; "bob"

 array-push! a "sue"
 array-length a			; 11

 array-ref a 99			; *error*

Naturally, armed with infix operators we can confuse ourselves with
``=+`` and ``=-`` for push and pop and ``+=`` and ``-=`` for shift and
unshift.  (Hint: think about whether the ``+``/``-`` is before or
after the ``=`` -- and they really should have an ``!`` in them as
they are modifying the underlying structure but there's a limit).  So
I can say:

.. code-block:: idio

 a =+ "rita"

to push an element on the end.

:lname:`Scheme`\ s allow conversions of an array to and from a list
(``list->array`` and ``array->list``) which are neat enough ways to
initialise an array.  We'd probably like something more familiar such
as:

.. code-block:: idio

 a := #[ 1 2 3 ]
 
 array-ref a 2			; 3
 

Hashes
^^^^^^

Of course, these are *de rigueur*.

Not only will we use them for the usual... *stuff* ... but they are
the native representation of many structured file formats like JSON_
(from 2000?)  (or it's more accommodating derivative, JSON5_ (from
2012)), YAML_ (2001) and the new pretender TOML_ (2013).

They're going to work in a similar way to arrays:

.. code-block:: idio

 h := make-hash #n #n 10

the ``#n`` indicate to use the default equivalence and hashing
functions (don't worry for now!).  The ``10`` is, again, a hint as to
how much memory to allocate.

.. code-block:: idio

 hash-set! h "a" "apple"
 hash-ref h "a"			; "apple"

and a similar initialiser using pairs:

.. code-block:: idio

 h := #{ ("a" & "apple") ("b" & "banana") }

 hash-ref h "b"			; "banana"

:lname:`Python` might use a JSON-style construct to initialise a
dictionary.

Structures
^^^^^^^^^^

These seem like a good idea and they're probably going to be the basis
of other things.

In one sense the implementation is quite simple.  You have an
underlying compound data type to store the actual fields, let's say an
array, and the some mechanism to turn the request for a symbolically
named field into a reference to the underlying actual field.

If I could define a structure *type* with:

.. code-block:: idio

 define-struct bar x y

creating a structure type called ``bar`` with fields ``x`` and ``y``.
The declaration of which would create a number of structure
manipulation functions allowing me to create an instance of one:

.. code-block:: idio

 foo := make-bar 1 2

whereon I can access the elements with getters and setters:

.. code-block:: idio

 bar-x foo		; 1
 set-bar-y! foo 10
 bar-y foo		; 10

That looks a little clumsy with a field reference being:

.. parsed-literal::

   *typename*-*fieldname* *instance*

dot-operator
^^^^^^^^^^^^

It would be useful to have an infix operator come to our rescue for
structures (and arrays and hashes and strings and ..., for that
matter) by expressing our intent and having something else figure out
the detail.  This is where I saw :lname:`Perl`'s `Template::Toolkit`_
and then Jinja_ show the way.

For our structure example:

.. code-block:: idio

 foo.y			; 10

for arrays and hashes and strings you can do the sensible thing:

.. code-block:: idio

 array.10
 hash."a"

you can imagine these are reworked into

.. code-block:: idio

 array-ref array 10
 hash-ref hash "a"

We ought to be able to use variables too as:

.. code-block:: idio

 i := 10
 array.i

seems reasonable.

You can also *assign* to these constructs:

.. code-block:: idio

 array.10 = "rita"
 hash."c" = "carrot"

.. sidebox:: The implementation will make your head hurt.

which will take us into the esoteric world of boxed variables later
on.  

This syntactic sugar is much easier to read and understand (for us
simple folk) although there is a cost.  :lname:`Idio` is a dynamic
language where only values have types and we can only reason with
those types at *runtime*.

This means the *dot operator* has to plod through testing to see if
its left hand side is an array, hash, string, structure, ... and call
the appropriate accessor function.  That makes it relatively
expensive.

So, write the underlying accessor function out in full by hand if
speed is an issue.

Maybe, if, possibly, we did some *type inference* work we could
recognise that ``h`` is a hash and therefore re-write the dot
operation ``h."a"`` as ``hash-ref h "a"`` directly.

Handles
^^^^^^^

.. sidebox:: I'm much happier, now, thanks!

I don't like the name *ports*.  I'm renaming them *handles* like
:lname:`Perl` and others.  So, file handles and string handles.

Templates
^^^^^^^^^

.. sidebox:: I should work in PR!

Macros in :lname:`Lisp`\ s have had a bad press.  If we rename them
*templates* then we're halfway to sorting the problem out, right?

Also I find the quasiquoting hard to read.  :literal:`\``, ``,`` and
``'`` combine to become a bit unintelligible.  On top of which, I
quite like ``$`` as a sigil telling me I'm about to expand some
expression, it's much more shell-ish/:lname:`Perl`-ish..

Here's my thinking.  I'm going to replace ``quasiquote`` itself with
my *template* which is not only going to be a bit weird but I need to
indicate the start and end with, say, ``{`` and ``}``, so something
like:

.. code-block:: idio

 #T{ ... $(h."a") ... }

Getting a little ahead of myself I was thinking about the problem of
here-documents where the snippet may be targeted for a language which
itself uses ``$`` as a sigil.  So what we need is the ability to
indicate we want to use a different sigil for ``unquote`` -- we could
actually use ``unquote``, the function call, but nobody does that.

So ``#`` is required to tell the reader something weird is coming and
``T`` tells it to handle a template.  Then ``{`` is there to mark the
start of the "block" of quasiquoted code.  Can we squeeze in some
flags, maybe, to indicate a change of ``unquote`` sigil between the
``T`` and the ``{``?  Of course we can!  There's more, though.  We've
also ``@`` the extra sigil for unquote-splicing, we should be able to
change that.  Hang on, ``'`` is the sigil for quoting things (again).
We ought to be able to change that too.  Finally, we could do with
some means of escaping any of the above.  By default, in
:lname:`Idio`, it's not a :lname:`Scheme` thing, that is ``\``.

The upshot of that is that we can say:

.. code-block:: idio

 #T!%:;{ ... !%(a.3) $foo ... }

where ``!%`` is now our unquote-splicing sigil (assuming ``a.3``
results in a list, of course!) and on we go with, say, ``(... 1 2 $foo
...)`` in our hands!

If you only wanted to change the escape sigil, say, you can use ``.``
for the others meaning use the default: ``#T...!{ ... }``.

.. sidebox:: There's probably a way round even this but we're flexible
             enough for now.

If you want to use ``.`` as your unquote sigil (or any other),
*tough!*

*Clearly* there's no immediate need to change any *template* sigils
even if the snippet is for :lname:`Scheme` as the unquote sigil, ``$``
doesn't conflict with :lname:`Scheme` and we can embed one within the
other with ease (probably, must try it!).

Pathname Templates
^^^^^^^^^^^^^^^^^^

Pathname templates have been suggested as a means to isolate
shell-globbing meta-characters from :lname:`Idio`'s hungry hungry dot
operator.

.. code-block:: idio

 ls -l #P{ *.txt }

I guess, in a similar fashion, we should consider different
meta-characters although it would require re-working internally as
:manpage:`glob(3)` won't change its meta-characters.

Of interest is the wildcard expression, like preparing a regular
expression in :lname:`Perl` or :lname:`Python`, is not to be expanded
until it is required.

You should you should be able to say:

.. code-block:: idio

 txt-files := #P{ *.txt }

 ...add/delete .txt files...

 ls -l txt-files

and only get the 

String Templates
^^^^^^^^^^^^^^^^

String templates would act as a form of here-document rather than a
template *per se* which is for code generation.  For a string template
we only, indeed must, generate a string.

Expansion
^^^^^^^^^

Of the various forms of shell expansion that we said we'd keep:

Command Substitution
^^^^^^^^^^^^^^^^^^^^

An old favourite:

.. code-block:: sh

 now=$(date +%Y%m%d-%H%M%S)

(missing a time zone indication etc., yes, I know)

Remember :ref:`string ports`?

.. code-block:: idio

 out := (open-output-string)
 date +%Y%m%d-%H%M%S > out
 now := get-output-string out

That's how it is at the moment.  I guess we could do with another bit
of syntax sugar to eliminate the temporary variable, ``out``.

The IO redirection infix operator ``>`` does something sensible with:

- strings: ``date > "foo"`` -- creating the file, :file:`foo`

- handles, both file and string: ``date > handle``

Thinking aloud, something like:

.. code-block:: idio

 date +%Y%m%d-%H%M%S >" now

where ``>"`` is symbolising that the output of the preceding command
should be captured and the ``now`` variable should be assigned the
result of the ``get-output-string``.

It doesn't look too clever, though.
 
Process Substitution
^^^^^^^^^^^^^^^^^^^^

I haven't written this yet but it looks like:

.. code-block:: sh

 ... < <(cmd args)

could be re-written as:

.. code-block:: sh

 ... <| cmd args

with ``<|`` symbolising the use of a named pipe for the following
command.

Filename Patterns
^^^^^^^^^^^^^^^^^

In :lname:`Scheme` ``(ls *.txt)`` would be a list of just ``ls`` and
``*.txt``, no pathname expansion has occurred and ``*.txt`` is a
valid, if unusual, variable name.  A first pass at providing pathname
expansion would result in ``(ls (file1.txt file2.txt ...))`` but who would
do it and when?

In general, ``(cmd args)`` would have ``args`` evaluated.  Perhaps,
then, the atom/symbol ``*.txt`` would need to be scanned for *filename
patterns* and expanded to a list if one is found.

Internal commands can handle a list being passed as an
argument. External commands would be expecting the list to be
flattened: ``ls file1.txt file2.txt ...``.  Perhaps the mysterious
mooted fallback function will flatten any args into a individual
words?  As, of course, it must as :manpage:`execvpe(3)` only accepts a flat
list of words.

Sorted Filename Patterns
""""""""""""""""""""""""

How can we sort a filename pattern?

::

 cmd *.txt

where we want to give ``cmd`` a particular ordered list.  The normal
behaviour for sorting is to sort lexicographically according to the
locale.

In *Perl* we would have to include the ``glob`` function to match
filename patterns regardless:

.. code-block:: perl

 cmd (glob ("*.txt"));

so it's not such a step to add a sort:

.. code-block:: perl

 cmd (sort { ... } glob ("*.txt"));

That said, if we wanted to sort the files by modification time we
would want to hand the work off to a function that will *glob* the
pattern, ``stat`` each file (preferably caching the results), sort the
list by modification time from the ``stat`` results and return the
sorted list:

.. code-block:: perl

 cmd (do_stuff ("*.txt"));

Underlying this is that we really want ``glob`` to do the hard work
for us (especially noting that it's doing some sorting anyway).
Perhaps we need some dynamic state to prompt the globbing code to do
the right thing:

.. code-block:: scheme

 (dynamic-let ((*glob-sort* 'stat-mtime))
   cmd *.txt)

where ``stat-mtime`` might be a library function, supplied by the
globbing code, to ``stat`` the files and sort by modification time.

Environment
^^^^^^^^^^^

You can manipulate the process' environment variables in the shell
just like regular shell variables.  We could do the same with, say,
(yet) another environment sat alongside the global environment.

::

 PATH = /here:/there

would find ``PATH`` in the global process environment and could
reference and assign to it there.

The previous ``dynamic-let`` for selecting the sorting algorithm looks
a bit like the shell's environment-twiddling functionality::

 TZ=GMT-10 date

Perhaps there's some syntactic sugar along those lines that can
achieve the same transient effect?  The shell's manipulation of
process environment variables being like dynamic variables is better
seen with::

 export TZ=GMT
 ...
 (
     TZ=GMT+5
     ...
     TZ=GMT-10 date
 )

We can envisage process environment variables as just dynamic
variables but with an extra flag to indicate they should be exported
to any external commands.

One thing missing, and from the shell, even, is the ability to remove
an environment variable transiently -- you can ``unset`` variables in
the shell but then they're gone in the rest of that (sub)shell.

From an implementation perspective, this requires some extra variable
magic as you need to add in an instance of the variable with an
*unset* flag, which ``meaning-reference`` is aware of, so that as this
dynamic scope unwinds the variable re-appears.

We could use ``~`` to represent dynamism and an optional ``^`` to
represent "up there" for the environment with an additional ``+`` for
creation, ``-`` for deletion/unsetting and ``?`` for usage
(ie. dynamic).  A longhand:

.. code-block:: scheme

 (dynamic-let ((x 2))
   (let (( x 3))
     (dynamic x)
     (+ x 1)))

(resulting in 3) might become::

 {
   ~+ x 2
   {
     x = 3
 
     ~? x
     x + 1
   }
 }

which is debatably readable, and::

 {
   ~^+ TZ "GMT"
   date
 }

In this last example, there is an onus on the user to use a lexical
block in order to remove the transient process environment variable,
otherwise it'll remain at the top-level for later commands.  In that
sense, the separation of assignment and body is not quite the same
as::

 TZ=GMT date

which is the single command-specific but is more akin to running a
sub-shell::

 (
   export TZ=GMT
   date
 )

You could write it longhand to retain the limited extent of the
dynamic variable:

.. code-block:: scheme

 (environ-let ((TZ "GMT"))
   date)

Whether that is easier is moot.

Sometimes, two or more process environment variables are set in
conjunction::

 TZ=GMT-10 LC_ALL=fr_FR date

``dynamic-let`` (or a process environment equivalent) can handle
multiple bindings:

.. code-block:: scheme

 (environ-let ((TZ     "GMT-10")
	       (LC_ALL "fr_FR"))
   date)

whereas the syntactic sugar will require multiple assignments::

 {
   ~^+ TZ     "GMT-10"
   ~^+ LC_ALL "fr_FR"
   date
 }

This is essentially the same as the shell's

::

 (
   export TZ=GMT-10
   export LC_ALL=fr_FR
   date
 )

Which isn't a bad thing, it's just not a short thing - a one-liner.
As all values are bounded, ie. the constructor of a value has a
definite end (whitespace, close parenthesis), perhaps they could be
consumed in pairs?

::

 {
   ~^+ TZ "GMT-10" LC_ALL "fr_FR"
   date
 }

How often is that actually done?  The reader would be expanding ``~^+
a b c d`` into:

.. code-block:: scheme

 (environ-let ((a b)
 	       (c d))
   ...)

Our original dynamic sorted globbing example::

 {
   ~+ *glob-sort* 'stat-mtime
   cmd *.txt
 }

again with the transient lexical block.  Lexical block is now sounding
wrong.

Here Documents
^^^^^^^^^^^^^^

Here documents are useful for creating templated output, in
particular, for other commands to use as input::

 awk << EOT
 /pattern/ { print $USER, \$1; } 
 EOT

Here we see an issue in that we now have a mixture of shell variables,
``$USER``, and the targeted command's variables which now require
escaping, ``\$1`` to prevent it being interpreted as a shell
variable.

What we really want to do is create a string representing the input
for the targeted command and have a distinct interpolation sigil for
our own variables::

 awk << EOT
 /pattern/ { print %USER, $1; } 
 EOT

This would require some dynamism on the part of interpolation -- as we
don't know whether ``%`` is the correct sigil in every case -- hence
we are directed towards a dynamic variable.

Separately, though, we need to indicate that interpolation occurs at
all.  We can interpolate a string with:

.. code-block:: scheme

 (interpolate '* "bar is *bar")

where the interpolation sigil might have been ``*``.  How do we do
that with a here document?

We can't have an all encompassing::

 (interpolate awk << EOT
   /pattern/ { print %USER, $1; } 
 EOT
 )

as both ``awk`` and ``EOT`` are included.  We could try::

 awk (interpolate << EOT
   /pattern/ { print %USER, $1; } 
 EOT
 )

where we recognise ``<<`` and ``EOT`` and interpolate what's lies
between the ``EOT`` markers.  The shell disables interpolation by
quoting the ``EOT`` marker::

 awk << 'EOT'
 /pattern/ { print %USER, $1; } 
 EOT

which would result in the literal string ``%USER`` being passed to
``awk``.

Perhaps we don't do the (rather convenient) here documents in the same
way.  ``{`` introduces a lexical block and ``{{`` a template.  Can we
extend the metaphor so that ``{"`` introduces a string block?

::

 awk << {"%
 /pattern/ { print %USER, $1; }
 "}

Here we have ``{"`` introducing a string block with ``%`` as the
interpolation character.  The actual string starts on the next line
but will end at the matching ``"}`` which may or may not be after a
trailing newline.  The closing delimiter, ``"}``, is all too common in
other languages, ``{print "foo\n"}``, say, so perhaps we need a more
Ruby-esque, say, ``%h`` followed by a choice of matchable bracket
(``{``, ``[``, ``(``, ``<``) whichever is more convenient::

 awk << %h%<
 /pattern/ { print %USER, $1; }
 >

where the second ``%``, in ``%h%``, indicates the interpolation sigil.

*Lua* allows nested quoted strings, ``[===[...]===]`` for different
numbers of ``=`` sigils. Should we have::

 cat << {"
 echo "The awk script result is:"
 awk << {="%
 /pattern/ { print %USER, $1; }
 "=}
 "}

or

::

 cat << %h={
 echo "The awk script result is:"
 awk << %h%=={
 /pattern/ { print %USER, $1; }
 ==}
 =}

for generating code for ourselves?  In the latter case, the embedded
``awk`` code has a ``}`` so both the wrapping ``%h`` here documents
must either use a different bracket sigil pair or use at least one
``=`` sigil.

Iterators
^^^^^^^^^

::

 for x in "$@" ...

``$@`` is an array -- ``"$@"`` assuring that elements with whitespace
in them retain the whitespace and are not subject to word splitting --
and the loop will be run with the variable ``x`` assigned to each
element of the array in turn.  Other languages allow you to iterate
over collection objects so long as, obviously, they support the
iteration interface.

Reader
^^^^^^

Another problem is the reader. Firstly, in an interactive shell we
would type

::

 ls *.tar

whereas :lname:`Scheme` requires something akin to:

.. code-block:: scheme

 (ls *.tar)

We don't want leading and trailing parentheses in a shell.  

That's the least of our worries.  For the most part we might suspect
that :lname:`Scheme`’s parenthesis overload is no more onerous than any other
language's overload for embedded function calls, for example:

.. code-block:: scheme

 (func1 (func2 args) (func3 args))

will be:

.. code-block:: c

 func1 (func2 (args), func3 (args));

in *C* and::

 func1 $(func2 args) $(func3 args)

in the shell.

However, the explicit delimitation of lists would have been a boon for
argument trailing onto the next line:

.. code-block:: scheme

 (let bindings
   body)

where in the shell::

 let-cmd bindings
   body

and the end-of-line ``RETURN`` at the end of ``let-cmd`` bindings
disassociates it from the following body.  We could use continuation
lines::

 let-cmd bindings \
   body

but that has the possibility of becoming intractable with nested
expressions.

There was a Python-esque increase in indentation, though.  Should
whitespace be significant?  The problem with significant whitespace is
that you don't know until you've seen it.  Is

::

 cmd arg

standalone or are we waiting for::

 cmd arg
   another-arg

In general, in the interactive shell, we don't know.  Except maybe we
do.  By time we've read the ``RETURN`` the end of ``cmd arg`` we
should be able to see if ``cmd`` is an internal function, if so, we
can check its arity and compare that to what we've read so far.  If
it's not an internal function then it must be an external command in
which case arg is all we need to execute it.

You can imagine the code to handle the constant retries for more
arguments to be pretty ugly, though.

An alternative is to state that any expression that extends over
multiple lines must be in a list, hence:

.. code-block:: scheme

 (cmd arg
   another-arg)

Other Ideas
^^^^^^^^^^^

Special Case Function Declarations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several languages have implicit syntactic transforms for function
declarations.  For example, ``factorial`` can be simplified with case
analysis in Haskell:

.. code-block:: haskell

 factorial 0 = 1
 factorial n = n * factorial (n - 1)

Implied Argument Passing
^^^^^^^^^^^^^^^^^^^^^^^^

In :lname:`Scheme` we return a value to our caller allowing us an implied
chain of values:

.. code-block:: scheme

 (set! a (car (cdr (cdr v))))

In *C++* we might do something similar with a temporary object being
passed between functions:

.. code-block:: c++

 T a = v.cdr().cdr().car();

*Perl* takes the idea further and has an implicit/default variable
``$_`` for many functions:

.. code-block:: perl

 while <*.txt> { print $_; }
 map { $_ + 1; } (1, 2, 3)

*Perl* 6 uses the *whatever* argument, ``*``, extensively though that
leads to the bizarre: ``* * 2`` where the first asterisk is the
whatever variable and the second is multiplication.  We can't use a
hyphen, ``-``, even though it appeals as many external commands use
hyphen to mean ``stdin``.  Let's stick with ``_``.

Where we have a pipeline utilising ``<`` ``|`` and ``>`` to manipulate
the standard IO streams associated with the commands in the pipeline,
should we have some equivalent for internal functions passing
arguments.  Let's try doubling ``|`` up::

 func1 args || func2 _ args

where the result of ``func1 args`` is available as the variable ``_``
for ``func2`` to manipulate alongside ``args``.

There problem is that the more you write such expressions the more
your mind is filled with *C*’s and *Perl*’s logical or: ``func1 args
OR func2 _ args``.  If ``_`` is our implied variable, perhaps it
should be ``|_``, ie. we are piping ``_`` to the next command::

 func1 args |_ func2 _ args

We might use ``<<`` and ``>>`` or, rather, ``<_`` and ``_>``, as
referencing and assigning to some variable::

 a <_ abs _ |_ _ + 1 |_ factorial _ |_ _ - 2 _> b

would be equivalent to:

.. code-block:: scheme

 (set! b (- (factorial (+ (abs a) 1)) 2)

but the overuse of ``_`` makes it hard to read -- ``_`` being hard
enough as it is.

::

 a <+ abs _ |+ _ + 1 |+ factorial _ |+ _ - 2 +> b

Whether the choice of ``_`` makes it clearer is moot, it certainly
shows the sequence of expressions. ``<_`` looks a bit pointless as you
can always replace the first ``_`` with the variable but it might be
useful for code generation.

Spawning
^^^^^^^^

Following this trend, where ``&`` in the shell backgrounds a command,
maybe we can use ``&&`` to spawn a new thread?

Quasiquoting
^^^^^^^^^^^^

If we're using ``{`` for a code block perhaps we should use ``{{`` for
a syntactic transform block?

.. code-block:: scheme

 `(echo bar is ,bar)

might be::

 {{ echo bar is $bar }}

However, we want to avoid using ``$`` as the interpolation sigil as it
is common to many scripting languages we might be looking to invoke in
turn (*Perl*, ``awk``, etc.).  It would be useful to indicate the
sigil of choice::

 (interpolate % {{ echo bar is %bar }})

Perhaps with a second sigil for ``unquote-splicing``.  We could do
with a shorthand for that, say, ``{{% echo %bar}}`` with the first
character after ``{{`` denoting the sigil but we're in danger of some
mis-interpretation issues: ``{{echo %bar}}`` -- does the ``e`` of
``echo`` immediately following the ``{{`` mean that it is the
interpolation sigil and therefore the quotation is returned as

::

 %bar

with an error about the missing ``cho`` variable?  Do we have to
enforce whitespace after ``{{``?

Data Structure Access
^^^^^^^^^^^^^^^^^^^^^

An idea from the *Template::Toolkit*, a *Perl*-based template
processing system, is to indirect through data structures using the
dot operator:

.. code-block:: jinja

 [% client.name %] 
 [% FOREACH item = shopcart.contents %]
      <li>[% item.name %] : [% item.qty %] @ [% item.price %]
 [% END %]

\ 

 The Template Toolkit will automatically Do The Right Thing to access
 the data in an appropriate manner to return some value which can then
 be output. The dot operator '.' is used to access into lists and
 hashes or to call object methods.

 ^^^ Template::Toolkit webpage

Here, we might see::

 myarray.num.str

to access a *Perl*-ish ``$myarray->[$num]->{$str}``, ie. array index
``$num`` of the array reference ``$myarray`` should be a hash table
and we access the element given by index ``$str`` of that.

The dot operator would descend the array/hashtable hierarchy using the
next element of the dot operator as the index into the object reached
so far.

List access might be::

 mylist.cdr.cdr.car

There is a simple look to that although the need to pass any arguments
to any functions becomes more interesting.  Suppose we want to get the
fourth field of a ``/``-delimited string::

 str.split "/".3

doesn't scan very well.  Is that a single dot operation or two
elements, ``str.split`` and ``"/".3``?  A parser might assume that
``split`` takes some default arguments (``SPACE``, ``TAB`` and
``NEWLINE``, the default shell ``IFS``, or intra-field separator) but
what would ``"/".3`` mean?

How about re-visiting ``||`` and the implied argument ``_``::

 str.split "/" || _.3 eq "foo" ...

The result from ``split`` and therefore ``_`` will be an array which
we can access the fourth element of.

Assuming, that is, that ``split`` is clever enough to merge its
supplied arguments, ``"/"``, with the dot operator-supplied ``str``.
Perhaps the simpler::

 split str "/" || _.3 eq "foo"

As an alternative to ``||``, what if we used an operator, ``then``,
which introduced an *anaphoric* variable, ``it``?

::

 split str "/" then it.3 eq "foo"

or in a longer example::

 read-line then split it "/" then it.3 eq "foo"

In a :lname:`Scheme`-ly fashion this might be:

.. code-block:: scheme

 (let ((it (read-line)))
   (let ((it (split it "/")))
     (eq? (vector-ref it 3)
          "foo")))

in our putative language it might be a syntax transformation to::

 {
   it := read-line
   {
     it := split it "/"
     eq? it.3 "foo"
   }
 }

Regular Expressions
^^^^^^^^^^^^^^^^^^^

The shell uses filename pattern matching a great deal, ``*``, ``?``,
``[...]``.  It is very concise and satisfies many cases especially
when augmented with the ksh-originated extended pattern matching
operators ``?(pattern)``, ``+(pattern)`` etc..  A long time spent
typing ``tar *.txt`` doesn't really want to be forced into ``tar
.*\.txt`` to satisfy some regular expression wonks.

Many shell commands such as ``grep`` and ``awk`` use the (confusingly
similar) basic and extended regular expressions.  These primarily
differ from filename matching in that ``*`` and ``?`` apply to a
pattern (which might be ``.``, meaning any character, giving the
shell's ``*`` being the regular expression ``.*``) but go on to
introduce other regular expression concepts including back-references.

*Perl* Compatible Regular Expressions, PCRE, take us to the dizzyingly
baroque heights of *Perl*’s take on regular expressions which, people
seem to admit when discussing *Perl* 6, went too far.

Cox [C07]_ notes that the use of back-references leads to exponentially
inefficient code leading to his development of Google's RE2 code:
https://code.google.com/p/re2/.

How might we introduce a regular expression?  What would a regular
expression constructor look like, cf. double quotes, ``"``, used as a
string constructor?  *Perl* introduced its regular expressions with
expressions like ``m/regex/[modifiers]`` -- where the ``m`` could be
omitted if the delimiters were ``/``.  *Ruby* is similar.  As it
stands that would conflict with our liberal variable names,
e.g. ``m/n`` so we need something else.  *Ruby* also has
``%{regexp}``.

VMs
^^^

If we are looking to compile should we consider compiling for an
existing VM where we would benefit from all the virtual machine
knowledge and both regular and JIT compiler knowledge?

JVM is very popular with languages other than *Java* (*Clojure*,
*Scala*, *JPython*, *JRuby* etc.)

*LLVM*, which supports a variety of languages.

*Parrot*, for *Perl* 6 and *Python* and ...?  *Parrot* might be
falling by the wayside for *Perl* 6, though, as *MoarVM* supplants
it.

Is it possible to be compiler/VM agnostic?  Maybe if our language is
simple enough.  Although continuations, let alone closures would test
that hypothesis.

libuv
^^^^^

Born of *node.js*, a standalone *JavaScript* engine for event driven
network application but now at the heart of many applications and
languages including *Rust* and *MoarVM*.

Why Not :lname:`Scheme`?

An existing :lname:`Scheme` would have the benefit of being designed and
implemented by people who know what they're doing -- certainly more
than we do regarding :lname:`Scheme`.  However, we sense we want to modify
the evaluator of :lname:`Scheme` before we can rest on the back of any
existing implementation and therefore we would need to understand the
design and implementation choices made by any given :lname:`Scheme` before
making a decision on whether we can enhance it suitably for our own
purposes -- how easy would it be to augment this existing :lname:`Scheme`
with infix operators and a fallback function springs to mind.

We could, though, use a :lname:`Scheme` as our implementing language, as we
did in the chapters on implementing our proto-:lname:`Scheme`.  Of course,
that means that any distribution of our shell would mandate the
inclusion of the implementing :lname:`Scheme` too.  How would that work if we
were thinking of embedded systems with limited resources?  A
full-blown :lname:`Scheme` implementation with attendant libraries just for
the relatively few :lname:`Scheme` features we need to bootstrap the system.
After all, we only need implement those features we've used to date
from the implementing :lname:`Scheme` which are, to a large degree, the
features we've been looking to implement in our proto-:lname:`Scheme`.

Of course, choosing to not use a :lname:`Scheme` also rules out using any
other implementing language for the same reasons.

That leads us to various "small" implementations of :lname:`Scheme` in *C*
which we might look to re-imagine.  There are any number of trivial
implementations of :lname:`Scheme` in *C*, largely little more than
pedagogical examples or extended homework implementations.  Some go
the extra mile, for example, Nils M. Holm's *Scheme 9 from Empty
Space* [H14]_ which is a thorough implementation of R4RS, a :lname:`Scheme`
standard.  It lacks continuations, however, and is solely an
interpreter without any analysis leading towards compilation.

We are probably set to use the *lingua franca* of Unix, *C*, and write
the whole thing from scratch.  Perhaps no bad thing, we will get a
domain specific engine which we can tune without being waylaid by or
upsetting anyone else.

