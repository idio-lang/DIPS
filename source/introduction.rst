.. include:: global.rst

############
Introduction
############

I want to create a programmable shell.  At least that's the easiest
way of describing it.  I want to have the power and expressibility of
a proper programming language whilst at the same time utilising the
elegant abstractions of the shell for command orchestration.

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
interacting with other systems, gathering information, applying some
change.

These *always* start with a shell script.  I know to :pname:`netcat`
-this, or :pname:`ssh` with a particular key to obtain some bespoke
behaviour -that.  Most commands print unstructured text to *stdout*
which we can "screen scrape" to find out our facts.  Need
:lname:`Expect` to poke about in a bespoke User Interface to find some
status?  No problem.

But then I always do have a problem when I start to gather similar
information from more than one source and I need an ostensibly simple
list of lists or hash of arrays or, in fact, anything that reveals the
shell's great computing problem.  If computing is algorithms and data
structures, the shell can ``if`` and ``while`` with the best of them
but it only has unnamed flat lists for data structures.

Suddenly, we're goosed.  Our world-conquering shell script has thrown
us at the first hurdle.

Real programmers will turn to :lname:`Perl` (in my youth) or
:lname:`Python` (in my attempts to appear young) or some other
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
short cuts there.

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
programming language of choice, :lname:`Scheme` (the *horror*, the
*horror*), and argue as to why it does what we need it do.
:lname:`Scheme` does an awful lot more besides which we can benefit
from although there is a decent argument that it does too much and
that we should hold back from some of its more baroque and entangled
features.  We'll then look at how to implement a Scheme-ish language
from basic interpretation through to byte compilation.  If
:lname:`Scheme` could do the things we want then the smart people
behind :lname:`Scheme` would already have done so, so we need to
discuss, *ahem*, how to butcher it until it bends to our will!  That
leads to some tricky compromises.

There's another, more reflective, reason for this rambling.  In my
experience when I have tried to explain what I have done in written
prose using examples I had not tried myself I discover that my casual
understanding is, in fact, an abject misunderstanding -- and, often as
not, a poor implementation.  If I can satisfactorily explain how
:lname:`Idio` works then there's a decent chance it actually doing
what it says on the side of the tin.

.. rst-class:: center

---

One obvious question is, why am I writing a new shell at all?  Aren't
there lots of perfectly good shells already out there and even more
perfectly good programming languages?  Why don't I hack away at
:lname:`Bash`, say, and look to support nested data structures or if
I'm really determined to have my shell abstractions, couldn't I look
into the bowels of :lname:`Python` and see if I can't slip a ``|``
into the code reader?

.. sidebox:: :lname:`Python`, I confess, might be better than most for
	     design documentation -- although I've not looked for any
	     as I don't want to use it for the programming part of my
	     programmable shell.  YMMV

Well, yes, I *could* have pursued either approach but we're back to
that business of not having an intimate understanding of the design of
the language -- and an understanding of the implementation, for that
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

Most importantly of all, I want to know *how* things work.  I want to
know how *all* the things work.  That means everything.  We start with
nothing, we use nothing from anyone else that we haven't *re-imagined*
ourselves.

The downside of this *Not Invented Here* approach is at best we don't
have world class implementations and at worst we suffer our own
incompetence and misunderstanding -- there's a price to pay for
everything.

.. rst-class:: center

---

.. topic:: Influences

	   These things

.. todo: influences
   
