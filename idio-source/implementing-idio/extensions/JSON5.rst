.. include:: ../../global.rst

.. _`JSON5 extension`:

*****
JSON5
*****

To paraphrase that old adage about writing cryptographic libraries:

    The first rule of writing a JSON library is that you do not write
    a JSON library.

    --- Wiser men than us

Of course, we are not wise but, armed with our limited knowledge, we
are *dangerous*.

In truth, I didn't want to write a JSON library, isn't the point that
someone else has written one already?  Indeed, what's the pressing
reason for getting involved with JSON at all?

Well, for good or for ill, JSON has become a *de facto* data
interchange format for REST-oriented systems.  And we'll probably want
to talk to REST-oriented systems at some point so our card is marked.

JSON itself, now RFC8259_, appears in the guise of a *machine* data
interchange format except that, as is the way, it has become a
configuration format and is obligingly human-editable.

Humans are rubbish, though, and they:

* like to throw in a comment or two as `aide-mémoire
  <https://en.wikipedia.org/wiki/Aide-mémoire>`_ and, despite an early
  iteration that did support comments, JSON does not support comments

* like to delete lines of configuration meaning that trailing commas
  become a thing which is illegal in JSON

* like to use regular identifiers as the names in JSON objects rather
  than strings.

So JSON5_ was created to accommodate these things and some other
`fettling <https://en.wiktionary.org/wiki/fettle#Verb>`_ around
unrepresentable numbers that JSON explicitly denies.

.. sidebox::

   Interestingly, a favourite bugbear, whilst JSON5 supports comments
   in a JSON5 token stream, they are not accommodated in the resultant
   structure.  It is a one way trip for your precious thoughts, they
   don't make it through the gate.

So, job #1, find a JSON5 library.

In my first pass I could see that JSON5 involves Unicode and so if the
JSON5 library *doesn't* make heavy use of Unicode then it isn't likely
to be correct.  Hmm, that rules a few out.

You also notice that whilst JSON5 is read in, by and large, only JSON
is printed back out.  I don't think that is hugely unreasonable but it
is interesting.

I then hit upon Simon Schoenenberger's `standalone C library for JSON5
<https://github.com/detomon/json5>`_.  Slightly more importantly, is
his `Unicode character lookup table
<https://github.com/detomon/unicode-table>`_ work.  You can read more
about my re-imagining in :ref:`USI` and its changes to how Unicode is
handled in :lname:`Idio`.

Parser
======

.. aside::

   You had one rule.  Only one rule...

Enthused, I immediately broke rule one, above, and started writing a
JSON5 parser which turns out, thanks to the use of :lname:`ECMAScript`
Identifiers, to be far more tiresome than hoped.

As an interesting aside, :lname:`ECMAScript` lets you use Unicode
characters in Identifier names which is good, right?  Even more
interestingly, it lets you use *Unicode Escape Sequences* in
Identifier names: ``\u00337`` is the, otherwise illegal, Identifier
``37``.  Illegal because an Identifier must start with (*broadly*) a
"Letter" but can also start with a Unicode Escape Sequence.

It also has a throwback to :lname:`JavaScript`'s UTF-16 roots in that
such Unicode Escape Sequences can only encode code points in the Basic
Multilingual Plane (code points up to and including ``U+FFFF``).
Above that you must use the `UTF-16
<https://en.wikipedia.org/wiki/UTF-16>`_ high-surrogate + low
surrogate two step shuffle.

.. aside::

    And, probably, for things not all that extreme.

In the end, though, we have a passable, inefficient, JSON5 parser
which, doubtless, fails *in extremis*.

The code is set up to be used standalone or as part of an extension to
:lname:`Idio`.

As it can be used standalone, the code enforces :lname:`C`'s numeric
limitations.

Limits
------

The JSON[5] format is a bit vague on limits, particularly, numbers.

:socrates:`Should there be any limits?` Maybe?  It's meant to be a
machine data interchange format after all!

There does appear to be tacit acceptance that in practice :lname:`C`
might be a limiting factor.  This is lightly `addressed
<https://datatracker.ietf.org/doc/html/rfc8259#section-6>`_ in
RFC8259_ noting merely that by constraining output to such 64-bit
formats:

    good interoperability can be achieved by implementations that
    expect no more precision or range than these provide

