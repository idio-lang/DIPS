.. include:: global.rst

############
Introduction
############

I want to create a programmable shell.  At least that's the easiest
way of describing it.  I want to have the power and expressibility of
a proper programming language whilst at the same time utilising the
elegant abstractions of the shell for command orchestration.

But command orchestration is the ultimate goal -- just with some nice
programming features.

My background has been a mixture of Unix systems administration,
provisioning hardware and software infrastructure and developing tools
and toolchains for engineers.  I've covered a lot of ground albeit
without actually doing anything that might be considered customer
facing.  When asked what I do, there's no easy categorisation so I've
shrugged and answered ... *stuff*.

System administrators are always writing shell scripts -- with more or
less attention to the niceties of programming.  Every new system
requires some customisation to fit into the local computing
environment and that experience gets encoding into setup scripts.

New software and new releases of software all require some
experimentation to discover their models of operation then appropriate
massaging to fit in with the way we work *here*.  Encode those local
customisations into installation shell scripts.

Invariably, that software will behave erratically and produce reams of
logs and output.  We need more bespoke shell scripts to monitor and
manage it.  How do we do alerting, here?  Do we send an email (and
hope someone reads it)?  Is there a local alerting system (hopefully
with someone watching it)?

Even something as simple as taking a backup using the software's own
backup scripts will usually require some shell scripting to run pre-
and post-checks to manage historic accumulated backups and available
disk space and so on.

Further, these local customisations are of their time and place.  Not
only are your computers in your network different to my computers in
my network but we both *change* our computers and the environment they
run in over time.  The shell scripts are in permanent flux.  The lucky
ones are under version control!

On the other hand I also write software for engineers to use.
Generally, software that roams around the computing infrastructure,
interacting with other systems, querying a database, poking a REST
interface, gathering information, applying some change.

These *always* start with a shell script.  I know to :command:`netcat`
-this, or :command:`ssh` with a particular key to obtain some bespoke
behaviour -that.  Most commands print unstructured text to *stdout*
which we can "screen scrape" to find out our facts.  :command:`sed`,
:command:`grep` and :command:`awk` are our best friends although we
can do a fair amount of twirling and twiddling directly in the shell
with ``IFS`` and arrays and pattern matching and parameter expansion.
Need :lname:`Expect` to poke about in a bespoke User Interface to find
some status?  No problem.

But then I always do have a problem when I start to gather similar
information from more than one source and I need an ostensibly simple
list of lists or hash of arrays or, in fact, anything that reveals the
shell's great computing problem.  If computing is algorithms and data
structures, the shell can ``if`` and ``while`` with the best of them
but it only has flat arrays for data structures.

Suddenly, we're goosed.  Our world-conquering shell script has thrown
us off at the first hurdle.

Programmers will turn to :lname:`Perl` (in my youth) or
:lname:`Python` (in my attempts to remain young) or some other
"proper" programming language and that's great.  We can gloss over the
problem of running all those commands interacting with the environment
by calling ``system`` (or whatever will, in turn, simply invoke the
shell again!) and capture the output in some convoluted way.

Only a paragraph or two ago we could have run ``a=$(cmd args | this |
that)`` and carried on our merry way.  Yes, we can call, say,
``popen`` and then ``read`` from a file descriptor until we get an end
of file indication and in the meanwhile be ``realloc``'ing memory for
the output to go into and then arrange for that data to be accessible
as a variable -- and, obviously, that is what the shell is doing --
but no-one is interested in that.  *Just run this command and give me
the output!*

Of course, everybody has to handle the command pipeline failing
outright or even failing to produce the expected output, there are no
short cuts for anyone.

However, we've traded a succinct abstraction for a lot more systems
code (interaction with the operating system) with attendant error
handling for the sake of richer data structures.  Should we have to?
We've moved on, we're at a higher level where a command and its output
are our units of computing.  We're a *shell*.

That's the thinking behind :lname:`Idio`, the language.  I could have
just written a reference manual, a few tutorials etc. and called it a
day but in trying to implement :lname:`Idio` I hit a problem.  I
couldn't for the life of me, find out *how* (to a large part) but more
importantly *why* some languages were written the way they were.  They
simply exist, *de facto*, without explanation and have done so for
decades -- :lname:`Python` is a relative stripling at 25 years old.
You need to reverse engineer thousands upon thousands of lines of code
without explanation which still won't tell you why someone chose a
particular implementation.

