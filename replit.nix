{pkgs}: {
  deps = [
    pkgs.libsodium
    pkgs.iana-etc
    pkgs.postgresql
    pkgs.openssl
  ];
}