Integers
^^^^^^^^

Integers, ultimately, :lname:`ECMAScript` `NumericLiterals
<https://262.ecma-international.org/5.1/#sec-7.8.3>`_, are an
unbounded sequence of decimal or hexadecimal digits and the decimal
variant can have a signed exponent of an equally arbitrary number of
digits.

In practice, though, my suspicion is virtually everything interacting
with JSON is 64-bit bounded.  What should we make of the `withExponent
example <https://spec.json5.org/#numbers>`_ of ``123e-456``?

.. aside::

   We clearly need some homeopathic numeric type.  I didn't see that
   in the `Scheme Number Tower
   <https://en.wikipedia.org/wiki/Numerical_tower>`_.  Poor show!

The current code handles that badly, I calculate, *\*ahem\**, 0, as
the JSON5 processing part stores decimal numbers as a :lname:`C`
``int64_t`` and shifting 123 by 456 orders of magnitude doesn't leave
much behind.

The JSON RFC implies the use of IEEE 754 binary64 double precision
numbers even for integers with the effect that integers are bounded
to, roughly, +/- 2\ :sup:`53`.

Of note, IEEE 754 binary64 supports slightly fewer (significant)
decimal digits, 15-17, in its mantissa than a native :lname:`C`'s
``int64_t``.

Of course, :ref:`bignums` are a thing but are my bignums anything like
your bignums?  We defined :lname:`Idio` to support arbitrary
significant digits (albeit they get normalised to 18 frequently) and a
32-bit exponent.  What do your bignums support, assuming you have any?
How can we share information reliably?

We're back to `wishy-washy
<https://www.collinsdictionary.com/dictionary/english/wishy-washy>`_
commentary from the RFC:

    A JSON number such as 1E400 or 3.141592653589793238462643383279
    may indicate potential interoperability problems, since it
    suggests that the software that created it expects receiving
    software to have greater capabilities for numeric magnitude and
    precision than is widely available.

.. sidebox::

   My other favourite bugbear is that there is no version numbering
   let alone options flagging.

I can't help but think that the standard of a machine data interchange
format ought to, maybe, define some limits.  Offer some options for
extensibility, maybe?

Floating Point Numbers
^^^^^^^^^^^^^^^^^^^^^^

Again, many systems will be using :lname:`C`'s ``double`` which is
limited to exponents of +/- 340 or so which won't stand up to the
arbitrary precision possible in JSON5.

Interestingly, that means we couldn't have stored ``123e-456`` as a
floating point number either!

Implementation
==============

Reading
-------

JSON5 is designed for data interchange so the ultimate goal is for us
to extract our *local interpretation* of the textual message.

.. sidebox::

   RFC8259_ now `mandates UTF-8
   <https://datatracker.ietf.org/doc/html/rfc8259#section-8.1>`_
   which, presumably, applies to JSON5 as well.

In the very first instance, I am assuming that the input stream is
UTF-8 and I've chosen to use the same multi-width technique as for
:lname:`Idio` strings meaning I can extract individual code points
without subsequent re-interpretation of the UTF-8 input stream.

This means we're already facing a double memory allocation.  In the
first instance we need to allocate memory for the UTF-8 input stream
and then we allocate memory for a multi-width array of code points
based on that input stream.

.. sidebox::

   The code has no especially good reason to be able to run standalone
   but that's how it was written.

   I don't think it makes too much of a difference.

In order to make it standalone it falls back to :lname:`C` limitations
on numbers, especially.

The "unicode string" can then be tokenized using the `JSON5 grammar
<https://spec.json5.org/#grammar>`_.  This is where the
:lname:`ECMAScript` rules for Identifiers and Numbers come into play.
The result of this should be a chain of JSON5 tokens (identifiers,
punctuation, strings and numbers) each of which has an associated
JSON5 value.

We can then parse the chain of tokens to validate the input stream
from which we should be able to derive a single JSON5 value -- the
bound up collection of values.

No tokens is a fail and any left over tokens is a fail, of course.