.. aside:: *idiot* wasn't deliberate when I just typed it but it is
           very apt.  I was half-listening to Radio 4 on the commute
           home when somebody mentioned idiots on the grass -- whereon
           I starting thinking about Pink Floyd lyrics -- to come back
           to the word for idiot derives from the Greek, *idios*,
           meaning private or doing one's own thing.

	   There are too many *i*\ s and *o*\ s to follow that
	   noughties penchant for dropping vowels from names so I took
	   the alternate approach and dropped a consonant.  ergo
	   :lname:`Idio` (to mix my ancient languages).

	   Sadly, the Middle English (a person of low intelligence)
	   from the Old French, *idiota* (an ignorant person), may be
	   more befitting.
   
Maybe they are well-documented and I'm an idiot -- my Google-fu has
let me down.  Maybe so.  However, it has prompted me to try to explain
how *I* made my design and implementation decisions about
:lname:`Idio` which might help you make your design and implementation
decisions for your language.  If nothing else, *not like he did it!*

So that is the purpose of this treatise.  I'm going to look at the
shell and argue for the things I like and ignore the things I don't.
I'm also going to throw in some things I think would be useful for
someone like me to have in a shell.  I'm then going to look at my
programming language of choice, :lname:`Scheme`, and argue as to why
it does what we need it do.  :lname:`Scheme`, it transpires, does an
awful lot more besides which we can benefit from although there is a
decent argument that it does too much and that we should hold back
from some of its more baroque and entangled features.  We'll then look
at how to implement a Scheme-ish language from basic interpretation
through to byte compilation.  If :lname:`Scheme` could do the things
we want then the smart people behind :lname:`Scheme` would already
have done so, so we need to discuss how to, *ahem*, butcher it until
it bends to our will!  That leads to some tricky compromises.

There's another, more reflective, reason for this rambling.  In my
experience when I have tried to explain what I have done in written
prose using examples I had not tried myself I discover that my casual
understanding is, in fact, an abject misunderstanding -- and, often as
not, a poor implementation.  If I can satisfactorily explain how
:lname:`Idio` works then there's a decent chance it's actually doing
what it says on the side of the tin.

.. rst-class:: center

---

One obvious question is, why am I writing a new shell at all?  Aren't
there lots of perfectly good shells already out there and even more
perfectly good programming languages?  Why don't I hack away at
:lname:`Bash`, say, and look to support nested data structures or, if
I'm really determined to have my shell abstractions, couldn't I look
into the bowels of :lname:`Python` and see if I can't slip a ``|``
into the code reader?

.. sidebox:: :lname:`Python`, I confess, might be better than most for
	     design documentation -- although I've not looked for any
	     as I don't want to use it for the programming part of my
	     programmable shell.  YMMV

Well, yes, I could have pursued either approach but we're back to that
business of not having an intimate understanding of the design of the
language -- and an understanding of the implementation, for that
matter.  There's also that problem we know from experience where the
minor task of changing some perceived simple function of the code
unearths untold assumptions across the piece that you've now broken.
The code might not start up again for days if not weeks whilst you
track down the last unrepentant snippet of code.  I find that that is
true in this code base and I wrote the lot!

There's also the very *size* of the beasties.  :lname:`Bash`'s repo is
a mere 776 thousand lines in 1300 files.  :lname:`CPython`'s repo is
2.2 million lines over 4600 files.  Good luck making sweeping changes
across either of those!  Of course, those repos are not all code but
you'll need to update the documentation and Internationalisation as
well, so count it all in.

Most importantly, I want to know *how* things work.  In fact, I want
to know how *all* the things work.  That means everything.  I'm going
to suggest that we start with nothing, the proverbial blank sheet of
paper, or empty directory in this case, and we use nothing from anyone
else that we haven't :strike:`nicked` :strike:`borrowed`
:strike:`ported` *re-imagined* ourselves such that we can document it
as though we had implemented it ourselves.

The downside of this *Not Invented Here* approach is at best we don't
have world class implementations and at worst we suffer from our own
incompetence and misunderstanding and the codebase becomes a festering
pit of despair -- and they say there's a price to pay for everything.

With this downside in mind we ought to ensure that the codebase is
modular enough that we could swap out subsystem implementations.  I
suspect that that might be "hard" but hopefully not impossible.

.. rst-class:: center

---

Roaming the Internet looking for inspiration on implementing a
programming language I hit on three key sources.

