# Proxy image

Build from the configured `split` branch once its repository is public:

```bash
./build.sh
```

Build an explicit local proxy working tree:

```bash
./build.sh /path/to/phobos-5g
```

Images are loaded locally as `chronos-proxy:<commit8>`. Dirty trees use
`<commit8>-dirty-<content-hash8>`. Override the repository with
`IMAGE_REPOSITORY`; the script never pushes.
