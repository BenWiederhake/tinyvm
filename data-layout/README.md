# Data layout conventions

At the start of execution, 0xFFFF should contain the environment ID, and 0xFFFE should contain the version. (In case someone wants to write a multi-game algorithm.)

- 0x0000: reserved (invalid)
- 0x0001: [0001_connect4.md](0001_connect4.md)
- 0x0002: [0002_judge.md](0002_judge.md)
- 0x0003 - 0xEFFF: reserved (might be defined later)
- 0xF000 - 0xFFFF: private use

The other initial values of registers and memory are left to the specific data-layout definition, but should default to all-zeros if not used intentionally.