In the first case, like many people, I read :ref-author:`Abelson and
Sussman with Sussman`'s :ref-title:`Structure and Interpretation of
Computer Programs` (SICP) :cite:`SICP` which served as the basis of
MIT's entry-level computer science subject from the 80s.

Skipping the computer science bit, Chapter 4,
:ref-title:`Metalinguistic Abstraction` implements a
:term:`metacircular evaluator`, the basic meaning of which is that if
your programming language is worth its salt you should be able to
implement (a probably weedier, much less efficient version of) your
programming language or some other programming language *in* your
programming language.  You use your programming language to create
other programming languages.

To be fair, no-one is going to get excited that we used :lname:`C` to
implement :lname:`Idio` but there's a sense of "having made it" when
you reach the stage of being able to implement other languages in
yours.  After all, you basically need to be able to read characters,
one at a time, and decide whether to bundle them up into names or
numbers or strings etc. then have a mechanism to evaluating them
maintaining some sense of "memory" where values can be set and
retrieved from.

Chapter 5, :ref-title:`Computing with Register Machines` then goes on
to discuss the transformation of your evaluator (your *interpreter*)
into a language suitable for a traditional computer, a *register
machine*.  This isn't any real world computer but rather a
hypothetical machine whose assembly code is suited to your language.
It has a program counter and registers for shuffling transient data to
and from "memory" like real world computers but the units of operation
are more abstract.

This is the start of the rabbit hole for *Virtual Machines* in a
programming language sense -- we're not talking about virtual machines
as in something to run an operating system on, here we mean something
more like a `Turing machine`_ which will process our instructions.
Almost every language these days uses a virtual machine, a proper
advance from evaluation/interpretation.

:ref-title:`SICP` uses :lname:`Scheme` as its core implementation
language -- much like we will use :lname:`C` -- and the metacircular
evaluator operates on a Scheme-ish language which can become a bit
confusing.  The problem here, though, is that the implementation
relies on behaviour supplied by the core implementation's
:lname:`Scheme`.  That's behaviour we don't have as we're
(deliberately) starting from nothing.

My next influence was the discovery of :ref-author:`Bill Hails`'
(seemingly?) unpublished book :ref-title:`Exploring Programming
Language Architecture in Perl` (EPLAiP) :cite:`EPLA` which implements
a :lname:`Scheme` interpreter in :lname:`Perl`.  I felt a lot more
comfortable following the working here than I did with
:ref-title:`SICP` and it throws in a few more interesting titbits like
an object system and continuations.  In fact, his Figure 13.6, of all
things, is the one that finally made continuations click for me.

So thoroughly influenced, not only did I go through building all his
increasing-levels-of-complexity interpreters in :lname:`Perl` I
actually went back and did them all again in :lname:`C`!  *Madness!*

And great fun!  I felt I was getting somewhere.  :ref-title:`EPLAiP`
is (obviously?) using :lname:`Perl` as its core implementation
language and, like :ref-title:`SICP`, relies on some behaviour from
the underlying :lname:`Perl`.  

My final inspiration source actually costs money (I'm showing
commitment here!)  in the form of what many might describe as the
bible for implementing, certainly, :lname:`Scheme`,
:ref-author:`Christian Queinnec`'s :ref-title:`Lisp in Small Pieces`
(LiSP) :cite:`LiSP`.  :ref-title:`LiSP` takes you through a dozen
variations of a :lname:`Scheme` engine from basic evaluation through
byte compilation for a virtual machine and even production of
:lname:`C` code to be compiled as a fixed executable.

:ref-title:`LiSP` uses :lname:`Scheme` as its core implementation
language and a Scheme-ish language is the one it is
evaluating/compiling.  So, again, we can't use "it" (given the number
of evaluators/compilers I presumably mean a later one) directly.

However, :lname:`Idio` is derived from :ref-title:`LiSP` by the simple
expedient of me figuring out what I needed to do to bootstrap enough
framework to get going.  That's an interesting point to reflect on,
there are several subsystems where there is a degree of mutual
reliance, the final version of the one can't exist without the final
version of the other.  We have neither when we start and will have to
bodge our way through.

At some point, though, I decided I'd had enough implementing something
to interpret/compile a dialect of :lname:`Scheme` and it was time to
wield the language cleaver of destiny and start butchering this
Scheme-ish language into something that did what I want.

I made a mistake at this point, though.  I didn't put the
:lname:`Scheme` code to one side and introduce some parallel
interpreter/compiler, I just hacked the :lname:`Scheme` engine to
bits.  Very satisfying but in hindsight a bit unwise.  It turns out
that :lname:`Idio` is *this close* (put your thumb and forefinger up
close to your eye and then squeeze them together) to :lname:`Scheme`
and :lname:`Scheme` has had a lot of software written for it.  So I've
found myself porting software written for :lname:`Scheme` and, more or
less, changing the syntax and a few structural elements.  It's not a
case of thinking that this is something that could be automated it's
the realisation that I could have simply left the :lname:`Scheme`
engine in there and just read it in direct.

What a waste.  So if there's one lesson you can learn...

.. rst-class:: center

---

There are a lot of programming languages out there.  There are a lot
of variations of the same kinds of languages out there.  There are a
lot of implementations of the *exact same language* out there --
compounded by any number of revisions of that language.

Which is these, if any, are influential to us as language designers
and implementers?  Good question.

In principle *all* languages should be influencing us as designers,
however, I'm not a programming language polyglot (nor likely to be)
so, whilst the core feature of my language wants to be the process
orchestration abstractions of the shell, the programming language side
of things comes from what I'm aware of, the :lname:`Perl`\ s,
:lname:`Python`\ s and :lname:`Lisp`\ s of the world.  (Not much to go
on, eh?  Let's hope it doesn't show!)

That said there are ever useful resources like `Hacker News`_ to keep
us in touch with people doing work with programming languages, shells,
JITs, secure coding, cryptography, etc. before you even start on the
general technology-oriented news.

From there you can pick up information on nascent and little
programming languages and eventually discover resources keeping track
of these things like the `Fledgling Languages List`_.  You can
discover people playing with programming ideas, implementation
techniques and be able to drill through to underlying academic papers.

One guiding property of any language that is going to be influential
to us (me?) as an implementer is that you have the time and space to
*grok* it.  What is it trying to do and, critically, how is it trying
to do it?  That is drawing us, inevitably, towards the smaller more
... *consumable* ... languages (or variants of languages).

I can see that over time I've downloaded and looked at (and variously
forgotten the details of) in no particular order:

* well-known languages:

  * Tcl_ in actual Toolkit Command Language mode as well as Expect mode.

  * Lua_ which is regularly appearing as an in-game programming language

* less well-known languages:

  * Qish_ playing with threading and garbage collectors

  * Solid_ minimalist interpreted language, with a clean object model and a tiny VM

  * Potion_ an object- and mixin-oriented (traits) language

  * Maru_ a symbolic expression evaluator that can compile its own implementation language

  * io_ a programming language focused on expressiveness through simplicity

* :lname:`Scheme` implementations

  * Stklos_ better known for its connection to the `GTK\+`_ toolkit it
    uses a virtual machine, :term:`CLOS`, PCRE_ and more

  * GNU_'s Guile_

  * :ref-author:`Alex Shinn`'s Chibi_ Scheme

  * :ref-author:`Nils M Holm`'s :ref-title:`S9fES` (Scheme 9 from
    Empty Space) :cite:`S9fES`

I have been unduly influenced by :ref-author:`Nils M Holm`'s
:ref-title:`S9fES`, in particular the September 2009 variant I
downloaded as it had an implementation of *bignums*.

For some reason I had become fixated on `bignums
<https://en.wikipedia.org/wiki/Arbitrary-precision_arithmetic>`_ and
wanted to understand the science (so advanced it was indistinguishable
from magic) that made it happen.  So many other implementations
deferred to the GMP_ (GNU Multi Precision Arithmetic Library) and GMP
itself is 2100 files and 435k lines of code -- I don't want to wade
through that!