.. sidebox::

   ``NaN`` is *explicitly* not legal JSON and explicitly legal JSON5
   for that very reason.

The usual JSON[5] we see is an object, ``{ ... }``, although the
shortest valid JSON5 could be a single digit decimal number, ``{}``,
``[]`` or ``""``/``''`` with ``NaN`` a close contender.

Strings (and identifiers) are reasonably straight-forward although you
need to be leery of the various escape sequences allowed thus creating
the more tiresome act of validating the input stream.

:lname:`ECMAScript` Identifiers can have

* *UnicodeEscapeSequences* in them, ``\uHHHH``

  including the UTF-16 high-surrogate + low-surrogate pairs

whereas strings can have any of the more common

* *C-style*, ``\n``

  including the ``\q`` for non-special code points meaning ``q``

* *HexEscapeSequences*, ``\xHH``

* the same *UnicodeEscapeSequences* as for Identifiers

* and escaped *LineTerminatorSequences* as JSON5 users get to
  experience multi-line strings (albeit with the *LineContinuation*
  bodge).  *Woo!*

What this means is that we have to reallocate identifiers and strings
*again* to accommodate any escape sequences.  Technically, an escape
sequence will result in a shorter string -- as two code point ``\\``,
the four code point Hex- and six or twelve code point
Unicode-EscapeSequences reduce to one code point -- but the chances
are the escape sequence is generating a wider character than the
(commonly) ASCII single byte width source text, so the whole
identifier/string value needs widening.

Given that JSON5 identifiers are only used as alternatives to strings
for the "member names" in objects (and differ in the rules about their
construction and escape sequences) then treating them subsequently as
strings seems to be OK.

Number values, as noted, are limited to :lname:`C`'s ``int64_t`` and
``double``.

.. aside::

   And remember to ``json5_value_free()``!

Overall, then, we're left with a ``json5_value_t *`` to do something
with.

Into Idio
---------

Given that JSON5 allows for some literals, strings, numbers, objects
and arrays then, I think, we have a reasonably straight-forward
translation into :lname:`Idio` symbols, strings, numbers, hash tables
and arrays.

There doesn't appear to be any requirements for those JSON5 values
that lie beyond those we use in :lname:`Idio` ourselves other than
constraints on numbers.  Hopefully, :lname:`Idio`'s limits lie beyond
:lname:`C`'s so we should be able to accommodate anything in a
``json5_value_t``.

Of course, the downside of going via :lname:`C` values is that we
could have accommodated a wider set of JSON5 numbers directly, largely
as :ref:`bignums`, although I'm struggling to see a use case.

I'm thinking of the ``123e-456`` example which requires that the
sender have some expectation that the receiver can store such a value.
Does the sender know the capabilities of the receiver?  It's not like
there was a HTTP- or SSH-style exchange of headers to agree a set of
acceptable limits.

.. aside::

   That's the *fourth* time!  Yikes, don't tell anyone!

In the meanwhile, we get to allocate strings *again* as, whilst the
multi-width "unicode string" format is the same, the ``json5_value_t``
is likely to get freed shortly after conversion into an :lname:`Idio`
string so we can't be lazy.

Numbers, of course, will need the "full" conversion into fixnums and
bignums.

Writing
-------

Going the other way, generating JSON5 from an :lname:`Idio` value is
slightly less traumatic albeit we hit the JSON5/JSON conundrum.

What is the receiver expecting?  We're not in the HTTP-negotiation
loop so we don't know what format is being agreed.  In the first
instance, I think we can only safely generate JSON, like everyone
else.

That's hardly the end of the world, the JSON5 format was constructed
for the convenience of humans not machines albeit legal JSON5 terms
are not necessarily legal JSON terms.

In the first instance, there is no need to translate the :lname:`Idio`
value into ``json5_value_t`` values, we merely need to validate it
then print it.  Validation being that the value consists of JSON
elements, largely, objects and arrays, although there's that hinted at
nuance.

