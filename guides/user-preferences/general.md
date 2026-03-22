# User Preferences — General

- .md files: bullet points over prose, tight structure, no padding. Only include what is necessary.
- When updating any .md file, actively look for content to delete — if you're not occasionally removing/refactoring something, you're not changing enough.
- Always run `make` with `-j16`. Example: `make clean && make vector-tests -j16 && make coverage -j16`
- Do NOT read make/build run logs inline — they contain too much noise. Check log files directly only when there is an error to diagnose.