The implementation of bignums is, of course, simply long-hand
arithmetic and, in the :ref-title:`S9fES` case, using a form of
range-limited integers to catch and handle carry bits.

Of course, by the time I'd figured out the implementation I'd been
poking about in :ref-title:`S9fES` for a while and, whilst none of the
underlying :lname:`C` is copied (the bignums implementation being
ported), there is a certain amount of the :lname:`Scheme` code that
has been copied largely because there is a reasonable test script
which meant taking the :lname:`Scheme` functions supporting
trigonometric functions with it.

That's not great.  Not because the code is poor, or anything, but
because I've taken it verbatim.  I can't claim to be able to describe
its working and certainly not well enough to be able to re-implement
it in a clean room.  The tests I can replace with code-coverage
results (and am, slowly) plus whatever boundary conditions I can think
of.  The trigonometric algorithms remain a mystery.  I can't do the
maths.
   
.. rst-class:: center

---

Who should be reading this opus?  This isn't a pedagogical text but a
faintly organized brain dump so I guess the audience is someone like
me: written a bit of code, done a bit of stuff but, most importantly,
*interested* in how things work.

Interested enough to want to try something of their own but, like I
was, at a bit of a loss as to how to begin.  You might not like where
I'm going or what I've done but it might help you scribble the first
line on the blank sheet of paper.
   
.. rst-class:: center

---

.. rst-class:: paragraph-header

Software