If we read in JSON5, ``NaN`` is a valid value.  It is not valid JSON
-- which only accepts ``null``, ``true`` and ``false`` literals.
JSON5's ``NaN`` could become JSON's ``"NaN"`` with attendant
mis-interpretation -- did I mean the `IEEE-754 NaN
<https://en.wikipedia.org/wiki/NaN>`_ or the (ostensibly random
three-letter) string ``"NaN"``?

We could, of course, claim that ``NaN`` is invalid JSON -- which it is
-- which means that the read/tweak/write loop becomes the more risky
read/tweak/barf loop.

I'm more tempted to fail as there is some legitimacy in failing to
generate JSON than there is to second-guess how to mangle JSON5's
extras into JSON.

An alternative is to upgrade the output to JSON5 if we see any
JSON5-specific elements and hope that the next guy is JSON5-aware.

I guess the defining approach would be to have two generators, albeit
largely the same code, which validate and generate JSON and JSON5
distinctly.

One interesting side-effect of our choice of processing
identifier-style "member names" as strings is that we are unable to
distinguish them as (originally) identifiers when writing.  Indeed we
can't distinguish between (originally) single- and double-quoted
strings.

.. aside::

   Hopefully the web page shows a nice musical score glyph!  My source
   text has the usual box with 01F and 3BC and :program:`xterm` is
   showing a box with a question mark.

   That's the result of my choice of X11 font and utilities,
   obviously, but I am that human reading that JSON as though it was
   meant for me...

Another string-issue is that we are unable to reproduce any of the
original escapes from the input stream.  The `Example 2
<https://spec.json5.org/#escapes>`_ of ``'\uD83C\uDFBC'``, which is
``U+1F3BC, MUSICAL SCORE``, will be emitted as a UTF-8 sequence: 🎼.

That's not wrong but it's not Art.  How might we choose to re-escape
code points?

Pernicious RFC detail for `strings
<https://datatracker.ietf.org/doc/html/rfc8259#section-7>`_: the
"control characters" ``U+0000`` through ``U+001F`` MUST be escaped.  I
can't say as I've ever noticed that although, in my defence, I don't
recall ever having had a snippet of JSON where I expected to have a
control character in a string.  It must be true.  Of all
implementations.

Another side-effect is that hexadecimal numbers in the original will
have been translated to integers and not remain flagged as hexadecimal
numbers when we come to output them with the examples of ``-0xC0FFEE``
and ``0xdecaf`` becoming the less obvious ``-12648430`` and ``912559``
respectively.

None of these side-effects should matter as JSON[5] is a machine data
interchange format.  But humans like to read the output.

From Idio
---------

With a mechanism to read JSON5 from an external UTF-8 source --
presumably a file (descriptor) -- it shouldn't be too much effort to
reuse the existing code to read JSON5 from an :lname:`Idio` string.

Even if we need to reallocate the space (as neither the JSON5 code nor
the :lname:`Idio` code know how long they other will maintain the
memory allocation) at least the underlying multi-width "unicode
string" format is the same so it is a quick copy.

That means we should be able to say:

.. sidebox::

   Noting the annoying escaped double-quotes!

.. code-block:: idio

   v-in := json5/parse-string "
   {
     foo : \"bar\"
   }
   "

Albeit what we really want to do is pass :lname:`Idio` hash tables
etc.:

.. code-block:: idio

   v-out := json5/generate {
     foo : "bar"
   }

The question is, what is :samp:`{v-out}`?  It's a string, the UTF-8
representation of the JSON5 encoding of the :lname:`Idio` hash table
(as a JSON5 object).

What we are saying, here, though, is that there is no native JSON5
type in :lname:`Idio`.  That's not to say that ``json5_value_t``
etc. have disappeared it's that they are not accessible to
:lname:`Idio`.  They were used, fleetingly, in translation, like a
(normal) programming language's `Abstract Syntax Tree
<https://en.wikipedia.org/wiki/Abstract_syntax_tree>`_.

We read a JSON[5] input stream from an external source (file or
string), have it validated and a local representation of the data
returned.

When we convert :lname:`Idio` values to JSON[5], we don't get some
cascading JSON[5] structure, we just had that in the :lname:`Idio`
value, we get the UTF-8 representation of the wire-ready JSON[5]
(output) stream.

.. include:: ../../commit.rst

