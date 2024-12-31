{
  pkgs,
  system,
}:
pkgs.mkShell rec {
  packages = (import ./lib.nix).devPkgs {inherit pkgs system;};
  LD_LIBRARY_PATH =
    pkgs.lib.makeLibraryPath ([pkgs.stdenv.cc.cc] ++ packages);

  shellHook = ''
    export PRISMA_SCHEMA_ENGINE_BINARY="${pkgs.prisma-engines}/bin/schema-engine"
    export PRISMA_QUERY_ENGINE_BINARY="${pkgs.prisma-engines}/bin/query-engine"
    export PRISMA_QUERY_ENGINE_LIBRARY="${pkgs.prisma-engines}/lib/libquery_engine.node"
    export PRISMA_INTROSPECTION_ENGINE_BINARY="${pkgs.prisma-engines}/bin/introspection-engine"
    export PRISMA_FMT_BINARY="${pkgs.prisma-engines}/bin/prisma-fmt"
  '';
}