I've implemented :lname:`Idio` in :lname:`C` -- and using C99_ in
particular -- as, if nothing else, it's a programming language I'm
familiar with although by no means an expert.

There's plenty of reasons not to use :lname:`C` so I could have
written :lname:`Idio` in :lname:`Go` or :lname:`Rust` (or :lname:`D`
or ...) but that would mean:

#. I have to learn a new language -- wait... I'm learning a new
   language in order that I can design and implement my own?

#. everyone looking at the implementation has to

   * learn the new language

   * *and* the nuances of this other language

   * *and* figure out if I've written something brilliant or am just
     getting away with it.

   All of us doing that in a new language whilst figuring out how to
   make the target language work.  Doesn't seem... right.

#. everyone has to be able to *get hold of* this other language

I would like my language to be reasonably portable and from my
background I'm fairly certain most systems I've used have a :lname:`C`
compiler.  Your current system may have a packaging system that let's
you download a ready-to-roll ``$LANGUAGE`` implementation but not
everybody does.

The downside of this is that we're writing everything in :lname:`C`
with all its attendant issues with memory management and pointer
mangling and everything else that people throw in the face of
:lname:`C`.  OK, sure.  Let's just write safe, secure code.  It can't
be that hard....

.. rst-class:: paragraph-header

Hardware and Operating Systems

I'm limited to the physical kit I can get my hands on: various x86
systems and (the ubiquitous Raspberry Pi?) ARM systems and to what
virtual machines I can convince to run on either.  That gives me a
reasonable pool of operating systems with enough variance to keep my
:lname:`C` porting honest.

One question arises, how *broad* should that pool be?  I've wrestled a
little with how much effort should I put into *old* operating systems.
I might be able to get hold of versions of Linux and, say, Solaris,
from the late 90s but am I looking for usable completeness or
technical completeness?  Does anyone, and this is critical, who *wants
to run a new shell* actually run one of these old operating systems?

The chances are that if you're still running an Operating System
released in the 90s then it is critical infrastructure -- otherwise
you wouldn't still be running it -- and you're not likely to (be
allowed to) run new code with a dubious provenance on it.

That said, there is some technical merit in ensuring that the code is
portable enough to run on such systems as it was the time of the
transition from 32-bit to 64-bit computing and the various LP64_
variations that came with it.

So I think the goal is to ensure that the shell works on a fleet of
the latest Operating Systems together with a selection of "others"
which aren't expected to see much action but which force the code to
be honest.

A broad range without being too specific:

.. csv-table:: Test Systems
   :header: "ISA", "OS", "bits", "notes"

   "x86-64", "Fedora 33", 64
   "x86-64", "Ubuntu 18", 64
   "x86-64", "Debian 10", 64 / 32
   "x86-64", "CentOS 7", 64
   "x86-64", "CentOS 6", 64 / 32
   "x86-64", "OpenIndiana Hipster", 64
   "x86-64", "OpenIndiana a151", 64 / 32
   "x86-64", "FreeBSD 10", 32
   "x86-64", "Mac OS 10.15.5", 64, 10.15.6 breaks virtualisation software
   "i386", "Mac OS 10.5.8", 32
   "ARMv7", "Raspbian 9", 32
   "x86-64", "Windows 10 via WSL", 64

   "x86-64", "Solaris 10", 32, WIP

.. rst-class:: smaller

Noting that several recent Operating System releases have dropped
32-bit support.

Whenever we see performance statistics for a programming language we
should be given clues about the host machine, usually the CPU make and
model.  No computer I've ever owned has matched a single one of these
but all these things are relative.

A Raspberry Pi (Model 3B+) *is* much closer to a standard unit of
computing and, being a tichy little thing, also represents, to some
degree, a *minimal* unit of computing.  If :lname:`Idio` can "perform"
on a Raspberry Pi then we've nailed it.

Unfortunately, :lname:`Idio` does not "perform" on a Raspberry Pi.
Which is annoying.  It doesn't "perform" on the latest and greatest
CPU I have.  Which is more disturbing.

More work required.

.. rst-class:: center

---

The standout sections of code snippets and console interaction look
like:

.. code-block:: sh

   ls -l *.txt

.. sidebox:: There have been several efforts to recreate green screen
             fonts, like glasstty_, but that's taking old-school
             authenticity too far.

where, the Internet tells me, the `colours are accurate for green
screen VDUs`_ together with the usual inline representations for code
like ``$PATH`` etc..



Man pages, see :manpage:`man(1)`, are most likely to refer to whatever
primary development system I happen to be using -- almost certainly a
Linux variant.  Solaris and BSDs may vary.
