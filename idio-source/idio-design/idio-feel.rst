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
complexity's sake.  What the language implementation needs to make
this worthwhile is the ability to enforce the testing of the option
type in the caller's code.

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

We can use :ref:`interpolated strings <interpolated strings>` but the
obvious :lname:`C`-style ``sprintf`` function (cf. ``format`` in
:lname:`Python`) does a lot of heavy lifting for us.

I have included the notion of a *substring* in :lname:`Idio`.  My
thinking is that a lot of the time we're splitting strings into fields
in the shell and rather than re-allocate memory for all of these why
not have an offset and length into the original string?  It works
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
will dedicate some time to it :ref:`later <idio unicode>`.

I'd like to say :lname:`Idio` can handle Unicode everywhere but that's
a work in progress.

Of course there is an implication for not being ASCII any more,
:lname:`Idio` expects its source code and inputs to be encoded in
UTF-8.

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

Anyway, we need a reader input form: ``#U+hhhh``.

Where ``hhhh`` is the commonly used Unicode code point hexadecimal
number.

The traditional :lname:`Scheme` reader input form for characters is:
``#\X`` for some ``X`` so, with our near-ASCII hats on:

.. code-block:: idio

   #\A
   #\b
   #\1
   #\ħ

will create instances of the (now Unicode) characters, ``A``, ``b``,
``1`` and ``ħ`` (U+0127 (LATIN SMALL LETTER H WITH STROKE)).

For Unicode code points in general we get into a bit of a mess.  The
``#\X`` format will always work (assuming that ``X`` is valid UTF-8)
but the person viewing the source code might not see anything useful.
In fact, I'm assuming you can see the correct glyph for ``ħ`` and not
some substitute "box character."

.. aside::

   There's a decent chance I wouldn't spot anything wrong in the ASCII
   range!

The problem lies in your viewer's (text editor, web viewer) ability to
draw the corresponding code point's `glyph`.  I don't know if you have
appropriate support for displaying glyphs outside of the "usual" ASCII
ranges.  My editors and fonts (I'm largely using *DejaVu Sans* and
X11) don't do a very good job outside of the Unicode BMP plane (the
first 65,536 codepoints) and I wouldn't know if they did a decent job
*within* that code plane.

So, by and large, we're probably better off using the ``#U+127``
format for "exotic" characters in order that we give other users an
outside chance of figuring out what we're up to.

Exotic Base Types
^^^^^^^^^^^^^^^^^

I haven't needed, yet, any further exotic fundamental types.  A
fundamental type is one where there is some performance or efficiency
gain to be had for the construction (and deconstruction for printing)
of what is, fundamentally, a string in the source code.

GUID
""""

Post-creation, are these used in any way other than to compare them or
print them out?

Commonly manipulated forms include (for the same GUID):

.. code-block:: text
   
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
though chunking an IPv4 network up into /20 blocks was a bit annoying
-- and I did convert everything into 32bit numbers.  Chunking my IPv6
address might be more fun.

IPv6 addresses have many forms too:

.. code-block:: text
   
   fe80:0000:0000:0000:01ff:fe23:4567:890a
   fe80:0000:0000:0000:1ff:fe23:4567:890a
   fe80:0:0:0:1ff:fe23:4567:890a
   [fe80::1ff:fe23:4567:890a]
   fe80::1ff:fe23:4567:890a
   fe80::1ff:fe23:4567:890a%3

Pathnames
"""""""""

Pathnames are a constant vexation and I can't quite decide how to fix
the problem.  :socrates:`What problem?`  Well, the problem is that
pathnames should probably be treated specially.

Most pathnames that we use are functionally strings albeit ones we
frequently pass as symbols (or words in :lname:`Bash`):

.. code-block:: bash

   $ ls "${filename}"

