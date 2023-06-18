# TinyVM

> Sandbox for small programs, repository of silly algorithms, and Connect4 tournament. Submit your own, and see how well/badly it does! :D

Tic-tac-toe and Connect4 are solved games, for which unbeatable strategies exist. On the other hand, games like chess and go are too hard to "just play around". A silly algorithm has no real chance to compete at all!

Hence Connect4 on TinyVM: Connect4 is moderately difficult, where playing the perfect strategy still takes a considerable amount of resources. TinyVM, as the name suggests, limits those resources. By executing the algorithms on a virtual CPU, resources like memory and computation time can be tightly controlled. This allows simple algorithms to compete with each other, without having to rely on silly restrictions such as "it has to finish within 1.3 seconds of computation time of my computer".

<!-- Keep in sync with tournament/template.html -->
The basic idea is inspired by <a href="https://www.youtube.com/watch?v=DpXy041BIlA">Elo World by Tom7</a>. I guess the biggest differences are:
<ul>
  <li>Let's use Connect4 instead of chess, because it's much much simpler to make a valid move in Connect4.</li>
  <li>Instead of writing all the algorithms myself, enable and encourage everyone else to write and easily compare them.</li>
  <li>Because of that, and also because it's fun in and of itself, write a lot of assembly.</li>
  <li>Try to enforce programmatically that the algorithms don't just brute-force the solution.</li>
  <li>Have a [neat website that presents the results](https://benwiederhake.github.io/tinyvm/). In particular I liked the table at the end of <a href="http://tom7.org/chess/weak.pdf">Tom7's paper</a>, so I gotta have something similar.</li>
</ul>
</p>

New silly algorithms are very welcome! I'd love to hear your feedback, or any other kind of issue: [https://github.com/BenWiederhake/tinyvm/issues/new](https://github.com/BenWiederhake/tinyvm/issues/new).

This repository contains:
- `assembler/`: An assembler from program text to binary TinyVM instructions.
- `data-layout/`: The specification of how [Connect4 data](https://github.com/BenWiederhake/tinyvm/blob/master/data-layout/connect4.md#connect4-conventions) is passed to your algorithm.
- `instruction-set-architecture.md`: An in-depth definition of all the TinyVM instructions and their effect.
- `src/`: The source code for TinyVM itself, which can execute TinyVM binaries. (Just like the jvm can execute java binaries, for example.)
- `tournament/`: Management code that generates this [neat website](https://benwiederhake.github.io/tinyvm/).
- `vms/connect4/`: A bunch of silly Connect4 algorithms, stored as program text. A script to easily (re-)generate all binaries is included.

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [Performance](#performance)
- [TODOs](#todos)
- [NOTDOs](#notdos)
- [Contribute](#contribute)

## Install

You'll need python and rust; I recommend using your favorite package manager to install these.

Other than that, no special packages or configuration is necessary.

(*): TinyVM has a dependency on the crate `getrandom`; but that is automatically resolved by cargo, as usual.

### Additional step for best performance

For best performance, you should allow `rustc`
to use special instructions available on your specific CPU that can speed up execution even more.
I don't expect this to make a huge difference, but it's worth a shot if you think it's too slow.

Add this to your `.cargo/config` file
[somewhere up the tree](http://doc.crates.io/config.html#hierarchical-structure):

```TOML
[build]
rustflags = ["-C", "target-cpu=native"]
```

## Usage

Well, what are you trying to do?

### (Re-)Build the TinyVM binaries

Initially, you need to build all TinyVM binaries:
```
./vms/convert_all.sh
```
You will need to re-run this whenever you add a new algorithm.

### Manually build TinyVM

Although it would happen automatically later on anyway, it might be nice to build of TinyVM in advance:
```
cargo build --release
```
(That will also take care of downloading the `getrandom` dependency and compiling it.)

### Build the website

In case you want to build your very own tournament page, e.g. to compare the performance of your own new algorithm, you can trigger the build like so:
```
mkdir ./tournament/pages/  # Or a checkout of the latest gh-pages branch
./tournament/run_tournament.py
```
FIXME: Not implemented yet, duh

### Run all self-tests

Test TinyVM itself:
```
cargo test
```

Test the assembler:
```
./assembler/asm_test.py
```

Test that all TinyVM algorithms work and compile to the indicated hash:
```
./vms/convert_all.sh
```

## Performance

It seems that TinyVM runs at about 30 MHz in debug mode, and about 300 MHz in release more. That's *way* faster than anything I'll actually need, so I didn't optimize it at all.

The main TinyVM executable automatically detects whether both players are deterministic, and doesn't sample multiple times, thus saving a large factor of running time.

## TODOs

Next up are these:
* Implement automatic tournament execution
* Implement tournament ranking
* Tell people about it
* Encourage people to make and shat silly Connect4 algorithms :D
* Perhaps extend this project to other games? Perhaps chess, go, or maybe [Tak](https://en.wikipedia.org/wiki/Tak_(game))?
* Perhaps try to write an algorithm that plays more than one game?
* Recreate logo.png and favicons using the new `#FF4B5D` / `#EDFF76` / `#000049` colors, or at least the correct hues.

## NOTDOs

Here are some things this project will definitely not support:
* TinyVM will never support "syscalls", because having I/O or network access is absolutely against the point of this project. If you add it, I'd like to ask you to define a new feature flag in the [ISA, section CPUID](https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102b-cpuid) and tell me about it.

These are somewhat unlikely, but I'm not opposed either:
* An actual high-level language compiler. (Doing this through LLVM sounds like the best approach.)
* "Advanced" calculations in the assembler. That's just reinventing the wheel in a way that I don't find interesting right now.

## Contribute

Feel free to dive in! [Open an issue](https://github.com/BenWiederhake/tinyvm/issues/new) or submit PRs.
