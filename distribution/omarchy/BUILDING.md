# Building the Omarchy integration

Build on Linux x86_64 with Rust 1.97.1, a C/C++ toolchain, pkg-config, OpenSSL,
libudev, libseccomp and SQLite development packages. Use the lockfiles from the
same ANOLISA commit. A separate target directory can reuse dependencies without
changing component source.

```bash
export CARGO_TARGET_DIR="$PWD/target/omarchy"
cargo build --release --locked --manifest-path src/aw/Cargo.toml --bin aw
cargo build --release --locked --manifest-path providers/agent-sec-core/Cargo.toml
cargo build --release --locked --manifest-path providers/tokenless/Cargo.toml
cargo build --release --locked --manifest-path src/cosh-ng/Cargo.toml --workspace
cargo build --release --locked --manifest-path src/agent-sec-core/v2/Cargo.toml -p asc-cli -p asc-daemon
bash src/tokenless/packaging/build/setup-rtk.sh
cargo build --release --locked --manifest-path src/tokenless/Cargo.toml --bin tokenless
python3 distribution/omarchy/package.py --bin-dir "$CARGO_TARGET_DIR/release" --output "$PWD/target/omarchy-candidate" --cache "$PWD/target/omarchy-downloads"
```

`package.py` uses cosh's maintained raw-package layout, adds the native programs,
verifies the official Qoder archive by SHA-256, and produces a tarball plus
`SHA256SUMS`. Every payload file is recorded in `bundle.json`. The source commit
identifies the component checkout; review local integration changes separately
until they have been committed. This is an experimental integration package,
not a new official ANOLISA component release.

For the 0.1.1 package, reuse the verified demo.2 archive with `--reuse-demo2 ARCHIVE`
in place of `--bin-dir`. The assembler checks each reused program and sources
Qoder CLI 1.1.84 separately. Pass `--cache` to reuse the verified Qoder archive.
`bundle.json` records
the original binary provenance, the assembly environment, and per-file
integration source digests.

The checkout installer expects the verified `anolisa-omarchy-0.1.1.tar.gz`
asset under the `omarchy-v0.1.1` GitHub Release. Its pinned SHA-256 is in
`distribution/omarchy/SHA256SUMS`. If rebuilding the release, verify the new
archive on Omarchy and update the pin before publishing that archive.

The current builder has no binary compatibility guarantee for every Linux
distribution. Validate the candidate with `ldd`, real CLI calls and the native
desktop in a clean target Omarchy image before handing it to another user.