Here, ``ls``, is read by :lname:`Bash` as a word and :lname:`Idio`
might read in as a symbol and, assuming the symbol ``ls`` wasn't bound
to a value would give us a... symbol for the element in functional
position -- our future command to be executed.  Even in :lname:`Bash`,
``"${filename}"`` undergoes parameter expansion and quote removal to
leave you with the *word* ``foo.txt``, or whatever.  Obviously(?),
``"${filename}"`` is a valid construction in :lname:`Idio` with the
value, er, ``"${filename}"`` -- you probably just wanted ``filename``.

In both cases, however, the *intent* is that we find both ``ls`` and
``foo.txt`` in the filesystem which means they must be converted to
:lname:`C` strings (being careful about ASCII NULs!) before ``ls`` is
found on the user's :envvar:`PATH` (via a lot of calls to
:manpage:`access(2)`) and then :manpage:`ls(1)` will ultimately
:manpage:`stat(2)` ``foo.txt``.

Is there value at this point in handling these elements as special
strings?  That's where I'm not sure.  I have a sense that we should
but we don't.

File globbing will return a list of :lname:`Idio` strings.  As things
stand we are assuming the encoding is UTF-8 which is *so so* wrong --
I mean, only *technically* wrong.

There are **no** encoding specifications for \*nix filenames.  About
the nearest you'll get to a specification is that a \*nix filename is
a sequence of bytes excluding U+0000 (ASCII NUL) and a directory entry
also excluding U+0027 (SOLIDUS -- forward slash).  How you interpret
those bytes is up to you.  Or, rather, how you avoid interpreting
those bytes defines you.

So, in that sense, we shouldn't be treating filenames coming from or
going to the filesystem as anything other than an opaque array of
:lname:`C` characters.  Symbols and strings we get from :lname:`Idio`
source code will, by definition, be Unicode code points (originally
encoded as UTF-8) but after that it's all a bit free.

So, taking an example, I want a file called ``© 2021``.  We're already
in trouble with the first character!  Should that be the ISO8859-1_
character number 0xA9?  Hmm, if someone is using the ISO-8859-2
encoding, a listing is likely to *show* them a ``Š``, Unicode's U+0160
(LATIN CAPITAL LETTER S WITH CARON).  Any UTF-8 decoding will get an
error.  This character encoding mixup is called `Mojibake
<https://en.wikipedia.org/wiki/Mojibake>`_.

Mind you, the problems of interpreting/displaying bytes for files in
the wrong code page has been true since forever (well, post ISO-8859
and other implementations in the 1980s).

There's another, slightly more insidious, problem with displaying
arbitrary strings of bytes in that, quite often, those sequences of
bytes can control the terminal.  If you type :program:`ls` and your
terminal jumps into an Alternate Character Set then you'll be most
aggrieved.

In fact, how do we even *create* such a character?  An :lname:`Idio`
string, ``"©"``, will have assumed UTF-8 in the source which, when
recreated/deconstructed into UTF-8 is a two byte sequence, 0xC2 0xA9.

Well, as it happens, our :ref:`c-api` lets us create arbitrary
:lname:`C` base types with the :samp:`C/integer-> {n} char` function
albeit we probably don't want to create filenames character by
character.

If we want to use :lname:`Idio` strings as the basis for filenames
(hint: we do), we also have the problem of "wide" characters in
Unicode-based strings, ie. those where the Unicode code point is more
than 0xFF.  We can, of course, simply use the UTF-8 encoding as the
filename but then we're mixing up encodings (remember, the filesystem
has none) with the danger of retrieving a filename from the filesystem
which has an invalid UTF-8 encoding, like the 0xA9 in our ISO 8859-1
``© 2021``.

Hmm.  What's to do?

* In the first instance, if the user supplies an :lname:`Idio` string
  as a filename then we'll use the UTF-8 encoding of that string to
  access or create the file.

  .. code-block:: idio-console

     Idio> "© 2021"
     "© 2021"
     Idio> "\ua9 2021"
     "© 2021"
     Idio> "\xc2\xa9 2021"
     "© 2021"

* If we retrieve filenames from the file system then they will be in a
  "pathname" encoding, ie. just a stream of bytes.

