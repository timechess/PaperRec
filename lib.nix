{
  devPkgs = {
    pkgs,
    system ? "x86_64-linux",
  }:
    with pkgs; [
        poetry
        gnumake
        ruff
        openssl
      ];
}