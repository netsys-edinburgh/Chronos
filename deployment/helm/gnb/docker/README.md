# gNB image

Build from the public `phobos-gnb` branch:

```bash
./build.sh
```

Build an explicit local OAI working tree:

```bash
./build.sh /path/to/openairinterface5g
```

Images are loaded locally as `chronos-gnb:<commit8>`. Dirty trees use
`<commit8>-dirty-<content-hash8>`. Override the repository with
`IMAGE_REPOSITORY`; the script never pushes. Compilation defaults to four jobs
on CPUs 4-7.