Of course, we should allow a user to create a "pathname" encoded
filename (string) for *special purposes*.

In particular, the :lname:`Idio` string, ``"\xa9 2021"`` will get a
U+FFFD (REPLACEMENT CHARACTER) when it is used as a regular string and
printed to a UTF-8 expectant terminal:

.. code-block:: idio-console

   Idio> "\xa9 2021"
   "� 2021"

because the :lname:`Idio` UTF-8 decoder was unable to decode 0xA9 when
reading in the string.  In other words this is a problem for
:lname:`Idio` inputting what it thought was UTF-8 source.

So we need to force the interpretation of the "string" as raw bytes --
most of which are likely to be perfectly valid UTF-8 encoded Unicode
code points!  I've mulled over ``%`` introducing formatted things
(referencing :manpage:`printf(3)`'s format specifier) and so a ``%P``
pathname format which *doesn't* interpret the string as UTF-8
(although it probably will be mostly UTF-8 in the source code).  Now I
can say:

.. code-block:: idio-console

   Idio> %P"\xa9 2021"
   "© 2021"

Of interest, the reason you're seeing the copyright symbol, there, is
because the REPL has printed the value and :ref:`printf <printf>` will
force a UTF-8 interpretation of 0xA9 which we can see with
:program:`od`:

.. code-block:: idio-console

   Idio> printf %P"\xa9 2021\n"
   © 2021
   #<unspec>
   Idio> printf %P"\xa9 2021\n" | od -t x1
   0000000 c2 a9 20 49 61 6e 0a
   0000007
   #t

Notice the ``c2 a9`` (before the ``20``) the UTF-8 encoding of 0xA9
itself?

However, we can use a simpler (printing) interface:

.. code-block:: idio-console

   Idio> puts %P"\xa9 2021\n"
   � 2021
   6

With U+FFFD (REPLACEMENT CHARACTER) indicating that 0xA9 isn't valid
UTF-8 input for this terminal and the ``6`` means that
:manpage:`write(2)` wrote 6 bytes.  :program:`od` shows what was
output:

.. code-block:: idio-console

   Idio> puts %P"\xa9 2021\n" | od -t x1
   0000000 a9 20 32 30 32 31 0a
   0000007
   #t

This time we can see the raw ``a9`` (before the ``20``).  In other
words this is a problem for *the terminal* inputting what it thought
was UTF-8 source.  Looks pretty similar to the problem of
:lname:`Idio` failing to decode a UTF-8 input stream before and
therefore makes verifying correctness more... *fun* when an input
failure and an output failure are visually identical.

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
shell.  I fancy I will need to change my mind again.

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

This requires a little tweak to the evaluator to identify a right-hand
odd-number of ``*`` symbols in the name of the last formal argument
and if so quietly re-write the function's form as an improper list.

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

You can access the array using negative indexes to index from the end.

Following the :lname:`Scheme` model we would create and access arrays
along the following lines:

.. function:: make-array size [default]

   :param size: initial array size
   :type size: integer
   :param default: default element value
   :type default: any

   ``default`` defaults to ``#f``


.. code-block:: idio

   a := make-array 2 "and"
   array-ref a 1			; "and" - default value here, #f normally
   array-set! a 0 "sue"
   array-ref a 0			; "sue"

   array-push! a "rita"
   array-length a			; 3

   array-ref a 99			; *error*

Naturally, armed with infix operators we can confuse ourselves with
``=+`` and ``=-`` for push and pop and ``+=`` and ``-=`` for shift and
unshift.  (Hint: think about whether the ``+``/``-`` is before or
after the ``=`` -- and they really should have an ``!`` in them as
they are modifying the underlying structure but there's a limit).  So
I can say:

.. code-block:: idio

   a =+ "too"

to push an element on the end and:

.. code-block:: idio

   a += "bob"

to *unshift* (a :lname:`Perl`-ism?) onto the front.

:lname:`Scheme`\ s allow conversions of an array to and from a list
(``list->array`` and ``array->list``) which are neat enough ways to
initialise an array.  We'd probably like something more familiar such
as:

.. code-block:: idio

   a := #[ 1 2 3 ]
 
   array-ref a 2			; 3
 
with ``#[ ... ]`` being an array constructor.

Hashes
^^^^^^

Of course, these are *de rigueur*.

Not only will we use them for the usual... *stuff* ... but they are
the native representation of many structured interchange/file formats
like:

* JSON_ (from 2000?)

* it's more accommodating derivative, JSON5_ (from 2012)

* YAML_ (2001)

* and the new pretender TOML_ (2013).


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

.. sidebox:: But haven't implemented.

:lname:`Python` might use a JSON-style construct to initialise a
dictionary which I quite like.



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

.. _`dot operator`:

dot operator
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

I've also allowed for the *index* to be a (named) function where the
(now mis-named) index is applied to the value allowing us to write:

.. code-block:: idio

   str.split-string

which is trivially transformed into:

.. code-block:: idio

   split-string str

Hardly rocket science albeit ``split-string`` is defaulting to using
:var:`IFS` as the delimiter.  Here we might write a function to get
the first letters of each word:

.. code-block:: idio

   str := "hello world"

   define (foo s) {
     map (function (w) {
	    w.0
     }) s.split-string
   }

   printf "%s\n" str.foo		; (#\h #\w)
   printf "%s\n" str.foo.2		; w

.. note::

   The ``.2`` in the ``str.foo.2`` is accessing the second element of
   a list.  Strings and array are indexed from 0 (zero) but lists from
   their first element.

.. rst-class:: center

\*

This ``.`` syntactic sugar is much easier to read and understand (for
us simple folk) although there is a cost.  :lname:`Idio` is a dynamic
language where only values have types and we can only reason with
those types at *runtime*.

This means the :ref:`dot operator` has to plod through testing to see
if its left hand side is an array, hash, string, structure, ... and
call the appropriate accessor function.  That makes it relatively
expensive.

So, write the underlying accessor function out in full by hand if
speed is an issue.

Maybe, if, possibly, we did some *type inference* work we could
recognise that ``h`` is a hash and therefore re-write the dot
operation ``h."a"`` as ``hash-ref h "a"`` directly.

.. warning::

   The dot operator is far from a panacea.  In particular, the fact
   that it will allow you to use variables to walk over an array, say,
   :samp:`arr.{i}`, where :samp:`{i}` is some loop variable is great.

   Until you want your ``i`` to be the symbolic name of a structure
   field, say, :samp:`si.sym` and you've only gone and defined a
   variable called ``sym`` somewhere else in your code.

   Here you can force ``sym`` to be the symbol ``'sym`` or use a
   type-appropriate accessor such as one of the field accessor methods
   for your structure's type, say, ``st-sym si``.

Handles
^^^^^^^

I don't like the name *ports* -- *I* immediately thought of TCP/IP
ports and was mildly confused.

.. sidebox:: I'm much happier, now, thanks!  It all makes *sense*.

Executive decision: I'm renaming them *handles* like :lname:`Perl` and
others.  So, file handles and string handles.

.. _templates:

Templates
=========

.. sidebox:: I should work in PR!

Macros in :lname:`Lisp`\ s have had a bad press.  If we rename them
*templates* then we're halfway to sorting the problem out, right?

Also I find the quasiquoting hard to read: :literal:`\``, ``,`` and
``'`` combine to become a bit unintelligible (to non-:lname:`Lisp`\
ers).  On top of which, I quite like ``$`` as a sigil telling me I'm
about to expand some expression, it's much more
shell-ish/:lname:`Perl`-ish.

Here's my thinking.  I'm going to replace ``quasiquote`` itself with
my *template* which is not only going to be a bit weird for the reader
but I need to indicate the start and end with, say, ``{`` and ``}``,
so something like:

.. code-block:: idio

   #T{ ... $(h."a") ... }

Getting a little ahead of myself I was thinking about the problem of
here-documents where the snippet may be targeted for a language which
itself uses ``$`` as a sigil.  So what we need is the ability to
indicate we want to use a different sigil for ``unquote`` -- we could
actually use ``(unquote ...)``, the function call, but nobody does
that.

So ``#`` is required to tell the reader something weird is coming and
``T`` tells it to handle a template.  Then ``{`` is there to mark the
start of the "block" of quasiquoted code.  Can we squeeze in some
flags, maybe, to indicate a change of ``unquote`` sigil between the
``T`` and the ``{``?  Of course we can!

There's more, though.  We've also ``@``, the extra sigil for
``unquote-splicing`` -- which is fine as a default, we should be able
to change that.  Hang on, ``'`` is the sigil for ``quote``'ing things
(again) -- which, again, is fine as a default, we ought to be able to
change that too.  Finally, we could do with some means of escaping any
of the above.  By default, in :lname:`Idio` -- it's not a
:lname:`Scheme` thing -- that is ``\``.  Which is the, er, universal
escape sigil.

The upshot of that is that we can let loose and say:

.. this code block is text as the lexer won't handle the change in sigils

.. code-block:: text

   #T!%:;{ ... !%(a.3) $foo ... }

where ``!%`` is now our ``unquote-splicing`` sigil (assuming ``a.3``
results in a list, of course!) and on we go with, say, ``(... 1 2 $foo
...)`` in our hands!

If you only wanted to change the escape sigil, say, you can use ``.``
for the others meaning use the default: ``#T...!{ ... }``.

.. sidebox:: There's probably a way round even this but I think we're
             flexible enough for now.

If you want to use ``.`` as your ``unquote`` sigil (or any other),
*tough!*

*Clearly* there's no immediate need to change any *template* sigils
even if the snippet is for :lname:`Scheme` as the ``unquote`` sigil,
``$`` doesn't conflict with :lname:`Scheme` and we can embed one
within the other with ease (probably, must try it!).

.. _`pathname templates`:

Pathname Templates
------------------

Pathname templates have been suggested as a means to isolate
shell-globbing meta-characters from :lname:`Idio`'s hungry hungry
:strike:`hippo` :ref:`dot operator`.

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

   the-txt-files := #P{ *.txt }

   ...add/delete .txt files...

   ls -l the-txt-files

and only get the files extant at the time of invoking :program:`ls`.

Work in progress.

.. _`sorted pathname expansion`:

Sorted Pathname Expansion
^^^^^^^^^^^^^^^^^^^^^^^^^

.. sidebox:: I find it hard to believe this is still missing.

One thing we **must** be able to do is *sort* the result of pathname
expansion.  How many people have resorted to bespoke mechanisms to get
the newest, largest, most *whatever*-est file from a set of files?

In :lname:`Perl` we can use the ``glob`` function to match filename
patterns:

.. code-block:: perl

   cmd (glob ("*.txt"));

and it's not such a step to add an anonymous function to sort the
results:

.. code-block:: perl

   cmd (sort { ... } glob ("*.txt"));

That said, if we wanted to sort the files by *modification time*, say,
we would want to hand the work off to a function that will *glob* the
pattern, :manpage:`stat(2)` each file (caching the results), sort the
list by modification time from the ``stat`` results and return the
sorted list:

.. code-block:: perl

   cmd (do_sorting_stuff ("*.txt"));

I think we can do something similar in :lname:`Idio`.  We need a
little bit of help first in that we need an actual sorting function.
GNU's :ref-title:`libc` only supports :manpage:`qsort(3)` but we can
fall back on our :lname:`Scheme` friends and SRFI-95_ gives use some
useful sorting and merging functions, here:

.. function:: sort sequence less? [key]

   :param sequence: initial array sequence
   :type sequence: array or list
   :param less?: comparison predicate
   :type less?: function
   :param key: value to be sorted accessor
   :type key: function

which will return a new sequence sorted according to ``less?`` (a
comparator function) where the value to be compared for each element
of ``sequence`` can be retrieved by calling the function ``key`` with
the element.

In other words, ``sort`` is smart enough to let you sort by something
that isn't the actual element in ``sequence`` but rather a value you
can derive from each element.

With that indirection in mind, to sort by *size* or *modification
time* etc. we need to :manpage:`stat(2)` all the files in question and
then call ``sort`` with an appropriate accessor into our *stat*'ed
data.

That, in turn, requires not just the ability to call
:manpage:`stat(2)` but also access to something that can compare two
:lname:`C` ``size_t``\ s (or ``time_t``\ s or ...).

.. sidebox::

   Whilst ``libc`` (named after the standard :lname:`C` library) is a
   true :lname:`Idio` module, the ``C`` in ``C/<`` is more of an
   indication that you're using something in the :lname:`C` domain.

There is a ``libc/stat`` function which returns a ``C/pointer``
structure where the fields are named after their ``struct stat``
equivalents and a ``C/<`` function for those two.

Here's a snippet showing the code for sorting by ``sb_size``.

.. code-block:: idio
   :caption: :file:`lib/path.idio`

   sort-size := #n		; global scope

   {
    sort-stats := #n

    key-stat-size := function (p) {
      sort-stats.p.sb_size
    }

    sort-size = function (l) {
      sort-stats = make-hash #n #n ((length l) + 10)

      for-each (function (p) {
	sort-stats.p = libc/stat p
      }) l

      sort l C/< key-stat-size
    }
   }

Using, ``sort-size`` as an example, where it is called with a list of
pathnames.  It points the private variable ``sort-stats`` at a new
hash big enough for the list of pathnames passed in and then walks
over that list assigning the results of the ``libc/stat`` call to an
entry indexed by the pathname.

.. sidebox::

    This sorting works (surprisingly well) but there's a little bit of
    artifice currently involved in using it regarding how the pathname
    expansion works.

It can now call ``sort`` with the original list, the :lname:`C`
comparator function and a function that knows to access the
``sb_size`` field from the table of ``libc/stat`` results.

A reversed version of this sort could repeat the function with ``C/>``
although a more :lname:`Scheme`\ ly way would be to have the reversed
function simply call ``reverse`` on the results of ``sort-size``:

.. code-block:: idio

   sort-size-reversed = function (l) {
     reverse (sort-size l)
   }

before we take the full :lname:`Lisp`\ y experience and note that
these are all derivative and that I really only need to know a pair,
``(size sb_size)`` and I can put the rest in a :ref:`template
<templates>`.

.. sidebox:: Read: not implemented yet.

To complete the picture, we need a dynamic
variable, say, ``~glob-sort~``, to be pointed at ``sort-size`` (or
``sort-mtime`` etc.) and for the pathname matching code to call it.

.. code-block:: idio

   ~glob-sort~ = sort-mtime

   files := #P{ *.tgz }

   rm -f files.0

(maybe apply a bit more rigour to your algorithm for choosing which
file to :program:`rm`...)

.. _`string templates`:

String Templates
----------------

String templates would act as a form of here-document rather than a
template *per se* which is for code generation.  For a string template
we are looking to generate a string, *duh!*, rather than some code.

To some degree, the expansion of expressions in the template is
derivative of the work done to convert values into strings for the code
that executes external commands.

Here documents are useful for creating templated output, in
particular, for other commands to use as input.  Ignoring that we're
using :program:`awk`'s *stdin* for the script:

.. code-block:: sh

   awk << EOT
   /pattern/ { print $USER, \$1; } 
   EOT

then we see an issue in that we now have a mixture of shell variables,
``$USER``, and the targeted command's variables which now require
escaping, ``\$1`` to prevent it being interpreted as a shell variable.

What we really want to do is create a string representing the input
for the targeted command and have a distinct interpolation sigil for
our own variables, for example:

.. code-block:: sh

   awk << EOT
   /pattern/ { print %USER, $1; } 
   EOT

So, in the same style as we've seen for templates we might try:

.. code-block:: idio

   awk << #S%{
   /pattern/ { print %USER, $1; }
   }

with ``#S`` telling the reader there's a string template coming, ``%``
changing the ``unquote`` sigil from ``$`` to ``%`` and ``{`` through
to ``}`` delimiting the string.  (We can debate if the template should
honour or elide leading and trailing whitespace).

It assumes that *we* (in :lname:`Idio`-land) have a ``USER`` variable
to evaluate -- which we quite likely do as most people have it set as
an environment variable.

.. sidebox:: TBD

In this particular case, trying to have :program:`awk` use its *stdin*
for both the script and the stream it is trying to filter is doomed.
Clearly what we need is something like :ref:`feel/process
substitution` but for strings.

Expansion
=========

Of the various forms of shell expansion that we said we'd keep:

Command Substitution
--------------------

An old favourite:

.. code-block:: sh

   now=$(date +%Y%m%d-%H%M%S)

(missing a time zone indication etc., yes, I know)

Remember :ref:`string ports`?

.. code-block:: idio

   out := (open-output-string)
   date +%Y%m%d-%H%M%S > out
   now := get-output-string out

Where the IO redirection operator, ``>``, is happy to do the right
thing when given a string (for a filename) or a handle (file or
string).

I guess we could do with another bit of syntax sugar to eliminate the
temporary variable, ``out``, how about:

.. code-block:: idio

   collect-output date +%Y%m%d-%H%M%S

with the value returned by ``collect-output`` being the string of the
output from the command.

This should work for pipelines too!

The IO redirection infix operator ``>`` does something sensible with:

- strings: ``date > "foo"`` -- creating the file, :file:`foo`

- handles, both file and string: ``date > handle``

I suggested before using ``>>`` to capture "output" in a string,
something like:

.. code-block:: text

   date +%Y%m%d-%H%M%S >> now

where the ``now`` variable should be assigned the result of the
``get-output-string`` on the temporary string handle (not shown but
obviously like ``out`` above) used to capture the output.

It will confuse many people, mind.

.. _`feel/process substitution`:

Process Substitution
--------------------

I haven't written this yet but what in the shell looks like:

.. code-block:: sh

   ... < <(cmd args)
 
   diff <(pipeline using file1) <(pipeline using file2)

to become:

.. code-block:: sh

   ... < /dev/fd/M

   diff /dev/fd/M /dev/fd/N

is all timed rather nicely as process substitution occurs before IO
redirection hence ``... < <(cmd args)`` becoming ``... < /dev/fd/M``
and then ``<`` can (re-)open the file as input for ``...``.

I was wondering if

.. code-block:: text

   ... <| cmd args

with ``<|`` symbolising the use of a named pipe for the following
command might work -- I guess ``>|`` for the output equivalent.

But that doesn't quite wash as I can't use that twice in the same
statement unless the behavioural code behind ``<|`` is smart enough to
spot the second ``<|`` (and ``>|``) and we sort of assume that ``cmd
args`` extends to the end of the line.

We could simply keep the parentheses and then the command is correctly
delimited and we can have several on the same line.

.. code-block:: sh

   ... <(cmd args)

The problem here, though, is we need to convince the reader to do the
right thing.  It will have seen both ``<`` and ``(`` to determine it
is the named pipe IO variant.  It can then read a list up to the
corresponding ``)`` and then it has:

.. parsed-literal::

   *rhubarb* <( *cmd-list* *rhubarb*

Where the ``<(`` operator behaviour needs to handle the named pipe
business.

Some thought required.

.. sidebox:: :socrates:`Good luck with that!`

In the case of the :program:`diff` example, here some more programming
oriented developers might suggest that we can avoid named pipes
altogether if we write our own :program:`diff` using file descriptors
to the pipelines.

We're of a Unix-toolchain heritage, though, where if someone has
created a useful tool then we should be using it.  We're also a shell
where the overhead of running an external program is not a factor in
the grand scheme *[sic]* of things.

The only real problem with Unix toolchain pipelines is the final form
isn't always easy to consume as it is often destined for the terminal
and a user to pass a eye over.  How do we handle the output of
:program:`diff` programmatically?

Jumping back to the :program:`awk` issue mentioned just before in
:ref:`string templates`, you feel that whatever implements
``<(``/``>(`` could do with doing something sensible if it is given a
string rather than a list:

* create a temporary file
* write the string to the file
* open the file for reading
* generate the ``/dev/fd/N`` form
* run the command
* clean up the file descriptor
* remove the temporary file

That isn't *quite* everything as the provocation to read a script from
a file is different for every command.  Here we might have said:

.. code-block:: text

   awk -f <( #S%{ ... } ) file+

which, because of the way the reader will consume multiple lines when
reading a block might look like:

.. code-block:: text

   awk -f <( #S%{
     awk-ish %this with $that
     awk-ish the other
   }) file+

which takes a little to get used to -- in the sense that a command
line trails over multiple lines -- but, I think, works OK.

(Apart from using ``%`` as a sigil in any scripting language that uses
``printf``.)

Modules
=======

:socrates:`Do we need modules?` *Need* is a very loaded term.  They're
certainly very useful in terms of encapsulating ideas and, indeed,
avoiding some unfortunate name clashes.  Not that unfortunate name
clashes are consigned to the bin but they can be reduced enormously.

Of course everyone and his dog has their own ideas about modules
including :lname:`Scheme` -- or was it the dog?

R7RS :lname:`Scheme` has developed the idea of a *library* involving
expressive (and therefore complex) mechanisms to include bodies of
code.

It's one of those things where it seems too much for us just starting
out.  I fancy something simpler which, like so many things, may become
deprecated over time.

At a high enough level what we want is to allow a developer to Mash
The Keyboard™ to produce *Art* of which they intend to *export*
(ie. make visible to their adoring public) only some *names* of the
many many names they used in the implementation.

The :strike:`gullible` adoring masses can them *import* said *Art* and
those exported names are now available for use locally.

.. code-block:: idio
   :caption: Art.idio

   module Art
   export (
	   beauty
	   light
   )

   ugly := ...
   beauty := not ugly
   
   darkness := ...
   light := not darkness

and then I can:

.. code-block:: idio

   import Art

   printf "shine a %s on %s\n" light darkness

and get an error about ``darkness`` being *unbound*.  I haven't
defined ``darkness`` in my code and nothing I have imported has
exported it.  ``light`` on the other hand is just fine.

Of course we will still get name clashes.  We are (read: I am) keen to
poke about and get up to no good so I quite like the idea of getting
access to :manpage:`read(2)` for which I can write a primitive and
export if from the ``libc`` module.

Hmm, :lname:`Idio` is quite likely to have a function called ``read``
in the reader.  If I:

.. code-block:: idio

   import libc

   read ...

which ``read`` am I going to get?

The answer is... that depends.  What the :lname:`Idio` engine will do
is look to see if the symbol exists in the current module (which
presupposes that we can change the current module) and use such a
symbol if it exists.  Next it will try each of the imported modules'
exported names lists looking for the symbol.

Note, here, that by default, every module imports the ``job-control``
and ``Idio`` modules.  ``job-control`` because that handles ``|`` and
various I/O redirection that everyone expects in a shell and ``Idio``
because that's where most functions are defined.

So, the chances are you're going to get the ``libc`` module's ``read``
function as the reader's ``read`` function is actually in the ``Idio``
module and would therefore only be found as a fallback if we hadn't
imported ``libc``.

:socrates:`What if I want the other one?` You can explicitly ask for
it with:

.. parsed-literal::

   import libc

   *module*/read ...

so, ``Idio/read`` in this case.

You can't ask for names that aren't exported.  That would be wrong.


.. include:: ../commit.rst

